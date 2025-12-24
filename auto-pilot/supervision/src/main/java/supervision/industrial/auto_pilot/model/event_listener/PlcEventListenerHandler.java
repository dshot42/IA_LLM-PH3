package supervision.industrial.auto_pilot.model.event_listener;


import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import supervision.industrial.auto_pilot.model.PlcEvent;
import supervision.industrial.auto_pilot.service.PartLifeCycleHandler;

@Slf4j
@Component
@RequiredArgsConstructor
public class PlcEventListenerHandler {

    private final PartLifeCycleHandler partLifecycleOrchestrator;

    /**
     * Déclenché APRÈS COMMIT DB
     */
    @EventListener
    public void onPlcEventInserted(PlcEventSpringPublisher.PlcEventCreatedEvent evt) {

        PlcEvent event = evt.event();

        log.debug("[PLC-LISTENER] New event id={} part={}",
                event.getId(), event.getPartId());

        partLifecycleOrchestrator.updatePartFromEvent(event);
    }
}
