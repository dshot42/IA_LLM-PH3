package supervision.industrial.auto_pilot.workflow.workflowService;

import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.model.enumeration.WorkorderStatus;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.WorkorderRepository;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;

@Service
public class WorkorderHandler {

    private final WorkorderRepository workorderRepository;
    private final PlcEventRepository eventRepo;
    private final PlcAnomalyRepository anomalyRepo;

    public WorkorderHandler(WorkorderRepository workorderRepository, PlcEventRepository eventRepo, PlcAnomalyRepository anomalyRepo) {
        this.workorderRepository = workorderRepository;
        this.eventRepo = eventRepo;
        this.anomalyRepo = anomalyRepo;
    }



    public ProductionStep getLastProductionStep(Workorder wo) {
        if (wo == null
                || wo.getProductionScenario() == null
                || wo.getProductionScenario().getProductionScenarioSteps() == null) {
            return null;
        }

        return wo
                .getProductionScenario()
                .getProductionScenarioSteps()
                .stream()
                .max(Comparator.comparing(ProductionScenarioStep::getStepOrder))
                .map(ProductionScenarioStep::getProductionStep) // 👈 clé ici
                .orElse(null);
    }

    public List<ProductionStep> getProductionStep(Workorder wo) {
        if (wo == null
                || wo.getProductionScenario() == null
                || wo.getProductionScenario().getProductionScenarioSteps() == null) {
            return null;
        }

        return wo
                .getProductionScenario()
                .getProductionScenarioSteps()
                .stream()
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
