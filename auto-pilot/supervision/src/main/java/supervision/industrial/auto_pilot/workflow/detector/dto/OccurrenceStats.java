package supervision.industrial.auto_pilot.service.detector.dto;

public record OccurrenceStats(
        long occurrences,
        double ratePerDay
) {}
