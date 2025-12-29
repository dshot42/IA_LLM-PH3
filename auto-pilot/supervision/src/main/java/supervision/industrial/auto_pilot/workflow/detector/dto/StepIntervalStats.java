package supervision.industrial.auto_pilot.workflow.detector.dto;

public record StepIntervalStats(
        long sampleCount,
        double meanS,
        double stdS,
        double p95S
) {
    public double zScore(double valueS) {
        if (sampleCount < 10) return 0.0;
        if (stdS <= 1e-9) return 0.0;
        return (valueS - meanS) / stdS;
    }
}
