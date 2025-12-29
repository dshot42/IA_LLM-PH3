package supervision.industrial.auto_pilot.api.service;

import com.fasterxml.jackson.databind.JsonNode;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.repository.PlcAnomalyRepository;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.api.dto.*;
import supervision.industrial.auto_pilot.workflow.productionHandler.WorkorderHandler;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service

public final class AnomalyContextBuilder {

    private final AnomalyReccurenceAnalyseService recurrenceService;
    private final PlcAnomalyRepository plcAnomalyRepository;

    private final WorkorderHandler workorderHandler;

    private AnomalyContextBuilder(AnomalyReccurenceAnalyseService recurrenceService, PlcAnomalyRepository plcAnomalyRepository,WorkorderHandler workorderHandler) {
        this.recurrenceService = recurrenceService;
        this.plcAnomalyRepository = plcAnomalyRepository;
        this.workorderHandler = workorderHandler;
    }

    public AnomalyContext build(PlcAnomaly a) {

        List<PlcAnomalyDto> allSimilarAnomalies =
                plcAnomalyRepository
                        .findAllByIdAndCreatedAtBetween(
                                a.getPlcEvent().getProductionStep().getId(),
                                OffsetDateTime.now().minusDays(a.getWindowDays()),
                                OffsetDateTime.now()

                        )
                        .stream()
                        .filter(similarA -> !similarA.getId().equals(a.getId()))
                        .sorted(Comparator.comparing(
                                similarA -> similarA.getPlcEvent().getTs(),
                                Comparator.reverseOrder()
                        ))
                        .limit(10)
                        .map(similarA -> new PlcAnomalyDto(
                                a.getMachine() != null ? similarA.getMachine().getName() : null,
                                a.getPart() != null ? similarA.getPart().getId() : null,
                                a.getPart() != null ? similarA.getPart().getExternalPartId() : null,
                                a.getPlcEvent() != null ? similarA.getPlcEvent().getTs().toLocalDateTime().toString() : null,
                                a.getProductionStep() != null ? similarA.getProductionStep().getId() : null,
                                a.getProductionStep() != null ? similarA.getProductionStep().getName() : null,
                                a.getProductionStep() != null ? similarA.getProductionStep().getStepCode() : null,
                                a.getRuleReasons() != null ? extractRules(similarA.getRuleReasons()): null
                        ))
                        .toList();

        ReccurenceAnomalyAnalyseDto recurrence =
                recurrenceService.analyse(a);

        List<RuleContextDto> rules = new ArrayList<>();
        JsonNode rr = a.getRuleReasons();
        if (rr != null && rr.isArray()) {
            rr.forEach(r ->
                    rules.add(new RuleContextDto(
                            r.path("rule").asText(),
                            r.path("message").asText(),
                            r.get("details")
                    ))
            );
        }

        // 👉 cycleTrace minimal (tu peux enrichir plus tard)
        List<CycleStepDto> cycle = buildCycleTrace(a);

        return new AnomalyContext(
                a.getId().toString(),
                a.getWorkorder().getId().toString(),
                a.getPart().getExternalPartId(),

                a.getMachine().getCode(),
                a.getMachine().getName(),
                a.getProductionStep().getStepCode(),
                a.getProductionStep().getName(),

                a.getProductionStep().getNominalDurationS(),
                a.getCycleDurationS(),
                a.getDurationOverrunS(),

                rules,
                a.getHasStepError(),

                a.getEventsCount(),
                a.getEwmaRatio(),
                a.getRateRatio(),
                a.getHawkesScore(),
                a.getAnomalyScore(),
                a.getHasStepError(),

                a.getSeverity(),
                a.getAnomalyScore(),

                recurrence,
                cycle,

                a.getTsDetected().toLocalDateTime().toString(),
                allSimilarAnomalies
        );
    }


    public List<CycleStepDto> buildCycleTrace(PlcAnomaly anomaly) {
        if (anomaly == null || anomaly.getWorkorder() == null) return List.of();

        Workorder wo = anomaly.getWorkorder();
        List<ProductionStep> steps = workorderHandler.getProductionSteps(wo);
        if (steps == null || steps.isEmpty()) return List.of();

        String anomalyStepCode = anomaly.getProductionStep() != null
                ? anomaly.getProductionStep().getStepCode()
                : null;

        return steps.stream()
                .map(ps -> {
                    boolean isAnomalyStep = anomalyStepCode != null
                            && ps != null
                            && anomalyStepCode.equals(ps.getStepCode());

                    // Nominal par step : OK
                    Double nominal = ps != null ? ps.getNominalDurationS() : null;

                    // Réel / overrun : inconnu par step -> on met uniquement pour l’étape anomalée
                    Double real = isAnomalyStep ? anomaly.getCycleDurationS() : null;
                    Double over = isAnomalyStep ? anomaly.getDurationOverrunS() : null;

                    // Machine code : si le step a sa machine => meilleur que anomaly.getMachine()
                    String machineCode = (ps != null && ps.getMachine() != null)
                            ? ps.getMachine().getCode()
                            : (anomaly.getMachine() != null ? anomaly.getMachine().getCode() : null);

                    return new CycleStepDto(
                            machineCode,
                            ps != null ? ps.getStepCode() : null,
                            nominal,
                            real,
                            over,
                            isAnomalyStep
                    );
                })
                .toList();
    }

    private static String extractRules(JsonNode ruleReasons) {
        if (ruleReasons == null || !ruleReasons.isArray()) {
            return null;
        }

        List<String> rules = new ArrayList<>();

        for (JsonNode entry : ruleReasons) {
            JsonNode ruleNode = entry.get("rule");
            if (ruleNode != null && ruleNode.isTextual()) {
                rules.add(ruleNode.asText());
            }
        }

        return rules.isEmpty() ? null : String.join(", ", rules);
    }

}