package supervision.industrial.auto_pilot.workflow.detector.dto;

import com.fasterxml.jackson.databind.JsonNode;
import supervision.industrial.auto_pilot.api.dto.AnomalyContext;

import java.time.OffsetDateTime;

    public record AnomalyToPromptDto(

            Long id,

            OffsetDateTime tsDetected,
            OffsetDateTime eventTs,

            String partId,
            Integer cycle,
            String machine,

            String stepId,
            String stepName,

            Double anomalyScore,

            Boolean ruleAnomaly,
            JsonNode ruleReasons,

            Boolean hasStepError,
            Integer nStepErrors,

            Double cycleDurationS,
            Double durationOverrunS,

            Integer eventsCount,
            Integer windowDays,

            Double ewmaRatio,
            Double rateRatio,
            Double burstiness,

            Integer hawkesScore,
            String confidence,

            String status,
            String severity,

            OffsetDateTime createdAt,

            AnomalyContext anomalyContext
    ) {}
