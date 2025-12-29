package supervision.industrial.auto_pilot.api.dto;

import java.time.OffsetDateTime;

public record CycleStepDto(
        String machineCode,
        String stepCode,
        Double nominalDurationS,
        Double realDurationS,
        Double overrunS,
        boolean anomalyDetected
) {}