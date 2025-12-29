package supervision.industrial.auto_pilot.workflow.detector.rules;



import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionStep;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public record RuleContext(
        PlcEvent event,
        OffsetDateTime previousStepTs,
        PlcEvent previousEventSamePart,
        Map<Long, ProductionStep> nominalByStepId,
        List<ProductionStep> nominalSequence
) {}
