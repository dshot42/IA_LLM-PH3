package supervision.industrial.auto_pilot;

import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.RunnerConstante;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.RunnerConstanteRepository;
import dependancy_bundle.repository.WorkorderRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import supervision.industrial.auto_pilot.workflow.productionHandler.PartLifeCycleHandler;
import supervision.industrial.auto_pilot.workflow.productionHandler.WorkorderHandler;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class LaunchDetector {

    private final PlcAnomalyRepository plcAnomalyRepository;
    private final PartLifeCycleHandler partLifeCycleHandler;
    private final PlcEventRepository plcEventRepository;
    private final WorkorderHandler workorderHandler;
    private final RunnerConstanteRepository runnerConstanteRepository;
    private final WorkorderRepository workorderRepository;



    private static final AtomicLong LAST_EVENT_ID = new AtomicLong(0);

    // =========================
    // INIT AU DÉMARRAGE
    // =========================
    @PostConstruct
    public void init() {
        Optional<RunnerConstante> rcOpt =
                runnerConstanteRepository.findAll().stream().findFirst();

        if (rcOpt.isPresent()) {
            LAST_EVENT_ID.set(rcOpt.get().getLastCurrentEvent());
            log.info("[EVENT-POLL] Initial last event id = {}", LAST_EVENT_ID.get());
        } else {
            LAST_EVENT_ID.set(0L);
            log.warn("[EVENT-POLL] RunnerConstante absente → initialisation à 0");
        }
    }

    // =========================
    // LOOP TOUTES LES 10s
    // =========================
    public void pollNewEvents() {
        System.out.println("POLL NEW EVENT");

        Long currentMax = plcEventRepository.findMaxId();
        if (currentMax == null) return;

        long lastSeen = LAST_EVENT_ID.get();
        if (currentMax <= lastSeen) return;

        List<PlcEvent> newEvents =
                plcEventRepository.findAllByIdGreaterThanOrderByIdAsc(lastSeen);

        if (newEvents.isEmpty()) return;

        for (int i = 0; i < newEvents.size(); i++) {

            PlcEvent evt = newEvents.get(i);
            if (evt == null) continue;

            if (plcAnomalyRepository.findByPlcEventId(evt.getId()).isPresent()) {
                log.debug(
                        "[EVENT-POLL] Event {} déjà analysé (anomalie existante), skip",
                        evt.getId()
                );
                continue;
            }

            Optional<Workorder> woOpt =
                    workorderRepository.findById(evt.getWorkorder().getId());

            if (woOpt.isEmpty()) continue;

            Workorder wo = woOpt.get();
            ProductionStep lastProductionStep =
                    workorderHandler.getLastProductionStep(wo);

            if (lastProductionStep == null) continue;

            // =========================
            // CALCUL DURÉE STEP (SAFE)
            // =========================
            Double durationStep = null;

            if (i + 1 < newEvents.size()) {
                PlcEvent nextEvt = newEvents.get(i + 1);
                if (nextEvt != null && nextEvt.getTs() != null && evt.getTs() != null) {
                    durationStep =
                            Duration.between(evt.getTs(), nextEvt.getTs())
                                    .toMillis() / 1000.0;
                }
            }

            boolean isLastScenarioStep =
                    evt.getProductionStep().getId().equals(lastProductionStep.getId());

            // =========================
            // ANOMALIE AVANT FIN DE CYCLE
            // =========================
            if (!isLastScenarioStep) {
                Long lastStepId = lastProductionStep.getId();
                Double lastNominalDuration = lastProductionStep.getNominalDurationS();
                boolean isError = "ERROR".equals(evt.getLevel());
                boolean durationOverrun =
                        durationStep != null
                                && lastNominalDuration != null
                                && durationStep > lastNominalDuration  * MainConfig.toleranceOverrun;

                if (isError || durationOverrun) {
                    log.info("Anomalie détectée sur event {}", evt.getId());
                    partLifeCycleHandler.updatePartFromEvent(evt, false);
                }

                continue;
            }

            // =========================
            // FIN DE CYCLE
            // =========================
            partLifeCycleHandler.updatePartFromEvent(evt, true);
        }

        // ✅ on avance le curseur UNE FOIS, à la fin
        LAST_EVENT_ID.set(currentMax);
        RunnerConstante rc = runnerConstanteRepository.findAll().stream().findFirst().get();
        rc.setLastCurrentEvent(LAST_EVENT_ID.get());
        runnerConstanteRepository.save(rc);
    }
}