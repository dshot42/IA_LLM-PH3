package supervision.industrial.auto_pilot.workflow.workflowService;

import dependancy_bundle.model.Machine;
import dependancy_bundle.model.Part;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.repository.MachineRepository;
import dependancy_bundle.repository.PartRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.ProductionStepRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import supervision.industrial.auto_pilot.workflow.detector.PlcAnomalyDetectionService;
import supervision.industrial.auto_pilot.workflow.detector.WorkflowNominalService;
import supervision.industrial.auto_pilot.websocket.PartWebSocketUpdate;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Set;

/**
 * Orchestration métier de fin de vie d'une pièce.
 * <p>
 * RESPONSABILITÉS :
 * - décider quand une pièce est REJECTED / SCRAPPED / FINISHED
 * - déclencher l'analyse d'anomalies UNIQUEMENT à ces moments
 * <p>
 * AUCUNE logique de détection ici.
 */

@Service
@RequiredArgsConstructor
public class PartLifeCycleHandler {

    private final PartRepository partRepository;
    private final PlcEventRepository plcEventRepository;
    private final PlcAnomalyDetectionService anomalyDetectionService;
    private final WorkflowNominalService workflowNominalService;
    private final ProductionStepRepository productionStepRepository;
    private final MachineRepository machineRepository;
    private final WorkorderHandler workorderHandler;
    private final PartWebSocketUpdate partWebSocketUpdate;

    // =========================
    // ENTRY POINT
    // =========================

    private boolean isTerminalStatus(Part part) {
        return part.getStatus() != null &&
                (part.getStatus().equals("FINISHED")
                        || part.getStatus().equals("SCRAPPED")
                        || part.getStatus().equals("REJECTED"));
    }


    @Transactional
    public void updatePartFromEvent(PlcEvent event,boolean endCycle) {

        System.out.println("New Event receive : " + event.getProductionStep().getStepCode());

        if (event.getPart() == null) {
            return;
        }

        // 1️⃣ Reject immédiat sur erreur
        if (!endCycle || tryRejectFromError(event)) {
            triggerAnomalyDetection(event.getPart());
            return;
        }

        // 2️⃣ Scrap critique
        if (tryScrap(event)) {
            triggerAnomalyDetection(event.getPart());
            return;
        }

        // 3️⃣ Fin normale de pièce
        if (tryFinish(event)) {
            triggerAnomalyDetection(event.getPart());
        }

    }

    // =========================
    // REJECT
    // =========================

    private boolean tryRejectFromError(PlcEvent event) {

        if (!isRejectingError(event)) return false;

        Part part = partRepository
                .findByExternalPartId(event.getPart().getExternalPartId())
                .orElse(null);

        if (part == null || isTerminalStatus(part)) {
            return false;
        }

        part.setStatus("REJECTED");
        part.setFinishedAt(event.getTs() != null ? event.getTs() : OffsetDateTime.now());
        partRepository.save(part);
        workorderHandler.computeWorkorder(event);

        partWebSocketUpdate.emitPartCompleted();

        return true;
    }

    private boolean isRejectingError(PlcEvent event) {
        if ("ERROR".equalsIgnoreCase(event.getLevel())) return true;
        return event.getCode() != null &&
                (event.getCode().startsWith("E-") || event.getCode().startsWith("ERROR"));
    }

    // =========================
    // SCRAP
    // =========================

    private static final Set<String> CRITICAL_SCRAP_CODES = Set.of(
            // si necessaire cas speciaux
    );

    private boolean tryScrap(PlcEvent event) {

        if (event.getCode() == null) return false;
        if (!CRITICAL_SCRAP_CODES.contains(event.getCode())) return false;

        Part part = partRepository
                .findByExternalPartId(event.getPart().getExternalPartId())
                .orElse(null);

        if (part == null || isTerminalStatus(part)) {
            return false;
        }

        part.setStatus("SCRAPPED");
        part.setFinishedAt(event.getTs() != null ? event.getTs() : OffsetDateTime.now());

        partRepository.save(part);
        workorderHandler.computeWorkorder(event);
        partWebSocketUpdate.emitPartCompleted();

        return true;
    }

    // =========================
    // FINISH
    // =========================

    private boolean tryFinish(PlcEvent event) {
        Machine lastMachine = machineRepository.findFirstByOrderByIdDesc();
        ProductionStep lastStep = productionStepRepository.findFirstByOrderByIdDesc();

        if (!lastMachine.getName().equals(event.getMachine().getName())) return false;
        if (!lastStep.getStepCode().equals(event.getProductionStep().getStepCode())) return false;

        Part part = partRepository
                .findByExternalPartId(event.getPart().getExternalPartId())
                .orElse(null);

        if (part == null || isTerminalStatus(part)) {
            return false;
        }

        part.setStatus("FINISHED");
        part.setFinishedAt(event.getTs() != null ? event.getTs() : OffsetDateTime.now());

        partRepository.save(part);
        partWebSocketUpdate.emitPartCompleted();
        workorderHandler.computeWorkorder(event);

        return true;
    }

    // =========================
    // TRIGGER DETECTION
    // =========================

    private void triggerAnomalyDetection(Part part) {

        OffsetDateTime end = OffsetDateTime.now();
        OffsetDateTime start = end.minusDays(2);

        List<PlcEvent> events = plcEventRepository
                .findByPartAndTsBetween(part, start, end);

        for (PlcEvent e : events) {
            anomalyDetectionService.detectAndPersist(e);
        }
    }
}

