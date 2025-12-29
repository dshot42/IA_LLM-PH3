package supervision.industrial.auto_pilot.api.dto;


import java.time.OffsetDateTime;

public record PlcAnomalyDto(

        // =====================
        // MACHINE
        // =====================
        String machineName,

        // =====================
        // PART
        // =====================
        Long partId,
        String partExternalId,

        // =====================
        // PLC EVENT
        // =====================
        String plcEventTs,

        // =====================
        // PRODUCTION STEP
        // =====================
        Long productionStepId,
        String productionStepName,
        String productionStepCode,
        String ruleReason

) {
}
