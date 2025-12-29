package supervision.industrial.auto_pilot.workflow.detector;

import dependancy_bundle.model.Machine;
import dependancy_bundle.model.ProductionStep;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Tuple;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.workflow.detector.dto.OccurrenceStats;
import supervision.industrial.auto_pilot.workflow.detector.dto.StepIntervalStats;

import java.time.OffsetDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class StepStatsService {

    private final EntityManager em;

    // =========================================================
    // 1) INTERVALLE TEMPS ENTRE STEPS (terrain)
    // =========================================================
    public StepIntervalStats intervalStats(
            Machine machine,
            ProductionStep productionStep,
            OffsetDateTime since
    ) {
        String sql =
                "with e as ( " +
                        "  select ts, lag(ts) over (partition by part_id order by ts) as prev_ts " +
                        "  from plc_events " +
                        "  where machine_id = :machineId " +
                        "    and production_step_id = :stepId " +
                        "    and ts >= :since " +
                        "), d as ( " +
                        "  select extract(epoch from (ts - prev_ts)) as dt_s " +
                        "  from e where prev_ts is not null and ts >= prev_ts " +
                        ") " +
                        "select count(*) as n, " +
                        "       avg(dt_s) as mean_s, " +
                        "       stddev_samp(dt_s) as std_s, " +
                        "       percentile_cont(0.95) within group (order by dt_s) as p95_s " +
                        "from d";

        Tuple t = (Tuple) em.createNativeQuery(sql, Tuple.class)
                .setParameter("machineId", machine.getId())
                .setParameter("stepId", productionStep.getId())
                .setParameter("since", since)
                .getSingleResult();

        long n = ((Number) t.get("n")).longValue();
        double mean = t.get("mean_s") != null ? ((Number) t.get("mean_s")).doubleValue() : 0.0;
        double std = t.get("std_s") != null ? ((Number) t.get("std_s")).doubleValue() : 0.0;
        double p95 = t.get("p95_s") != null ? ((Number) t.get("p95_s")).doubleValue() : 0.0;

        return new StepIntervalStats(n, mean, std, p95);
    }

    // =========================================================
    // 2) TAUX D’ANOMALIES (macro)
    // =========================================================
    public OccurrenceStats anomalyOccurrenceRate(
            Machine machine,
            ProductionStep productionStep,
            OffsetDateTime since,
            int windowDays
    ) {
        String sql =
                "select count(*) " +
                        "from plc_anomalies " +
                        "where machine_id = :machineId " +
                        "  and production_step_id = :stepId " +
                        "  and ts_detected >= :since";

        Number n = (Number) em.createNativeQuery(sql)
                .setParameter("machineId", machine.getId())
                .setParameter("stepId", productionStep.getId())
                .setParameter("since", since)
                .getSingleResult();

        long occurrences = n.longValue();
        double ratePerDay = occurrences / Math.max(1.0, windowDays);
        return new OccurrenceStats(occurrences, ratePerDay);
    }

    // =========================================================
    // 3) SÉRIE JOURNALIÈRE DES ANOMALIES (fallback)
    // =========================================================
    public double[] dailyOccurrenceSeries(
            Machine machine,
            ProductionStep productionStep,
            OffsetDateTime since
    ) {
        String sql = """             
                with days as (
                select generate_series(
                date_trunc('day', CAST(:since AS timestamptz)),
                date_trunc('day', now()),
                interval '1 day'
                  ) as day
                ),
                a as (
                        select date_trunc('day', ts_detected) as day, count(*) as n
                        from plc_anomalies
                        where machine_id = :machineId
                        and production_step_id = :stepId
                        and ts_detected >= :since
                        group by 1
                )
                select coalesce(a.n,0) as n
                from days d left join a on a.day = d.day
                order by d.day
                """;

        @SuppressWarnings("unchecked")
        List<Number> rows = em.createNativeQuery(sql)
                .setParameter("machineId", machine.getId())
                .setParameter("stepId", productionStep.getId())
                .setParameter("since", since)
                .getResultList();

        double[] x = new double[rows.size()];
        for (int i = 0; i < x.length; i++) {
            x[i] = rows.get(i).doubleValue();
        }
        return x;
    }

    // =========================================================
    // 4) ⭐ SÉRIE JOURNALIÈRE DES ERREURS SIMILAIRES (CLÉ)
    // =========================================================
    public double[] dailySimilarErrorSeries(
            Machine machine,
            ProductionStep productionStep,
            String errorCode,
            OffsetDateTime since
    ) {
        String sql =
                "with days as ( " +
                        "  select generate_series( " +
                        "    date_trunc('day', CAST(:since AS timestamptz)),\n" +
                        "    date_trunc('day', now()), " +
                        "    interval '1 day' " +
                        "  ) as day " +
                        "), e as ( " +
                        "  select date_trunc('day', ts) as day, count(*) as n " +
                        "  from plc_events " +
                        "  where machine_id = :machineId " +
                        "    and production_step_id = :stepId " +
                        "    and level = 'ERROR' " +
                        "    and code = :code " +
                        "    and ts >= :since " +
                        "  group by 1 " +
                        ") " +
                        "select coalesce(e.n,0) as n " +
                        "from days d left join e on e.day = d.day " +
                        "order by d.day";

        @SuppressWarnings("unchecked")
        List<Number> rows = em.createNativeQuery(sql)
                .setParameter("machineId", machine.getId())
                .setParameter("stepId", productionStep.getId())
                .setParameter("code", errorCode)
                .setParameter("since", since)
                .getResultList();

        double[] x = new double[rows.size()];
        for (int i = 0; i < x.length; i++) {
            x[i] = rows.get(i).doubleValue();
        }
        return x;
    }
}
