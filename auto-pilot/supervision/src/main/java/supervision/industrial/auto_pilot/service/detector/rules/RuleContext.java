package supervision.industrial.auto_pilot.service.detector.rules;



import dependancy_bundle.model.PlcEvent;
import supervision.industrial.auto_pilot.service.detector.dto.NominalStep;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public record RuleContext(
        PlcEvent event,
        OffsetDateTime previousStepTs,
        PlcEvent previousEventSamePart,
        Map<String, NominalStep> nominalByStepId,
        List<NominalStep> nominalSequence
) {}
