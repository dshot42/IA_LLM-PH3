package supervision.industrial.auto_pilot.api.service;

import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import dependancy_bundle.repository.WorkorderRepository;
import jakarta.persistence.EntityManager;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ProductionService {

    private final EntityManager em;
    private final WorkorderRepository workorderRepository;
    private final PlcEventRepository plcEventRepository;
    private final PlcAnomalyRepository plcAnomalyRepository;

    // ============================================================
    // DTO RÉPONSE OEE
    // ============================================================
    public record OeeResponse(
            String from,
            String to,
            double elapsedS,
            double nominalCycleS,
            long totalCycles,
            long goodParts,
            long badParts,
            double downtimeS,
            double availability,
            double performance,
            Double quality,
            Double oee
    ) {
    }

    // ============================================================
    // OEE
    // ============================================================
    @Transactional(readOnly = true)
    public OeeResponse getOEE(
            OffsetDateTime from,
            OffsetDateTime to,
            double nominalCycleS
    ) {
        Map<String, Object> s = fetchOeeSummary(from, to);

        long totalCycles = toLong(s.get("total_cycles"));
        long goodParts = toLong(s.get("good_parts"));
        long badParts = toLong(s.get("bad_parts"));
        double downtimeS = toDouble(s.get("downtime_s"));

        double elapsedS = Math.max(Duration.between(from, to).toSeconds(), 1.0);

        double availability = clamp((elapsedS - downtimeS) / elapsedS, 0.0, 1.0);
        double runtimeS = Math.max(elapsedS - downtimeS, 1.0);

        double performance = clamp((nominalCycleS * totalCycles) / runtimeS, 0.0, 1.5);

        long denom = goodParts + badParts;
        Double quality = denom > 0 ? ((double) goodParts / denom) : null;

        Double oee = (quality != null) ? availability * performance * quality : null;

        return new OeeResponse(
                from.toString(),
                to.toString(),
                elapsedS,
                nominalCycleS,
                totalCycles,
                goodParts,
                badParts,
                downtimeS,
                availability,
                performance,
                quality,
                oee
        );
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> fetchOeeSummary(OffsetDateTime from, OffsetDateTime to) {
        // ✅ Hibernate renvoie 1 ligne -> Object[] ou Map selon config,
        // on force un résultat Map via "unwrap + transformer" = fragile.
        // Alternative robuste : on récupère Object[] et on construit Map nous-mêmes.
        Object[] row = (Object[]) em.createNativeQuery(OEE_SUMMARY)
                .setParameter(1, from)
                .setParameter(2, to)
                .getSingleResult();

        // Ordre = total_cycles, good_parts, bad_parts, downtime_s
        return Map.of(
                "total_cycles", row[0],
                "good_parts", row[1],
                "bad_parts", row[2],
                "downtime_s", row[3]
        );
    }

    private static final String OEE_SUMMARY = """
            WITH w AS (
              SELECT *
              FROM plc_events
              WHERE ts >= ?1 AND ts < ?2
            ),
            cycles AS (
              SELECT COUNT(*)::bigint AS total_cycles
              FROM w
              WHERE message ILIKE '%CYCLE_END%'
            ),
            quality AS (
              SELECT
                COUNT(*) FILTER (
                  WHERE (
                    message ILIKE '%M5_OK%'
                    OR code ILIKE '%M5_OK%'
                    OR (payload ? 'result' AND payload->>'result' ILIKE 'OK')
                  )
                )::bigint AS good_parts,
                COUNT(*) FILTER (
                  WHERE (
                    message ILIKE '%M5_NOK%'
                    OR code ILIKE '%M5_NOK%'
                    OR (payload ? 'result' AND payload->>'result' ILIKE 'NOK')
                  )
                )::bigint AS bad_parts
              FROM w
            ),
            downtime AS (
              SELECT COALESCE(SUM(duration), 0)::numeric AS downtime_s
              FROM w
              WHERE level = 'ERROR' AND duration IS NOT NULL
            )
            SELECT
              (SELECT total_cycles FROM cycles) AS total_cycles,
              (SELECT good_parts FROM quality) AS good_parts,
              (SELECT bad_parts FROM quality) AS bad_parts,
              (SELECT downtime_s FROM downtime) AS downtime_s
            """;

    // ============================================================
    // TRS
    // ============================================================
// ============================================================
// TRS
// ============================================================
    public record TrsResponse(
            double trs,
            double performance,
            double quality,
            long totalSteps,
            long goodSteps,
            long badSteps,
            double totalTheoreticalTimeS,
            double totalRealTimeS
    ) {
    }

    @Transactional(readOnly = true)
    public TrsResponse getTRS(OffsetDateTime start, OffsetDateTime end) {

        // 1️⃣ Charger les events SYSTEM dans la fenêtre temporelle
        List<PlcEvent> events = plcEventRepository
                .findAllByTsBetween(start, end)
                .stream()
                .filter(e ->
                        e.getProductionStep() != null &&
                                "SYSTEM".equals(e.getProductionStep().getStepType())
                )
                .sorted(Comparator.comparing(PlcEvent::getTs))
                .toList();

        if (events.size() < 2) {
            return emptyTrs();
        }

        long totalSteps = 0;
        long goodSteps = 0;

        double totalRealTimeS = 0.0;
        double totalTheoreticalTimeS = 0.0;

        PlcEvent previous = null;
        PlcEvent lastAnomalousEvent = null;

        for (PlcEvent current : events) {

            if (previous == null) {
                previous = current;
                continue;
            }

            boolean previousHadAnomaly =
                    plcAnomalyRepository.findFirstByPlcEventIdOrderByTsDetectedAsc(previous.getId()).isPresent();

            Double nominalS = current.getProductionStep().getNominalDurationS();
            if (nominalS == null || nominalS <= 0) {
                previous = current;
                continue;
            }

            // mémoriser l'event anomalie
            if (previousHadAnomaly) {
                lastAnomalousEvent = previous;
            }

            // si on a une anomalie en attente, on attend le step suivant
            if (lastAnomalousEvent != null) {

                boolean stepChanged = !current.getProductionStep().equals(lastAnomalousEvent.getProductionStep());

                if (stepChanged) {
                    double blockingTimeS = Duration
                            .between(lastAnomalousEvent.getTs(), current.getTs())
                            .toMillis() / 1000.0;

                    if (blockingTimeS > 0) {
                        totalSteps++;
                        totalRealTimeS += blockingTimeS;
                        totalTheoreticalTimeS += nominalS;
                        // NOK => pas goodSteps++
                    }

                    lastAnomalousEvent = null; // consommée
                }

                previous = current;
                continue;
            }


            // =========================
            // CAS 2 : step NORMAL
            // =========================
            double deltaRealS = Duration
                    .between(previous.getTs(), current.getTs())
                    .toMillis() / 1000.0;

            if (deltaRealS > 0) {
                totalSteps++;
                totalRealTimeS += deltaRealS;
                totalTheoreticalTimeS += nominalS;
                goodSteps++;
            }

            previous = current;
        }


        if (totalSteps == 0 || totalRealTimeS <= 0 || totalTheoreticalTimeS <= 0) {
            return emptyTrs();
        }

        // 3️⃣ Indicateurs TRS
        double performance = clamp(
                totalTheoreticalTimeS / totalRealTimeS,
                0.0,
                1.0
        );

        double quality = (double) goodSteps / (double) totalSteps;
        double trs = performance * quality;

        return new TrsResponse(
                round4(trs),
                round4(performance),
                round4(quality),
                totalSteps,
                goodSteps,
                totalSteps - goodSteps,
                round4(totalTheoreticalTimeS),
                round4(totalRealTimeS)
        );
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

    private TrsResponse emptyTrs() {
        return new TrsResponse(0, 0, 0, 0, 0, 0, 0, 0);
    }


}
