package supervision.industrial.auto_pilot.api.controller;

import dependancy_bundle.model.PlcAnomaly;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import supervision.industrial.auto_pilot.api.dto.PageResponse;
import supervision.industrial.auto_pilot.api.service.AnomalyService;

import java.util.List;

@Service
@RestController
@RequestMapping("/api")
public class AnomalyController {

    private final AnomalyService service;

    public AnomalyController(AnomalyService service) {
        this.service = service;
    }

    @GetMapping("/anomalies")
    public PageResponse<Object> list(
            @RequestParam(name = "page", defaultValue = "0") int page,
            @RequestParam(name = "page_size", defaultValue = "25") int pageSize
    ) {
        System.out.println("Anomaly => page: " + page);
        List<Object> items = service.listAnomalies(page - 1, pageSize);
        long total = service.countAnomalys();
        return new PageResponse<>(items, total, page, pageSize);
    }

    @GetMapping("/anomalies/{id}")
    public PlcAnomaly get(@PathVariable Long id) {
        return service.anomalyRepo
                .findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "PlcAnomaly not found with id " + id
                ));
    }


    @PostMapping
    public PlcAnomaly create(@RequestBody PlcAnomaly anomaly) {
        return service.anomalyRepo.save(anomaly);
    }
}
