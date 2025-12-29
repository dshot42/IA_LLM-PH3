package supervision.industrial.auto_pilot.workflow.trs;

import dependancy_bundle.model.Workorder;
import jakarta.persistence.EntityManager;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TRSHandler {
    private final EntityManager em;

    public record TrsResult(
            double trs,
            double performance,
            double quality,
            long totalCycles,
            long goodCycles,
            long badCycles,
            double cycleNominalS,
            double realTimeS
    ) {
    }

    @Transactional
    public TrsResult computeTrs(
            Workorder workorder,
            OffsetDateTime start,
            OffsetDateTime end
    ) {

        // =========================
        // 1) Cycle nominal (théorique)
        // =========================
        Double cycleNominalS = em.createQuery("""
                            SELECT SUM(ps.nominalDurationS)
                            FROM ProductionScenarioStep pss
                            JOIN pss.productionStep ps
                            WHERE pss.productionScenario.id = :scenarioId
                              AND ps.nominalDurationS IS NOT NULL
                        """, Double.class)
                .setParameter("scenarioId", workorder.getProductionScenario().getId())
                .getSingleResult();


        if (cycleNominalS == null || cycleNominalS <= 0) {
            throw new IllegalStateException(
                    "Cycle nominal invalide pour le scénario "
                            + workorder.getProductionScenario().getId()
            );
        }

        // =========================
        // 2) Cycles réels
        // =========================
        List<Object[]> rows = em.createNativeQuery("""
                            SELECT
                                e.cycle,
                                MIN(e.ts) AS start_ts,
                                MAX(e.ts) AS end_ts,
                                BOOL_OR(e.level = 'ERROR') AS has_error
                            FROM plc_events e
                            WHERE e.ts BETWEEN :start AND :end
                              AND e.cycle IS NOT NULL
                              AND e.workorder_id = :woId
                            GROUP BY e.cycle
                        """)
                .setParameter("start", start)
                .setParameter("end", end)
                .setParameter("woId", workorder.getId())
                .getResultList();

        if (rows.isEmpty()) {
            return new TrsResult(
                    0.0, 0.0, 0.0,
                    0, 0, 0,
                    cycleNominalS, 0.0
            );
        }

        long totalCycles = 0;
        long goodCycles = 0;
        double realTimeS = 0.0;

        for (Object[] r : rows) {
            OffsetDateTime tsStart = (OffsetDateTime) r[1];
            OffsetDateTime tsEnd = (OffsetDateTime) r[2];
            Boolean hasError = (Boolean) r[3];

            if (tsStart == null || tsEnd == null || tsEnd.isBefore(tsStart)) {
                continue;
            }

            double duration =
                    Duration.between(tsStart, tsEnd).toMillis() / 1000.0;

            if (duration <= 0) continue;

            totalCycles++;
            realTimeS += duration;

            if (!Boolean.TRUE.equals(hasError)) {
                goodCycles++;
            }
        }

        if (totalCycles == 0 || realTimeS <= 0) {
            return new TrsResult(
                    0.0, 0.0, 0.0,
                    0, 0, 0,
                    cycleNominalS, 0.0
            );
        }

        // =========================
        // 3) TRS
        // =========================
        double performance = Math.min(
                (totalCycles * cycleNominalS) / realTimeS,
                1.0
        );

        double quality = (double) goodCycles / totalCycles;
        double trs = performance * quality;

        return new TrsResult(
                round(trs),
                round(performance),
                round(quality),
                totalCycles,
                goodCycles,
                totalCycles - goodCycles,
                round(cycleNominalS),
                round(realTimeS)
        );
    }

    private double round(double v) {
        return Math.round(v * 10_000.0) / 10_000.0;
    }
}