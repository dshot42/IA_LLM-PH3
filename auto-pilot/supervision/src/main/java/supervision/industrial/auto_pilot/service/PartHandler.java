package supervision.industrial.auto_pilot.service;

import supervision.industrial.auto_pilot.dto.PartDetailResponse;
import dependancy_bundle.model.Part;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.repository.PartRepository;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PartHandler {

    private final PartRepository partRepo;
    private final PlcEventRepository eventRepo;
    private final PlcAnomalyRepository anomalyRepo;

    public PartHandler(PartRepository partRepo, PlcEventRepository eventRepo, PlcAnomalyRepository anomalyRepo) {
        this.partRepo = partRepo;
        this.eventRepo = eventRepo;
        this.anomalyRepo = anomalyRepo;
    }

    public List<Part> listParts(int page, int pageSize) {
        return partRepo.findAll(PageRequest.of(page, pageSize)).getContent();
    }

    public long countParts() {
        return partRepo.count();
    }

    public PartDetailResponse getPartDetail(String partId, int eventsLimit, int anomaliesLimit) {
        // In Python you used raw SQL to fetch steps/machine cycles.
        // Here we expose core information: last events + anomalies for that part.
        List<PlcEvent> events = eventRepo.findByPartIdOrderByTsDesc(partId, PageRequest.of(0, eventsLimit)).getContent();
        List<PlcAnomaly> anomalies = anomalyRepo.findByPartIdOrderByTsDetectedDesc(partId, PageRequest.of(0, anomaliesLimit)).getContent();
        return new PartDetailResponse(partId, events, anomalies);
    }
}
