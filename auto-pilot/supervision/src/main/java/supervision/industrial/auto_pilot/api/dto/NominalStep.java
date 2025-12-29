package supervision.industrial.auto_pilot.api.dto;

public record NominalStep(
        String machineCode,
        String stepCode,
        double nominalDurationS,
        int order
) {}
