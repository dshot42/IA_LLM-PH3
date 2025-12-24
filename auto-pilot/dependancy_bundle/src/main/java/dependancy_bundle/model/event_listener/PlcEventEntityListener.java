package dependancy_bundle.model.event_listener;

import jakarta.persistence.PostPersist;
import dependancy_bundle.model.PlcEvent;

public class PlcEventEntityListener {

    @PostPersist
    public void afterInsert(PlcEvent event) {
        PlcEventSpringPublisher.publish(event);
    }
}
