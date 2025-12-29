package supervision.industrial.auto_pilot.workflow.detector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.*;
import dependancy_bundle.model.enumeration.Severity;
import dependancy_bundle.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.workflow.detector.dto.OccurrenceStats;
import supervision.industrial.auto_pilot.workflow.detector.dto.PredictiveSignals;
import supervision.industrial.auto_pilot.workflow.detector.dto.StepIntervalStats;
import supervision.industrial.auto_pilot.workflow.detector.predict.Burstiness;
import supervision.industrial.auto_pilot.workflow.detector.predict.Ewma;
import supervision.industrial.auto_pilot.workflow.detector.predict.HawkesLike;
import supervision.industrial.auto_pilot.workflow.detector.rules.AnomalyRules;
import supervision.industrial.auto_pilot.workflow.detector.rules.RuleContext;
import supervision.industrial.auto_pilot.workflow.detector.rules.RuleHit;
import supervision.industrial.auto_pilot.workflow.prompt.AnomalyPromptService;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.*;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

@Slf4j
@Service
@RequiredArgsConstructor
public class PlcAnomalyDetectionService {

    @Autowired
    private final AnomalyPromptService anomalyPromptService;
    private static final ObjectMapper M = new ObjectMapper();

    private final WorkflowNominalService workflowNominalService;
    private final StepStatsService stepStatsService;

    private final PlcEventRepository plcEventRepository;
    private final PlcAnomalyRepository plcAnomalyRepository;
    private final PartRepository partRepository;
    private final MachineRepository machineRepository;
    private final RunnerConstanteRepository runnerConstanteRepository;
    private final ProductionStepRepository productionStepRepository;
    private final ProductionScenarioStepRepository productionScenarioStepRepository;

    // =========================================================
    // NOMINAL SCENARIO (string for prompt)
    // =========================================================
    public String getScenarioNominal(PlcAnomaly a) {

        StringBuilder sb = new StringBuilder();

        Machine m = a.getMachine();
        ProductionStep ps = productionStepRepository.findById(a.getProductionStep().getId()).orElse(null);

        sb.append("Machine nominale : ")
                .append(m.getCode())
                .append(" - ")
                .append(m.getName())
                .append("\n");

        sb.append("Durée nominale step : ")
                .append(valueOrNA(ps != null ? ps.getNominalDurationS() : null))
                .append(" s\n");

        sb.append("Enchaînement nominal des steps :\n");

        int i = 1;
        Workorder wo = a.getWorkorder();
        if (wo != null && wo.getProductionScenario() != null && wo.getProductionScenario().getProductionScenarioSteps() != null) {
            for (ProductionScenarioStep prodStep : wo.getProductionScenario().getProductionScenarioSteps()) {
                ProductionStep step = productionStepRepository.findById(prodStep.getProductionStep().getId()).orElse(null);
                if (step == null) continue;
                sb.append(i++)
                        .append(". ")
                        .append(step.getStepCode())
                        .append(" ")
                        .append(step.getName())
                        .append(" [")
                        .append(valueOrNA(step.getNominalDurationS()))
                        .append(" s]")
                        .append("\n");
            }

            ProductionScenarioStep lastProductionStep =
                    wo.getProductionScenario()
                            .getProductionScenarioSteps()
                            .stream()
                            .max(Comparator.comparing(ProductionScenarioStep::getStepOrder))
                            .orElse(null);
            lastProductionStep = productionScenarioStepRepository.findById(lastProductionStep.getId()).get();
            lastProductionStep.setProductionStep(productionStepRepository.findById(lastProductionStep.getProductionStep().getId()).get());
            if (lastProductionStep.getProductionStep() != null) {
                sb.append("\nStep terminal nominal attendu : ")
                        .append(lastProductionStep.getProductionStep().getStepCode())
                        .append(" ")
                        .append(lastProductionStep.getProductionStep().getName())
                        .append("\n");
            }
        }

        return sb.toString();

    }

    private String valueOrNA(Object v) {
        return v == null ? "N/A" : v.toString();
    }

    // =========================================================
    // MAIN ENTRY
    // =========================================================

    public void detectAndPersist(PlcEvent event) {
        if (event == null) return;
        if (event.getWorkorder() == null) return; // impossible de construire le nominal sans WO
        if (event.getPart() == null) return;

        // 1) Nominal workflow (issu du scénario du workorder)
        List<ProductionStep> nominalSeq =
                event.getWorkorder()
                        .getProductionScenario()
                        .getProductionScenarioSteps()
                        .stream()
                        .sorted(Comparator.comparing(ProductionScenarioStep::getStepOrder))
                        .map(ProductionScenarioStep::getProductionStep)
                        .filter(Objects::nonNull)
                        .toList();

        // IMPORTANT: mapping stepId -> step nominal. Ici on mappe par ID (Long),
        // donc il faut que RuleContext/AnomalyRules fasse des get(Long id), pas des get(stepCode).
        Map<Long, ProductionStep> nominalByStepId =
                workflowNominalService.loadNominalByStepId(event.getWorkorder().getId());

        // 2) Previous  event for same part (reference temporelle)
        PlcEvent prevEvent = null;

        Optional<PlcEvent> prevOpt = plcEventRepository
                .findFirstByPartIdAndTsBeforeOrderByTsDesc(
                        event.getPart().getId(),
                        event.getTs()
                );
        prevEvent = prevOpt.orElse(null);


        // 3) Apply deterministic rules
        RuleContext ctx = new RuleContext(
                event,
                prevEvent != null ? prevEvent.getTs() : null,
                prevEvent,
                nominalByStepId,
                nominalSeq
        );

        List<RuleHit> hits = AnomalyRules.evaluate(ctx);
        if (hits.isEmpty()) {
            log.info("[Detector] Aucune anomaly sur cet event ! ");
            return;
        }


        // 4) Build anomaly entity
        PlcAnomaly a = new PlcAnomaly();
        a.setWorkorder(event.getWorkorder());
        a.setPlcEvent(event);

        // Force attach managed Part (avoid lazy proxy outside session in downstream mapping)
        Part part = partRepository.findById(event.getPart().getId()).orElseThrow();
        a.setPart(part);

        a.setTsDetected(OffsetDateTime.now());
        a.setCycle(event.getCycle());
        a.setMachine(event.getMachine());
        a.setProductionStep(event.getProductionStep());

        a.setRuleAnomaly(true);
        a.setRuleReasons(ruleReasonsJson(hits));

        long errorHits = hits.stream().filter(h -> h.ruleCode() != null && h.ruleCode().contains("ERROR")).count();
        a.setHasStepError(errorHits > 0);
        a.setNStepErrors((int) errorHits);

        // 4.1) Durée "terrain" = intervalle entre prev STEP_OK et l'event courant (ts)
        // -> c'est EXACTEMENT ce que tu veux : "duration par rapport à la step précédente"
        Double intervalS = computeIntervalSeconds(prevEvent, event);
        a.setCycleDurationS(intervalS);

        Double nominalS = event.getProductionStep() != null
                ? event.getProductionStep().getNominalDurationS()
                : null;

        /*
         * Overrun uniquement calculable si :
         * - une durée terrain existe
         * - une durée nominale officielle existe
         * Sinon : overrun non applicable (null)
         */
        if (intervalS != null && nominalS != null) {
            a.setDurationOverrunS(intervalS - nominalS);
        } else {
            a.setDurationOverrunS(null);
        }
        // 5) Stats d’occurrence + "écart-type" sur survenue d’erreurs similaires
        // Ici on définit "erreur similaire" comme:
        //   - même machine
        //   - même productionStep
        //   - même code (si présent)
        //   - et on ne compte que les events ERROR (level = ERROR ou code != OK selon tes conventions)
        SimilarErrorStats errStats = computeSimilarErrorStats(event, 7);
        a.setEventsCount(errStats.sampleCount());

        // 6) Predictive signals (EWMA / rate / burstiness / Hawkes-like) — basé sur séries et historiques
        PredictiveSignals sig = computePredictiveSignals(event);

        a.setWindowDays(sig.windowDays());
        a.setEwmaRatio(sig.ewmaRatio());
        a.setRateRatio(sig.rateRatio());
        a.setBurstiness(sig.burstiness());
        a.setHawkesScore(sig.hawkesScore());
        a.setConfidence(sig.confidence());

        // 6.1) Anomaly score "simple" : max des signaux + bonus occurrence (écart-type / z-score)
        // - si pas d’historique: zScore=0
        // - hawkes est int -> cast double
        double z = errStats.zScore();
        double base = Math.max(sig.ewmaRatio(), Math.max(sig.rateRatio(), (double) sig.hawkesScore()));
        a.setAnomalyScore(Math.max(base, z));

        // 7) Severity / criticité (business)
        a.setSeverity(computeSeverity(hits, sig, errStats, intervalS, nominalS).name());

        PlcAnomaly aRes = null;
        if (!plcAnomalyRepository.existsByPlcEventId(event.getId())) {
            aRes = plcAnomalyRepository.saveAndFlush(a);
            log.info("[Detector]  anomaly  Detecté => persistance et prompt LLM ! ");

            RunnerConstante rc = runnerConstanteRepository.findAll().stream().findFirst().get();
            rc.setLastAnomalyAnalise(aRes.getId());
            runnerConstanteRepository.save(rc);
        } else {
            aRes = plcAnomalyRepository.findAllByPlcEventId(event.getId()).stream().findFirst().get();
        }
        a.setId(aRes.getId());
        anomalyPromptService.buildPrompt(
                getScenarioNominal(a),
                a
        );
    }

    public void generateLLMPrompt(PlcAnomaly a) {

        Executor LLM_EXECUTOR =
                Executors.newSingleThreadExecutor(r -> {
                    Thread t = new Thread(r);
                    t.setName("llm-prompt-thread");
                    t.setDaemon(true);
                    return t;
                });


        LLM_EXECUTOR.execute(() -> {
            try {
                anomalyPromptService.buildPrompt(
                        getScenarioNominal(a),
                        a
                );
            } catch (Exception e) {
                System.err.println("[LLM] Prompt generation failed for anomaly " + e);
            }
        });
    }


    // =========================================================
    // INTERVAL STEP
    // =========================================================
    private Double computeIntervalSeconds(PlcEvent prev, PlcEvent cur) {
        if (prev == null || prev.getTs() == null || cur == null || cur.getTs() == null) return null;
        long ms = Duration.between(prev.getTs(), cur.getTs()).toMillis();
        return ms / 1000.0;
    }

    // =========================================================
    // "SIMILAR ERRORS" STATS (occurrence + stddev)
    // =========================================================

    private SimilarErrorStats computeSimilarErrorStats(PlcEvent event, int windowDays) {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime since = now.minusDays(windowDays * 2L);

        Long machineId = event.getMachine() != null ? event.getMachine().getId() : null;
        Long stepId = event.getProductionStep() != null ? event.getProductionStep().getId() : null;

        if (machineId == null || stepId == null) {
            return new SimilarErrorStats(0, 0.0, 0.0, 0.0, 0.0);
        }

        double[] series = stepStatsService.dailyOccurrenceSeries(event.getMachine(), event.getProductionStep(), since);

        if (series == null || series.length == 0) {
            return new SimilarErrorStats(0, 0.0, 0.0, 0.0, 0.0);
        }

        int mid = Math.max(1, series.length / 2);
        double baseMean = mean(slice(series, 0, mid));
        double baseStd = stddev(slice(series, 0, mid), baseMean);
        double recMean = mean(slice(series, mid, series.length - mid));

        double z = 0.0;
        if (baseStd > 1e-9) {
            z = (recMean - baseMean) / baseStd;
        }

        int sampleCount = series.length;
        return new SimilarErrorStats(sampleCount, baseMean, baseStd, recMean, z);
    }

    private double mean(double[] x) {
        if (x == null || x.length == 0) return 0.0;
        double s = 0.0;
        for (double v : x) s += v;
        return s / x.length;
    }

    private double stddev(double[] x, double mean) {
        if (x == null || x.length < 2) return 0.0;
        double s = 0.0;
        for (double v : x) {
            double d = v - mean;
            s += d * d;
        }
        return Math.sqrt(s / (x.length - 1));
    }

    private record SimilarErrorStats(
            int sampleCount,
            double baseMean,
            double baseStd,
            double recentMean,
            double zScore
    ) {
    }

    // =========================================================
    // PREDICTIVE SIGNALS (unchanged, but keep as is)
    // =========================================================
    private PredictiveSignals computePredictiveSignals(PlcEvent event) {
        final int windowDays = 7;
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime recentSince = now.minusDays(windowDays);
        OffsetDateTime baselineSince = now.minusDays(windowDays * 2L);

        OccurrenceStats recent = stepStatsService.anomalyOccurrenceRate(
                event.getMachine(), event.getProductionStep(), recentSince, windowDays);

        OccurrenceStats baseline = stepStatsService.anomalyOccurrenceRate(
                event.getMachine(), event.getProductionStep(), baselineSince, windowDays * 2);

        double baselineRate = Math.max(1e-9, baseline.ratePerDay());
        double rateRatio = recent.ratePerDay() / baselineRate;

        double[] series = stepStatsService.dailySimilarErrorSeries(
                event.getMachine(),
                event.getProductionStep(),
                event.getCode(),
                baselineSince
        );

        int mid = Math.max(1, series.length / 2);
        double ewBase = Ewma.compute(slice(series, 0, mid), 0.35);
        double ewRec = Ewma.compute(slice(series, mid, series.length - mid), 0.35);
        double ewmaRatio = Ewma.ratio(ewRec, ewBase);

        StepIntervalStats s = stepStatsService.intervalStats(event.getMachine(), event.getProductionStep(), baselineSince);
        double burstiness = Burstiness.compute(s.meanS(), s.stdS());

        List<OffsetDateTime> pastDetections = plcAnomalyRepository.findRecentDetections(
                event.getMachine().getId(), event.getProductionStep().getId(), baselineSince);

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
        System.arraycopy(x, start, out, 0, out.length);
        return out;
    }

    private String confidenceLabel(long n, double ewmaRatio, double rateRatio, int hawkes) {
        double strength = Math.max(Math.max(ewmaRatio, rateRatio), hawkes / 25.0);
        if (n >= 200 && strength >= 2.0) return "HIGH";
        if (n >= 80 && strength >= 1.4) return "MEDIUM";
        return "LOW";
    }

    // =========================================================
    // SEVERITY (slightly improved: include stddev/zScore and overrun)
    // =========================================================
    private Severity computeSeverity(List<RuleHit> hits,
                                     PredictiveSignals sig,
                                     SimilarErrorStats errStats,
                                     Double intervalS,
                                     Double nominalS) {

        boolean hasHardError = hits.stream().anyMatch(h -> "PLC_ERROR_LEVEL".equals(h.ruleCode()));
        boolean workflowBroken = hits.stream().anyMatch(h -> h.ruleCode() != null && h.ruleCode().startsWith("WORKFLOW_"));
        boolean intervalRule = hits.stream().anyMatch(h -> h.ruleCode() != null && (h.ruleCode().contains("INTERVAL") || h.ruleCode().contains("TS_")));

        // Overrun ratio
        double overrunRatio = 0.0;
        if (intervalS != null && nominalS != null && nominalS > 1e-9) {
            overrunRatio = intervalS / nominalS;
        }

        // Z-score occurrence strength
        double z = errStats != null ? errStats.zScore() : 0.0;

        // CRITICAL: hard error + predictive spike OR huge occurrence spike
        if (hasHardError && (sig.ewmaRatio() >= 1.8 || sig.rateRatio() >= 1.8 || sig.hawkesScore() >= 75 || z >= 2.5)) {
            return Severity.CRITICAL;
        }

        // MAJOR: workflow broken, hawkes high, ratios high, strong z-score, or big overrun
        if (workflowBroken || sig.hawkesScore() >= 60 || sig.ewmaRatio() >= 1.5 || sig.rateRatio() >= 1.5 || z >= 1.8 || overrunRatio >= 2.0) {
            return Severity.MAJOR;
        }

        // MINOR: timestamp/interval anomalies, small overrun
        if (intervalRule || overrunRatio >= 1.3) {
            return Severity.MINOR;
        }

        return Severity.MINOR;
    }

    // =========================================================
    // RULE REASONS JSON
    // =========================================================
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
