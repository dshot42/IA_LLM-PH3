package supervision.industrial.auto_pilot.workflow.detector.dto;

public record OccurrenceStats(
        long occurrences,
        double ratePerDay
) {}
