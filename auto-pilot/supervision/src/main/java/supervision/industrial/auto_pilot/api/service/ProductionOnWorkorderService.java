package supervision.industrial.auto_pilot.api.service;

import dependancy_bundle.model.ProductionScenario;
import dependancy_bundle.model.Workorder;
import dependancy_bundle.repository.WorkorderRepository;
import jakarta.persistence.EntityManager;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ProductionOnWorkorderService {

    private final EntityManager em;
    private final WorkorderRepository workorderRepository;


    // ============================================================
    // TRS
    // ============================================================
    public record TrsResponse(
            double trs,
            double performance,
            double quality,
            long totalCycles,
            long goodCycles,
            long badCycles,
            double totalTheoreticalTimeS,
            double totalRealTimeS
    ) {
    }

    @Transactional(readOnly = true)
    public TrsResponse getTRS(OffsetDateTime start, OffsetDateTime end) {

        List<Workorder> workorders =
                workorderRepository.findAllByStartedAtBetween(start, end);

        if (workorders.isEmpty()) return emptyTrs();

        long totalCycles = 0;
        long goodCycles = 0;
        double totalRealTimeS = 0.0;
        double totalTheoreticalTimeS = 0.0;

        for (Workorder wo : workorders) {

            ProductionScenario scenario = wo.getProductionScenario();
            if (scenario == null) continue;

            double cycleTheoreticalS = computeTheoreticalCycle(scenario);
            if (cycleTheoreticalS <= 0) continue;

            List<CycleRow> cycles = fetchCyclesForWorkorder(wo.getId(), start, end);

            for (CycleRow c : cycles) {
                if (c.startTs() == null || c.endTs() == null) continue;

                double realTime = Duration.between(c.startTs(), c.endTs()).toSeconds();
                if (realTime <= 0) continue;

                totalCycles++;
                totalRealTimeS += realTime;
                totalTheoreticalTimeS += cycleTheoreticalS;

                if (!c.hasError()) goodCycles++;
            }
        }

        if (totalCycles == 0 || totalRealTimeS <= 0) return emptyTrs();

        double performance = clamp(totalTheoreticalTimeS / totalRealTimeS, 0.0, 1.0);
        double quality = (double) goodCycles / (double) totalCycles;
        double trs = performance * quality;

        return new TrsResponse(
                round4(trs),
                round4(performance),
                round4(quality),
                totalCycles,
                goodCycles,
                totalCycles - goodCycles,
                round4(totalTheoreticalTimeS),
                round4(totalRealTimeS)
        );
    }

    private double computeTheoreticalCycle(ProductionScenario scenario) {
        // Somme des nominalDurationS par step (scenarioStep -> productionStep.nominalDurationS)
        if (scenario.getProductionScenarioSteps() == null) return 0.0;

        return scenario.getProductionScenarioSteps()
                .stream()
                .filter(pss -> pss.getProductionStep() != null)
                .map(pss -> pss.getProductionStep().getNominalDurationS())
                .filter(d -> d != null && d > 0)
                .mapToDouble(Double::doubleValue)
                .sum();
    }

    private List<CycleRow> fetchCyclesForWorkorder(Long workorderId, OffsetDateTime start, OffsetDateTime end) {

        @SuppressWarnings("unchecked")
        List<Object[]> rows = em.createNativeQuery("""
                            SELECT
                              cycle,
                              MIN(ts) AS start_ts,
                              MAX(ts) AS end_ts,
                              BOOL_OR(level = 'ERROR') AS has_error
                            FROM plc_events
                            WHERE workorder_id = :wo
                              AND ts BETWEEN :start AND :end
                              AND cycle IS NOT NULL
                            GROUP BY cycle
                            ORDER BY MIN(ts)
                        """)
                .setParameter("wo", workorderId)
                .setParameter("start", start)
                .setParameter("end", end)
                .getResultList();

        return rows.stream().map(r -> {
            Integer cycle = (r[0] == null) ? null : ((Number) r[0]).intValue();
            OffsetDateTime startTs = toOffsetDateTime(r[1]);
            OffsetDateTime endTs = toOffsetDateTime(r[2]);
            boolean hasError = (r[3] != null) && (Boolean) r[3];
            return new CycleRow(cycle, startTs, endTs, hasError);
        }).toList();
    }

    private OffsetDateTime toOffsetDateTime(Object v) {
        if (v == null) return null;
        if (v instanceof OffsetDateTime odt) return odt;
        if (v instanceof Timestamp ts) return ts.toInstant().atOffset(ZoneOffset.UTC);
        if (v instanceof java.util.Date d) return d.toInstant().atOffset(ZoneOffset.UTC);
        // fallback (rare)
        return null;
    }

    // ============================================================
    // Utils
    // ============================================================
    private TrsResponse emptyTrs() {
        return new TrsResponse(0, 0, 0, 0, 0, 0, 0, 0);
    }

    private long toLong(Object o) {
        if (o == null) return 0L;
        return ((Number) o).longValue();
    }

    private double toDouble(Object o) {
        if (o == null) return 0.0;
        return ((Number) o).doubleValue();
    }

    private double clamp(double v, double min, double max) {
        return Math.max(min, Math.min(v, max));
    }

    private double round4(double v) {
        return Math.round(v * 10_000.0) / 10_000.0;
    }

    private record CycleRow(
            Integer cycle,
            OffsetDateTime startTs,
            OffsetDateTime endTs,
            boolean hasError
    ) {
    }
}
