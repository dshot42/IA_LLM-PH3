package dependancy_bundle.model.event_listener;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import dependancy_bundle.model.PlcEvent;

@Component
public class PlcEventSpringPublisher {

    public record PlcEventCreatedEvent(PlcEvent event) {}
    private static ApplicationEventPublisher publisher;

    public PlcEventSpringPublisher(ApplicationEventPublisher publisher) {
        PlcEventSpringPublisher.publisher = publisher;
    }

    public static void publish(PlcEvent event) {
        publisher.publishEvent(new PlcEventCreatedEvent(event));
    }
}
