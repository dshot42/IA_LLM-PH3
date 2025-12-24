package supervision.industrial.auto_pilot.service.factory;

import supervision.industrial.auto_pilot.model.PlcAnomaly;
import supervision.industrial.auto_pilot.model.PlcEvent;
import supervision.industrial.auto_pilot.dto.AnomalyDetectionDto;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;

@Component
public class MapperFactory {

    public PlcAnomaly mapEventToAnomaly(
            PlcEvent event,
            AnomalyDetectionDto r
    ) {
        PlcAnomaly a = new PlcAnomaly();

        // ===== identité industrielle =====
        a.setPlcEvent(event);
        a.setPartId(event.getPartId());
        a.setCycle(event.getCycle());
        a.setMachine(event.getMachine());
        a.setStepId(event.getStepId());
        a.setStepName(event.getStepName());

        // ===== détection =====
        a.setRuleAnomaly(r.ruleAnomaly());
        a.setRuleReasons(r.ruleReasons());
        a.setSeverity(r.severity());

        // ===== métriques =====
        a.setCycleDurationS(r.cycleDuration());
        a.setDurationOverrunS(r.durationOverrun());

        // ===== statut =====
        a.setStatus("OPEN");

        return a;
    }
}
