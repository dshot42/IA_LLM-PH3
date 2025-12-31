package supervision.industrial.auto_pilot.workflow.productionHandler;

import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.model.enumeration.WorkorderStatus;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.ProductionStepRepository;
import dependancy_bundle.repository.WorkorderRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.api.websocket.WorkorderWebSocketUpdate;

import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;

@Service
public class WorkorderHandler {

    private final WorkorderRepository workorderRepository;
    private final PlcEventRepository eventRepo;
    private final PlcAnomalyRepository anomalyRepo;
    private final WorkorderWebSocketUpdate workorderWebSocketUpdate;
    private final ProductionStepRepository productionStepRepo;

    @Autowired
    public WorkorderHandler(ProductionStepRepository productionStepRepo, WorkorderRepository workorderRepository, PlcEventRepository eventRepo, PlcAnomalyRepository anomalyRepo, WorkorderWebSocketUpdate workorderWebSocketUpdate) {
        this.productionStepRepo = productionStepRepo;
        this.workorderRepository = workorderRepository;
        this.eventRepo = eventRepo;
        this.anomalyRepo = anomalyRepo;
        this.workorderWebSocketUpdate = workorderWebSocketUpdate;
    }


    public ProductionStep getLastProductionStep(Workorder wo) {
        if (wo == null
                || wo.getProductionScenario() == null
                || wo.getProductionScenario().getProductionScenarioSteps() == null) {
            return null;
        }

        ProductionStep lastProdStep = wo
                .getProductionScenario()
                .getProductionScenarioSteps()
                .stream()
                .max(Comparator.comparing(ProductionScenarioStep::getStepOrder))
                .map(ProductionScenarioStep::getProductionStep) // 👈 clé ici
                .orElse(null);

        return productionStepRepo.findById(lastProdStep.getId()).get();
    }

    public List<ProductionStep> getProductionSteps(Workorder wo) {
        if (wo == null
                || wo.getProductionScenario() == null
                || wo.getProductionScenario().getProductionScenarioSteps() == null) {
            return List.of();
        }

        return wo.getProductionScenario()
                .getProductionScenarioSteps()
                .stream()
                .sorted(Comparator.comparingLong(ProductionScenarioStep::getStepOrder)) // adapte le getter
                .map(ProductionScenarioStep::getProductionStep)
                .toList();
    }


    public List<ProductionScenarioStep> getProductionScenarioStep(Workorder wo) {
        if (wo == null
                || wo.getProductionScenario() == null
                || wo.getProductionScenario().getProductionScenarioSteps() == null) {
            return null;
        }

        return wo
                .getProductionScenario()
                .getProductionScenarioSteps();
    }

    public void computeWorkorder(PlcEvent event) {
        this.updateState(event);
        this.updateCpt(event);
    }

    public void updateCpt(PlcEvent event) {
        // check anomalie sur piece pour les autres cas
        if (event.getProductionStep().getId().equals(this.getLastProductionStep(event.getWorkorder()).getId())) {
            Workorder workorder = event.getWorkorder();
            workorder.setNbPartFinish(workorder.getNbPartFinish() + 1);
            workorderRepository.save(workorder);
            workorderWebSocketUpdate.emitWorkorderCompleted(workorder);
        }
    }

    public void updateState(PlcEvent event) {
        Workorder workorder = event.getWorkorder();

        if (workorder.getStatus().equals(WorkorderStatus.WAIT.toString())) {
            workorder.setStatus(WorkorderStatus.IN_PROGRESS.toString());
            workorder.setStartedAt(OffsetDateTime.now());
        }

        if (workorder.getStatus().equals(WorkorderStatus.IN_PROGRESS.toString())) {
            Long cptPart = workorder.getNbPartFinish() + workorder.getNbPartScrapped() + workorder.getNbPartRejected();
            if (cptPart.equals(workorder.getNbPartToProduce())) {
                workorder.setStatus(WorkorderStatus.FINISH.toString());
                workorder.setFinishedAt(OffsetDateTime.now());
            }
        }
    }
}
