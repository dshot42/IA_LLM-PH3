package supervision.industrial.auto_pilot.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class AnomalyService {


    public final PlcAnomalyRepository anomalyRepo;

    public AnomalyService(PlcAnomalyRepository anomalyRepo) {
        this.anomalyRepo = anomalyRepo;
    }

    @Autowired
    private ObjectMapper objectMapper;

    public List<Object> listAnomalies(int page, int pageSize) {
        return anomalyRepo
                .findAll(PageRequest.of(page, pageSize))
                .getContent()
                .stream()
                .map(a -> {
                    Map<String, Object> map =
                            objectMapper.convertValue(a, Map.class);
                    map.remove("plcEvents");

                    return (Object) map;
                })
                .toList();
    }


    public long countAnomalys() {
        return anomalyRepo.count();
    }


    public Page<PlcAnomaly> listByPart(String partId, int page, int pageSize) {
        return anomalyRepo.findByPartIdOrderByTsDetectedDesc(partId, PageRequest.of(page, pageSize));
    }

    public PlcAnomaly get(long id) {
        return anomalyRepo.findById(id).orElseThrow(() -> new IllegalArgumentException("anomaly_not_found"));
    }

}
