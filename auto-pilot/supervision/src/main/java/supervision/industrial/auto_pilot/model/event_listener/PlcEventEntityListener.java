package supervision.industrial.auto_pilot.model.event_listener;

import jakarta.persistence.PostPersist;
import supervision.industrial.auto_pilot.model.PlcEvent;

public class PlcEventEntityListener {

    @PostPersist
    public void afterInsert(PlcEvent event) {
        PlcEventSpringPublisher.publish(event);
    }
}
