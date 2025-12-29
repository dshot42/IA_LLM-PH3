package supervision.industrial.auto_pilot.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import dependancy_bundle.model.Part;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.repository.PartRepository;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.api.dto.PartDetailResponse;
import supervision.industrial.auto_pilot.api.dto.SkipPLCEvent;

import java.util.List;
import java.util.Map;

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

    @Autowired
    private ObjectMapper objectMapper;

    @PostConstruct
    public void configureMapper() {
        objectMapper.addMixIn(Part.class, SkipPLCEvent.class);
    }


    public List<Object> listParts(int page, int pageSize) {
        return partRepo
                .findAll(PageRequest.of(page, pageSize))
                .getContent()
                .stream()
                .map(part -> (Object) objectMapper.valueToTree(part))
                .toList();
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
