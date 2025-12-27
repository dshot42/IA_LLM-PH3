package supervision.industrial.auto_pilot.service.detector.rules;

import com.fasterxml.jackson.databind.JsonNode;

public record RuleHit(
        String ruleCode,
        String message,
        JsonNode details
) {}
