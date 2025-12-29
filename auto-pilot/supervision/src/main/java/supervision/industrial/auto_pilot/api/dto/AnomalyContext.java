package supervision.industrial.auto_pilot.api.dto;


import dependancy_bundle.model.PlcAnomaly;

import java.time.OffsetDateTime;
import java.util.List;

public record AnomalyContext(

        // =====================
        // IDENTITÉ
        // =====================
        String anomalyId,
        String workorderId,
        String partId,

        // =====================
        // MACHINE / STEP
        // =====================
        String machineCode,
        String machineName,
        String stepCode,
        String stepName,

        // =====================
        // TEMPS
        // =====================
        Double nominalDurationS,
        Double realDurationS,
        Double overrunS,

        // =====================
        // RÈGLES
        // =====================
        List<RuleContextDto> triggeredRules,
        boolean hasPlcError,

        // =====================
        // RÉCURRENCE / STATS
        // =====================
        long similarOccurrences,
        double ewmaRatio,
        double rateRatio,
        int hawkesScore,
        double zScore,
        boolean reinforcingOverTime,

        // =====================
        // SCORE & SÉVÉRITÉ
        // =====================
        String severity,
        double anomalyScore,

        // =====================
        // TRACE CYCLE (OPTIONNEL MAIS PUISSANT)
        // =====================
        ReccurenceAnomalyAnalyseDto reccurenceAnomalyAnalyseDto,

        List<CycleStepDto> cycleTrace,
        String detectedAt,
        List<PlcAnomalyDto> allSimilarAnomalies

) {
}

