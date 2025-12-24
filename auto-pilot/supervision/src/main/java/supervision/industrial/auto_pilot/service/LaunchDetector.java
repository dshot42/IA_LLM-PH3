package supervision.industrial.auto_pilot.service;


import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.model.PlcEvent;
import supervision.industrial.auto_pilot.model.ProductionScenarioStep;
import supervision.industrial.auto_pilot.model.Workorder;
import supervision.industrial.auto_pilot.repository.PlcEventRepository;
import supervision.industrial.auto_pilot.repository.ProductionScenarioRepository;
import supervision.industrial.auto_pilot.repository.WorkorderRepository;

import java.time.Duration;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class LaunchDetector {

    private final PartLifeCycleHandler partLifeCycleHandler;
    private final PlcEventRepository plcEventRepository;

    @Autowired
    private ProductionScenarioRepository productionScenarioRepository;

    @Autowired
    private WorkorderRepository workorderRepository;

    /**
     * Dernier ID traité (en mémoire)
     */
    private static final AtomicLong LAST_EVENT_ID = new AtomicLong(0);

    // =========================
    // INIT AU DÉMARRAGE
    // =========================

    @PostConstruct
    public void init() {
        Long lastId = plcEventRepository.findMaxId();
        if (lastId != null) {
            LAST_EVENT_ID.set(lastId);
        }
        log.info("[PART-POLL] Initial last part id = {}", LAST_EVENT_ID.get());
    }

    // =========================
    // LOOP TOUTES LES 30s
    // =========================

    @Scheduled(fixedDelay = 30_000) // en ms
    public void pollNewParts() {

        Long currentMax = plcEventRepository.findMaxId();
        if (currentMax == null) return;

        long lastSeen = LAST_EVENT_ID.get();

        if (currentMax > lastSeen) {
            List<PlcEvent> newEvents = plcEventRepository.findAllByIdGreaterThanOrderByIdAsc(lastSeen);
            for (int i = 0; i < newEvents.size(); i++) {
                PlcEvent evt = newEvents.get(i);
                log.info("[PART-POLL] New part detected: {} → {}", lastSeen, currentMax);

                if (evt == null)
                    return;

                // check is lastProductionStep step of scenario process
                Optional<Workorder> wo = workorderRepository.findById(evt.getWorkorder().getId());
                if (wo.isEmpty())
                    return;

                ProductionScenarioStep lastProductionStep =
                        wo.get()
                                .getProductionScenarioStep()
                                .getProductionScenarioSteps()
                                .stream()
                                .max(Comparator.comparing(ProductionScenarioStep::getStepOrder))
                                .orElse(null);
                if (lastProductionStep == null) {
                    System.out.println("[System ERROR] No production scenario step found for workorder ID :" + wo.get().getId());
                    return;
                }

                Double durationStep = null;

                if (newEvents.size() > i + 1) {
                    // check evt not last in stack
                    // on ne fait rien dans ce cas , car la fin peut arriver dans le prochain refresh du timmer,
                    // donc on laisser et on aura la prochaine stack
                    durationStep =
                            Duration.between(evt.getTs(), newEvents.get(i + 1).getTs())
                                    .toMillis() / 1000.0; // en sec
                }

                if (!evt.getStepId().equals(lastProductionStep.getProductionStep().getStepCode())) {
                    System.out.println("Aucune fin de cycle de production detecté !");
                    // on check les erreurs
                    if (evt.getLevel().equals("ERROR") || (durationStep != null && durationStep > lastProductionStep.getProductionStep().getDuration())) {
                        this.handleNewPart(evt, currentMax);
                    }
                    return;
                }
                this.handleNewPart(evt, currentMax);
            }

        } else {
            // pas de nouvelle piece , potientel erreur suivant le timmer et plage horaire
            // check life signal of machine opcua
        }
    }

    private void handleNewPart(PlcEvent event, long currentMax) {
        log.info("[PART-POLL] Handling new event id={} ",
                event.getId());
        LAST_EVENT_ID.set(currentMax);
        partLifeCycleHandler.updatePartFromEvent(event);

    }
}
