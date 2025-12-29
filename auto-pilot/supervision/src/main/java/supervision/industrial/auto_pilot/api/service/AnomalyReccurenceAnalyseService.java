package supervision.industrial.auto_pilot.api.service;

import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.api.dto.ReccurenceAnomalyAnalyseDto;
import supervision.industrial.auto_pilot.workflow.detector.StepStatsService;
import supervision.industrial.auto_pilot.workflow.detector.dto.StepIntervalStats;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Objects;

@Service
@RequiredArgsConstructor
public class AnomalyReccurenceAnalyseService {

    private final StepStatsService stepStatsService;
    private final PlcAnomalyRepository plcAnomalyRepository;

    public ReccurenceAnomalyAnalyseDto analyse(PlcAnomaly a) {

        int windowDays = a.getWindowDays();
        OffsetDateTime since = OffsetDateTime.now().minusDays(windowDays);

        // === INTERVAL STATS ===
        StepIntervalStats intervalStats =
                stepStatsService.intervalStats(
                        a.getMachine(),
                        a.getProductionStep(),
                        since
                );

        // === OVERRUN STATS ===
        List<Double> overruns =
                plcAnomalyRepository.findRecentOverruns(
                        a.getMachine().getId(),
                        a.getProductionStep().getId(),
                        since
                );

        double meanOverrun = overruns.stream()
                .filter(Objects::nonNull)
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0.0);

        double stdOverrun = stdDev(overruns, meanOverrun);

        // === TENDANCES ===
        boolean freqUp = a.getRateRatio() > 1.2;
        boolean overrunUp = a.getEwmaRatio() > 1.2;

        String trend =
                (a.getRateRatio() > 1.5 && a.getEwmaRatio() > 1.5)
                        ? "AGGRAVATION"
                        : (freqUp ? "EN_AUGMENTATION" : "STABLE");

        return new ReccurenceAnomalyAnalyseDto(
                windowDays,
                a.getEventsCount(),

                intervalStats.meanS(),
                intervalStats.stdS(),

                meanOverrun,
                stdOverrun,

                freqUp,
                overrunUp,
                trend
        );
    }

    private double stdDev(List<Double> values, double mean) {
        if (values.size() < 2) return 0.0;
        double s = 0.0;
        for (double v : values) {
            double d = v - mean;
            s += d * d;
        }
        return Math.sqrt(s / (values.size() - 1));
    }
}
