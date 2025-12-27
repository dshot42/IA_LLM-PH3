package supervision.industrial.auto_pilot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.WorkorderRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.dto.WorkorderDetailResponse;

import java.util.Comparator;
import java.util.List;
import java.util.Map;

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

    @Autowired
    private ObjectMapper objectMapper;

    public List<Object> listWorkorders(int page, int pageSize) {
        return workorderRepository
                .findAll(PageRequest.of(page, pageSize))
                .getContent()
                .stream()
                .map(wo -> {
                    Map<String, Object> map =
                            objectMapper.convertValue(wo, Map.class);
                    map.remove("plcEvents");

                    return (Object) map;
                })
                .toList();
    }

    public long countWorkorders() {
        return workorderRepository.count();
    }

    public WorkorderDetailResponse getWorkorderDetail(String workorderId, int eventsLimit, int anomaliesLimit) {
        // Todo display wo
        //   List<PlcEvent> events = eventRepo.findByWorkorderIdOrderByTsDesc(workorderId, PageRequest.of(0, eventsLimit)).getContent();
        //  List<PlcAnomaly> anomalies = anomalyRepo.findByWorkorderIdOrderByTsDetectedDesc(workorderId, PageRequest.of(0, anomaliesLimit)).getContent();
        //   return new WorkorderDetailResponse(workorderId, events, anomalies);
        return null;
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


}
