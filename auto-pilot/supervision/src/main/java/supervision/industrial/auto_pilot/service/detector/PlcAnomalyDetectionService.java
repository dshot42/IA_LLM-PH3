package supervision.industrial.auto_pilot.service.detector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.model.enumeration.Severity;

import supervision.industrial.auto_pilot.service.detector.dto.NominalStep;
import supervision.industrial.auto_pilot.service.detector.dto.OccurrenceStats;
import supervision.industrial.auto_pilot.service.detector.dto.PredictiveSignals;
import supervision.industrial.auto_pilot.service.detector.dto.StepIntervalStats;
import supervision.industrial.auto_pilot.service.detector.predict.Burstiness;
import supervision.industrial.auto_pilot.service.detector.predict.Ewma;
import supervision.industrial.auto_pilot.service.detector.predict.HawkesLike;

import supervision.industrial.auto_pilot.service.detector.rules.AnomalyRules;
import supervision.industrial.auto_pilot.service.detector.rules.RuleContext;
import supervision.industrial.auto_pilot.service.detector.rules.RuleHit;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class PlcAnomalyDetectionService {

    private static final ObjectMapper M = new ObjectMapper();

    private final WorkflowNominalService workflowNominalService;
    private final StepStatsService stepStatsService;

    private final PlcEventRepository plcEventRepository;
    private final PlcAnomalyRepository plcAnomalyRepository;

    @Transactional
    public void detectAndPersist(PlcEvent event) {
        if (event == null) return;

        // 1) Nominal workflow (BDD)
        String lineKey = "default";
        List<NominalStep> nominalSeq = workflowNominalService.loadNominalSequence(lineKey);
        Map<String, NominalStep> nominalByStepId = workflowNominalService.loadNominalByStepId(lineKey);

        // 2) Previous event for same part
        PlcEvent prev = plcEventRepository
                .findPreviousEventSamePart(event.getPartId(), event.getTs())
                .orElse(null);

        // 3) Apply deterministic rules
        RuleContext ctx = new RuleContext(event, prev != null ? prev.getTs() : null, prev, nominalByStepId, nominalSeq);
        List<RuleHit> hits = AnomalyRules.evaluate(ctx);

        // Stop early if no anomaly
        if (hits.isEmpty()) return;

        // 4) Build anomaly entity
        PlcAnomaly a = new PlcAnomaly();
        a.setPartId(event.getPartId());
        a.setTsDetected(OffsetDateTime.now());
        a.setCycle(event.getCycle());
        a.setMachine(event.getMachine());
        a.setStepId(event.getStepId());
        a.setStepName(event.getStepName());

        a.setRuleAnomaly(true);
        a.setRuleReasons(ruleReasonsJson(hits));

        long errorHits = hits.stream().filter(h -> h.ruleCode().contains("ERROR")).count();
        a.setHasStepError(errorHits > 0);
        a.setNStepErrors((int) errorHits);

        // 5) Predictive signals (EWMA / rate / burstiness / Hawkes-like)
        PredictiveSignals sig = computePredictiveSignals(event);
        a.setWindowDays(sig.windowDays());
        a.setEwmaRatio(sig.ewmaRatio());
        a.setRateRatio(sig.rateRatio());
        a.setBurstiness(sig.burstiness());
        a.setHawkesScore(sig.hawkesScore());
        a.setConfidence(sig.confidence());

        // 6) Severity / criticalité (business)
        a.setSeverity(computeSeverity(hits, sig).name());

        plcAnomalyRepository.save(a);
    }

    private PredictiveSignals computePredictiveSignals(PlcEvent event) {
        final int windowDays = 7;
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime recentSince = now.minusDays(windowDays);
        OffsetDateTime baselineSince = now.minusDays(windowDays * 2L);

        OccurrenceStats recent = stepStatsService.anomalyOccurrenceRate(
                event.getMachine(), event.getStepId(), recentSince, windowDays);

        OccurrenceStats baseline = stepStatsService.anomalyOccurrenceRate(
                event.getMachine(), event.getStepId(), baselineSince, windowDays * 2);

        double baselineRate = Math.max(1e-9, baseline.ratePerDay());
        double rateRatio = recent.ratePerDay() / baselineRate;

        double[] series = stepStatsService.dailyOccurrenceSeries(
                event.getMachine(), event.getStepId(), baselineSince);

        int mid = Math.max(1, series.length / 2);
        double ewBase = Ewma.compute(slice(series, 0, mid), 0.35);
        double ewRec  = Ewma.compute(slice(series, mid, series.length - mid), 0.35);
        double ewmaRatio = Ewma.ratio(ewRec, ewBase);

        StepIntervalStats s = stepStatsService.intervalStats(event.getMachine(), event.getStepId(), baselineSince);
        double burstiness = Burstiness.compute(s.meanS(), s.stdS());

        List<OffsetDateTime> pastDetections = plcAnomalyRepository.findRecentDetections(
                event.getMachine(), event.getStepId(), baselineSince);

        int hawkes = HawkesLike.score(
                now,
                pastDetections,
                1.0, 0.9, 1.0 / 3600.0
        );

        String confidence = confidenceLabel(s.sampleCount(), ewmaRatio, rateRatio, hawkes);
        return new PredictiveSignals(windowDays, ewmaRatio, rateRatio, burstiness, hawkes, confidence);
    }

    private static double[] slice(double[] x, int start, int len) {
        if (x == null || x.length == 0 || len <= 0) return new double[0];
        double[] out = new double[Math.min(len, x.length - start)];
        for (int i = 0; i < out.length; i++) out[i] = x[start + i];
        return out;
    }

    private String confidenceLabel(long n, double ewmaRatio, double rateRatio, int hawkes) {
        double strength = Math.max(Math.max(ewmaRatio, rateRatio), hawkes / 25.0);
        if (n >= 200 && strength >= 2.0) return "HIGH";
        if (n >= 80 && strength >= 1.4) return "MEDIUM";
        return "LOW";
    }

    private Severity computeSeverity(List<RuleHit> hits, PredictiveSignals sig) {
        boolean hasHardError = hits.stream().anyMatch(h -> h.ruleCode().equals("PLC_ERROR_LEVEL"));
        boolean workflowBroken = hits.stream().anyMatch(h -> h.ruleCode().startsWith("WORKFLOW_"));

        if (hasHardError && (sig.ewmaRatio() >= 1.8 || sig.rateRatio() >= 1.8 || sig.hawkesScore() >= 75)) {
            return Severity.CRITICAL;
        }
        if (workflowBroken || sig.hawkesScore() >= 60 || sig.ewmaRatio() >= 1.5 || sig.rateRatio() >= 1.5) {
            return Severity.MAJOR;
        }
        boolean interval = hits.stream().anyMatch(h -> h.ruleCode().contains("INTERVAL") || h.ruleCode().contains("TS_"));
        if (interval) return Severity.MINOR;
        return Severity.MINOR;
    }

    private JsonNode ruleReasonsJson(List<RuleHit> hits) {
        ArrayNode arr = M.createArrayNode();
        for (RuleHit h : hits) {
            ObjectNode o = M.createObjectNode();
            o.put("rule", h.ruleCode());
            o.put("message", h.message());
            if (h.details() != null) o.set("details", h.details());
            arr.add(o);
        }
        return arr;
    }
}
