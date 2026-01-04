package supervision.industrial.auto_pilot.api.dto;

import com.fasterxml.jackson.databind.JsonNode;

public record RuleContextDto(
        String ruleCode,
        String message,
        JsonNode details
) {}