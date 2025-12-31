package supervision.industrial.auto_pilot.workflow.trs;

import com.fasterxml.jackson.databind.JsonNode;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.WorkorderRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.api.service.ProductionService;

import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;


@Service
@RequiredArgsConstructor
public class TRSMainHandler {

    @Autowired
    private final WorkorderRepository workorderRepository;

    @Autowired
    private final ProductionService productionService;

    @Autowired
    private final PlcAnomalyRepository plcAnomalyRepository;

    @Autowired
    private final PlcEventRepository plcEventRepository;


    public record TrsAnalise(
            ProductionService.TrsResponse trs,
            List<StepAnomalyAggregate> impact
    ) {
    }

    public record StepAnomalyAggregate(

            String machineCode,
            String stepCode,

            long occurrences,

            double totalDurationOverrunS,
            double avgDurationOverrunS,

            double avgRateRatio,
            double avgEwmaRatio,
            double avgHawkesScore,

            double stdDevRateRatio,
            double stdDevEwmaRatio,
            double stdDevHawkesScore,

            boolean isReinforcingOverTime,
            // 🆕 NOUVEAU — CAUSALITÉ
            Map<String, Long> anomalyByRule,
            Map<String, Double> overrunDurationByRule,// ex : PLC_ERROR_LEVEL -> 7
            String dominantRule,               // ex : PLC_ERROR_LEVEL
            long dominantRuleOccurrences,      // ex : 7
            double dangerScore
    ) {
    }


    public TrsAnalise trsAnalyse(OffsetDateTime start, OffsetDateTime end) {
        ProductionService.TrsResponse trs = calculateTRBetween2Date(start, end);
        List<StepAnomalyAggregate> anomaliesAggr = getWholeAnomalies(start, end);
        return new TrsAnalise(
                trs,
                anomaliesAggr
        );
    }

    public ProductionService.TrsResponse calculateTRBetween2Date(OffsetDateTime start, OffsetDateTime end) {
        return productionService.getTRS(start, end);
    }

    public List<StepAnomalyAggregate> getWholeAnomalies(OffsetDateTime start, OffsetDateTime end) {

        List<PlcAnomaly> allAnomalies = plcAnomalyRepository.findAllByCreatedAtBetween(start, end);

        Map<String, List<PlcAnomaly>> byStep =
                allAnomalies.stream()
                        .collect(Collectors.groupingBy(a ->
                                a.getMachine().getCode()
                                        + "::"
                                        + a.getProductionStep().getStepCode()
                        ));

        return byStep.values().stream()
                .map(list -> {

                    PlcAnomaly ref = list.get(0);

                    Map<String, Long> byRule =
                            list.stream()
                                    .flatMap(a -> {
                                        JsonNode rr = a.getRuleReasons();
                                        if (rr == null || !rr.isArray()) return Stream.empty();
                                        return StreamSupport.stream(rr.spliterator(), false);
                                    })
                                    .map(r -> r.path("rule").asText("UNKNOWN"))
                                    .collect(Collectors.groupingBy(
                                            r -> r,
                                            Collectors.counting()
                                    ));

                    Map<String, Double> overrunByRule =
                            list.stream()
                                    .filter(a -> a.getDurationOverrunS() != null)
                                    .flatMap(a -> StreamSupport.stream(a.getRuleReasons().spliterator(), false)
                                            .map(r -> Map.entry(
                                                    r.path("rule").asText("UNKNOWN"),
                                                    a.getDurationOverrunS()
                                            )))
                                    .collect(Collectors.groupingBy(
                                            Map.Entry::getKey,
                                            Collectors.summingDouble(Map.Entry::getValue)
                                    ));

                    Map.Entry<String, Long> dominant =
                            byRule.entrySet()
                                    .stream()
                                    .max(Map.Entry.comparingByValue())
                                    .orElse(null);

                    String dominantRule = dominant != null ? dominant.getKey() : "UNKNOWN";
                    long dominantCount = dominant != null ? dominant.getValue() : 0;

                    List<Double> overruns =
                            list.stream()
                                    .map(PlcAnomaly::getDurationOverrunS)
                                    .filter(Objects::nonNull)
                                    .toList();

                    List<Double> rates =
                            list.stream().map(PlcAnomaly::getRateRatio).toList();

                    List<Double> ewmAs =
                            list.stream().map(PlcAnomaly::getEwmaRatio).toList();

                    List<Double> hawkes =
                            list.stream().map(a -> (double) a.getHawkesScore()).toList();

                    // 1️⃣ aggregate SANS dangerScore
                    StepAnomalyAggregate base =
                            new StepAnomalyAggregate(
                                    ref.getMachine().getCode(),
                                    ref.getProductionStep().getStepCode(),

                                    list.size(),

                                    overruns.stream().mapToDouble(Double::doubleValue).sum(),
                                    avg(overruns),

                                    avg(rates),
                                    avg(ewmAs),
                                    avg(hawkes),

                                    stdDev(rates),
                                    stdDev(ewmAs),
                                    stdDev(hawkes),

                                    isReinforcing(list),
                                    byRule,
                                    overrunByRule,
                                    dominantRule,
                                    dominantCount,
                                    0.0
                            );

                    // 2️⃣ calcul du dangerScore
                    double danger =
                            dangerScore(
                                    base,
                                    ref.getRuleReasons(),
                                    ref.getSeverity()
                            );

                    // 3️⃣ aggregate FINAL
                    return new StepAnomalyAggregate(
                            base.machineCode(),
                            base.stepCode(),
                            base.occurrences(),
                            base.totalDurationOverrunS(),
                            base.avgDurationOverrunS(),
                            base.avgRateRatio(),
                            base.avgEwmaRatio(),
                            base.avgHawkesScore(),
                            base.stdDevRateRatio(),
                            base.stdDevEwmaRatio(),
                            base.stdDevHawkesScore(),
                            base.isReinforcingOverTime(),
                            byRule,
                            overrunByRule,
                            dominantRule,
                            dominantCount,
                            danger
                    );
                })
                .toList();
    }

    /// //////// UTILS ///////////

    private boolean isReinforcing(List<PlcAnomaly> anomalies) {

        if (anomalies.size() < 5) return false;

        List<PlcAnomaly> sorted =
                anomalies.stream()
                        .sorted(Comparator.comparing(PlcAnomaly::getCreatedAt))
                        .toList();

        int mid = sorted.size() / 2;

        double earlyAvg = avg(
                sorted.subList(0, mid).stream()
                        .map(PlcAnomaly::getEwmaRatio)
                        .toList()
        );

        double lateAvg = avg(
                sorted.subList(mid, sorted.size()).stream()
                        .map(PlcAnomaly::getEwmaRatio)
                        .toList()
        );

        return lateAvg > earlyAvg * 1.2;
    }

    private double avg(List<Double> v) {
        return v.isEmpty() ? 0.0 :
                v.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
    }

    private double stdDev(List<Double> v) {
        if (v.size() < 2) return 0.0;
        double mean = avg(v);
        double variance = v.stream()
                .mapToDouble(x -> Math.pow(x - mean, 2))
                .average()
                .orElse(0.0);
        return Math.sqrt(variance);
    }

    private static double severityWeight(String severity) {
        return switch (severity) {
            case "CRITICAL" -> 1.00;
            case "MAJOR" -> 0.75;
            case "MINOR" -> 0.40;
            case "INFO" -> 0.15;
            default -> 0.30;
        };
    }

    private static double ruleWeight(String rule) {
        return switch (rule) {
            case "PLC_ERROR_LEVEL" -> 1.00;
            case "SEQUENCE_ERROR" -> 0.90; // sequence non respecté
            case "TIME_OVERRUN" -> 0.60;
            case "QUALITY_NOK" -> 0.80;
            default -> 0.50;
        };
    }

    private double ruleImpactScore(JsonNode ruleReasons) {

        if (ruleReasons == null || !ruleReasons.isArray()) {
            return 0.3;
        }

        double max = 0.0;

        for (JsonNode r : ruleReasons) {
            String rule = r.path("rule").asText("");
            max = Math.max(max, ruleWeight(rule));
        }

        return max;
    }

    private double statisticalScore(double ewma, double rate, double hawkes) {

        double s = 0.0;

        if (ewma >= 1.5) s += 0.35;
        if (rate >= 2.0) s += 0.35;
        if (hawkes >= 10) s += 0.30;

        return Math.min(s, 1.0);
    }

    private double recurrenceScore(boolean reinforcing) {
        return reinforcing ? 1.0 : 0.4;
    }

    private double dangerScore(
            StepAnomalyAggregate agg,
            JsonNode ruleReasons,
            String severity
    ) {

        double severityScore = severityWeight(severity);
        double ruleScore = ruleImpactScore(ruleReasons);
        double statScore = statisticalScore(
                agg.avgEwmaRatio(),
                agg.avgRateRatio(),
                agg.avgHawkesScore()
        );
        double recurrence = recurrenceScore(agg.isReinforcingOverTime());

        double raw =
                (0.30 * severityScore) +
                        (0.30 * ruleScore) +
                        (0.25 * statScore) +
                        (0.15 * recurrence);

        return Math.round(raw * 100.0);
    }
}
