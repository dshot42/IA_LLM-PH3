package supervision.industrial.auto_pilot.controller;

import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.dto.PageResponse;
import supervision.industrial.auto_pilot.dto.PartDetailResponse;
import supervision.industrial.auto_pilot.service.PartHandler;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Service
@RestController
@RequestMapping("/api")
public class PartController {

    private final PartHandler service;

    public PartController(PartHandler service) {
        this.service = service;
    }

    @GetMapping("/parts")
    public PageResponse<Object> list(
            @RequestParam(name = "page", defaultValue = "0") int page,
            @RequestParam(name = "page_size", defaultValue = "25") int pageSize
    ) {
        System.out.println("Part => page: " + page);
        List<Object> items = service.listParts(page-1, pageSize);
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
