package supervision.industrial.auto_pilot.workflow.detector.rules;

import com.fasterxml.jackson.databind.JsonNode;

public record RuleHit(
        String ruleCode,
        String message,
        JsonNode details
) {}
