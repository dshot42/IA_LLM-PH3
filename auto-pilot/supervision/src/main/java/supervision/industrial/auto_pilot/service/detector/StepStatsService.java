package supervision.industrial.auto_pilot.service.detector;


import jakarta.persistence.EntityManager;
import jakarta.persistence.Tuple;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.service.detector.dto.OccurrenceStats;
import supervision.industrial.auto_pilot.service.detector.dto.StepIntervalStats;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * Stats historiques sur fenêtre glissante via SQL natif (PostgreSQL/Timescale).
 * Adapte les noms de tables/colonnes selon ton schéma réel.
 */
@Service
@RequiredArgsConstructor
public class StepStatsService {

    private final EntityManager em;

    public StepIntervalStats intervalStats(String machine, String stepId, OffsetDateTime since) {
        String sql =
            "with e as ( " +
            "  select ts, lag(ts) over (partition by part_id order by ts) as prev_ts " +
            "  from plc_events " +
            "  where machine = :machine and step_id = :stepId and ts >= :since " +
            "), d as ( " +
            "  select extract(epoch from (ts - prev_ts)) as dt_s " +
            "  from e where prev_ts is not null and ts >= prev_ts " +
            ") " +
            "select count(*) as n, coalesce(avg(dt_s),0) as mean_s, " +
            "       coalesce(stddev_samp(dt_s),0) as std_s, " +
            "       coalesce(percentile_cont(0.95) within group (order by dt_s),0) as p95_s " +
            "from d";

        Tuple t = (Tuple) em.createNativeQuery(sql, Tuple.class)
                .setParameter("machine", machine)
                .setParameter("stepId", stepId)
                .setParameter("since", since)
                .getSingleResult();

        long n = ((Number) t.get("n")).longValue();
        double mean = ((Number) t.get("mean_s")).doubleValue();
        double std = ((Number) t.get("std_s")).doubleValue();
        double p95 = ((Number) t.get("p95_s")).doubleValue();

        return new StepIntervalStats(n, mean, std, p95);
    }

    public OccurrenceStats anomalyOccurrenceRate(String machine, String stepId, OffsetDateTime since, int windowDays) {
        String sql =
            "select count(*) as n " +
            "from plc_anomalies " +
            "where machine = :machine and step_id = :stepId and ts_detected >= :since";

        Number n = (Number) em.createNativeQuery(sql)
                .setParameter("machine", machine)
                .setParameter("stepId", stepId)
                .setParameter("since", since)
                .getSingleResult();

        long occurrences = n.longValue();
        double ratePerDay = occurrences / Math.max(1.0, windowDays);
        return new OccurrenceStats(occurrences, ratePerDay);
    }

    public double[] dailyOccurrenceSeries(String machine, String stepId, OffsetDateTime since) {
        String sql =
            "with days as ( " +
            "  select generate_series(date_trunc('day', :since::timestamptz), date_trunc('day', now()::timestamptz), interval '1 day') as day " +
            "), a as ( " +
            "  select date_trunc('day', ts_detected) as day, count(*) as n " +
            "  from plc_anomalies " +
            "  where machine = :machine and step_id = :stepId and ts_detected >= :since " +
            "  group by 1 " +
            ") " +
            "select coalesce(a.n,0) as n " +
            "from days d left join a on a.day = d.day " +
            "order by d.day asc";

        @SuppressWarnings("unchecked")
        List<Number> rows = em.createNativeQuery(sql)
                .setParameter("machine", machine)
                .setParameter("stepId", stepId)
                .setParameter("since", since)
                .getResultList();

        double[] x = new double[rows.size()];
        for (int i = 0; i < x.length; i++) x[i] = rows.get(i).doubleValue();
        return x;
    }
}
