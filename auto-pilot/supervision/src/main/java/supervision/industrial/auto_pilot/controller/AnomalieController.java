package supervision.industrial.auto_pilot.controller;

import supervision.industrial.auto_pilot.dto.PageResponse;
import dependancy_bundle.model.PlcAnomaly;
import supervision.industrial.auto_pilot.service.AnomalieService;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/anomalies")
public class AnomalieController {

    private final AnomalieService service;

    public AnomalieController(AnomalieService service) {
        this.service = service;
    }

    @GetMapping
    public PageResponse<PlcAnomaly> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(name = "page_size", defaultValue = "25") int pageSize
    ) {
        Page<PlcAnomaly> p = service.list(page, pageSize);
        return new PageResponse<>(p.getContent(), p.getTotalElements(), page, pageSize);
    }

    @GetMapping("/{id}")
    public PlcAnomaly get(@PathVariable long id) {
        return service.get(id);
    }

    @PostMapping
    public PlcAnomaly create(@RequestBody PlcAnomaly anomaly) {
        return service.save(anomaly);
    }
}
