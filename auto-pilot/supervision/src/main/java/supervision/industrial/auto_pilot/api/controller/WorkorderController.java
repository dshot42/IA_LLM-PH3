package supervision.industrial.auto_pilot.api.controller;

import org.springframework.web.bind.annotation.*;
import supervision.industrial.auto_pilot.api.dto.PageResponse;
import supervision.industrial.auto_pilot.api.dto.WorkorderDetailResponse;
import supervision.industrial.auto_pilot.api.service.WorkorderService;

import java.util.List;

@RestController
@RequestMapping("/api/workorders")
public class WorkorderController {

    private final WorkorderService service;

    public WorkorderController(WorkorderService service) {
        this.service = service;
    }

    @GetMapping
    public PageResponse<Object> list(
            @RequestParam(name="page", defaultValue = "0") int page,
            @RequestParam(name = "page_size", defaultValue = "25") int pageSize
    ) {
        List<Object> items = service.listWorkorders(page-1, pageSize);
        long total = service.countWorkorders();
        return new PageResponse<>(items, total, page, pageSize);
    }

    @GetMapping("/{workorderId}")
    public WorkorderDetailResponse detail(
            @PathVariable String workorderId,
            @RequestParam(defaultValue = "200") int events_limit,
            @RequestParam(defaultValue = "200") int anomalies_limit
    ) {
        return service.getWorkorderDetail(workorderId, events_limit, anomalies_limit);
    }
}
