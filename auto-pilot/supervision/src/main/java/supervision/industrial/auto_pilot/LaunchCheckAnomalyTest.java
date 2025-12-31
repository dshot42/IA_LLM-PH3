package supervision.industrial.auto_pilot;

import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import dependancy_bundle.repository.PlcEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import supervision.industrial.auto_pilot.workflow.detector.PlcAnomalyDetectionService;
import supervision.industrial.auto_pilot.workflow.prompt.TRSPromptHandler;

import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class CheckAnomalyRunner {

    private final PlcAnomalyDetectionService anomalyDetectionService;
    private final PlcEventRepository plcEventRepository;
    private final TRSPromptHandler trsPromptHandler;
    private final PlcAnomalyRepository plcAnomalyRepository;


    public void runCheckAnomaly() {
        System.out.println(">>> StartupRunner runCheckAnomaly ");
        checkAnomalie();
    }

    public void runTrsAnalyse() {
        System.out.println(">>> StartupRunner runTrsAnalyse");
        // ingest anomalies from event obligatoire !
        trsPromptHandler.trsAnalyse(OffsetDateTime.now().minusDays(10000), OffsetDateTime.now());
    }

    private void checkAnomalie() {
        System.out.println("Startup anomaly check");
        List<PlcAnomaly> plcAnomalies = plcAnomalyRepository.findAll()
                .stream()
                //.filter(e -> e.getLevel().equals("ERROR"))
                .sorted(Comparator.comparing(PlcAnomaly::getId).reversed())
                .limit(5)
                .toList();

        System.out.println("Found " + plcAnomalies.size() + " plc anomalies");
        plcAnomalies.forEach(a -> {
            try {
                anomalyDetectionService.anomalyDetection(a.getPlcEvent());
                Thread.sleep(100_000);
            } catch (InterruptedException ex) {
                throw new RuntimeException(ex);
            }
        });
    }


}
