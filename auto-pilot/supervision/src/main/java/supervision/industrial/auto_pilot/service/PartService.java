package supervision.industrial.auto_pilot.service;

import supervision.industrial.auto_pilot.dto.PartDetailResponse;
import supervision.industrial.auto_pilot.model.Part;
import supervision.industrial.auto_pilot.model.PlcAnomaly;
import supervision.industrial.auto_pilot.model.PlcEvent;
import supervision.industrial.auto_pilot.repository.PartRepository;
import supervision.industrial.auto_pilot.repository.PlcAnomalyRepository;
import supervision.industrial.auto_pilot.repository.PlcEventRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PartService {

    private final PartRepository partRepo;
    private final PlcEventRepository eventRepo;
    private final PlcAnomalyRepository anomalyRepo;

    public PartService(PartRepository partRepo, PlcEventRepository eventRepo, PlcAnomalyRepository anomalyRepo) {
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
