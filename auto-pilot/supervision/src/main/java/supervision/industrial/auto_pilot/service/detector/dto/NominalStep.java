package supervision.industrial.auto_pilot.service.detector.dto;

public record NominalStep(
        String machine,
        String stepId,
        String stepName,
        Integer orderIndex,
        Double nominalDurationS
) {}
