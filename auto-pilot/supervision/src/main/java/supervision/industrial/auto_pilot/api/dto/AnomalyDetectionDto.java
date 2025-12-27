package supervision.industrial.auto_pilot.dto;

import com.fasterxml.jackson.databind.JsonNode;

public record AnomalyDetectionDto(
        boolean ruleAnomaly,
        double cycleDuration,
        Double durationOverrun,
        JsonNode ruleReasons,
        String severity
) {}
