package supervision.industrial.auto_pilot.controller;

import supervision.industrial.auto_pilot.dto.PageResponse;
import supervision.industrial.auto_pilot.dto.PartDetailResponse;
import dependancy_bundle.model.Part;
import supervision.industrial.auto_pilot.service.PartHandler;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/parts")
public class PartController {

    private final PartHandler service;

    public PartController(PartHandler service) {
        this.service = service;
    }

    @GetMapping
    public PageResponse<Part> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(name = "page_size", defaultValue = "25") int pageSize
    ) {
        List<Part> items = service.listParts(page, pageSize);
        long total = service.countParts();
        return new PageResponse<>(items, total, page, pageSize);
    }

    @GetMapping("/{partId}")
    public PartDetailResponse detail(
            @PathVariable String partId,
            @RequestParam(defaultValue = "200") int events_limit,
            @RequestParam(defaultValue = "200") int anomalies_limit
    ) {
        return service.getPartDetail(partId, events_limit, anomalies_limit);
    }
}
