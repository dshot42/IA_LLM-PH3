package supervision.industrial.auto_pilot.service.mapper;

import dependancy_bundle.model.PlcAnomaly;
import supervision.industrial.auto_pilot.service.detector.dto.AnomalyToPromptDto;

public class PlcAnomalyMapper {

    private PlcAnomalyMapper() {
    }

    public static AnomalyToPromptDto toDto(PlcAnomaly a) {

        return new AnomalyToPromptDto(

                a.getId(),

                a.getTsDetected(),
                a.getPlcEvent() != null ? a.getPlcEvent().getTs() : null,

                // part_id attendu TEXT côté Python
                a.getPart() != null
                        ? a.getPart().getExternalPartId()
                        : null,

                a.getCycle(),

                a.getMachine() != null
                        ? a.getMachine().getName()
                        : null,

                a.getProductionStep() != null
                        ? a.getProductionStep().getStepCode()
                        : null,

                a.getProductionStep() != null
                        ? a.getProductionStep().getName()
                        : null,

                a.getAnomalyScore(),

                a.getRuleAnomaly(),
                a.getRuleReasons(),

                a.getHasStepError(),
                a.getNStepErrors(),

                a.getCycleDurationS(),
                a.getDurationOverrunS(),

                a.getEventsCount(),
                a.getWindowDays(),

                a.getEwmaRatio(),
                a.getRateRatio(),
                a.getBurstiness(),

                a.getHawkesScore(),
                a.getConfidence(),

                a.getStatus(),
                a.getSeverity(),

                a.getCreatedAt(),
                a.getReportPath()
        );
    }
}
