package supervision.industrial.auto_pilot.workflow.detector.dto;

public record PredictiveSignals(
        int windowDays,
        double ewmaRatio,
        double rateRatio,
        double burstiness,
        int hawkesScore,
        String confidence
) {}
