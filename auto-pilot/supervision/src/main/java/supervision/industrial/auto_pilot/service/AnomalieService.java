package supervision.industrial.auto_pilot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import supervision.industrial.auto_pilot.model.PlcAnomaly;
import supervision.industrial.auto_pilot.repository.PlcAnomalyRepository;
import supervision.industrial.auto_pilot.websocket.AnomalyWebSocketHandler;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

@Service
public class AnomalieService {

    private final PlcAnomalyRepository repo;
    private final AnomalyWebSocketHandler ws;
    private final ObjectMapper objectMapper;

    public AnomalieService(PlcAnomalyRepository repo, AnomalyWebSocketHandler ws, ObjectMapper objectMapper) {
        this.repo = repo;
        this.ws = ws;
        this.objectMapper = objectMapper;
    }

    public Page<PlcAnomaly> list(int page, int pageSize) {
        return repo.findAll(PageRequest.of(
                Math.max(page, 0),
                Math.max(pageSize, 1),
                Sort.by(Sort.Direction.DESC, "tsDetected")
        ));
    }

    public Page<PlcAnomaly> listByPart(String partId, int page, int pageSize) {
        return repo.findByPartIdOrderByTsDetectedDesc(partId, PageRequest.of(page, pageSize));
    }

    public PlcAnomaly get(long id) {
        return repo.findById(id).orElseThrow(() -> new IllegalArgumentException("anomaly_not_found"));
    }

    public PlcAnomaly save(PlcAnomaly a) {
        PlcAnomaly saved = repo.save(a);

        // Push to connected dashboards (replacement for SocketIO emit)
        try {
            ws.broadcastJson(objectMapper.writeValueAsString(saved));
        } catch (Exception ignored) {
        }

        return saved;
    }
}
