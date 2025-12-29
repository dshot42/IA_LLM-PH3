package supervision.industrial.auto_pilot.api.controller;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import supervision.industrial.auto_pilot.api.service.ProductionService;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

@Service
@RestController
@RequestMapping("/api")
public class ProductionController {

    private final ProductionService service;

    public ProductionController(ProductionService service) {
        this.service = service;
    }

    @GetMapping("/production/oee")
    public Object oee(
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime start,

            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime end,

            @RequestParam(name = "line_nominal_s", defaultValue = "90")
            double nominalCycleS
    ) {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);

        OffsetDateTime effectiveStart =
                (start != null) ? start : now.minusHours(1);

        OffsetDateTime effectiveEnd =
                (end != null) ? end : now;

        return service.getOEE(
                effectiveStart,
                effectiveEnd,
                nominalCycleS
        );
    }


    @GetMapping("/production/trs")
    public ProductionService.TrsResponse detail(
            @RequestParam() OffsetDateTime start,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime end
    ) {
        OffsetDateTime effectiveEnd =
                (end != null) ? end : OffsetDateTime.now();

        return service.getTRS(start, end);
    }
}
