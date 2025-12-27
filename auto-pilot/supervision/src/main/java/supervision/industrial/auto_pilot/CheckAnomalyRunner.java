package supervision.industrial.auto_pilot;

import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.repository.PlcEventRepository;
import org.springframework.boot.CommandLineRunner;


import lombok.RequiredArgsConstructor;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import supervision.industrial.auto_pilot.service.detector.PlcAnomalyDetectionService;

import java.util.List;

@Component
@Order(1)
@RequiredArgsConstructor
public class CheckAnomalyRunner implements CommandLineRunner {

    private  final PlcAnomalyDetectionService anomalyDetectionService;
    private final PlcEventRepository plcEventRepository;

    @Override
    public void run(String... args) {
        System.out.println(">>> StartupRunner CLASS LOADED");
        checkAnomalie();
    }

    private void checkAnomalie() {
        System.out.println("Startup anomaly check");
        // logique ici
        List< PlcEvent > plcEvents = plcEventRepository.findAll()
                .stream().filter(e-> e.getLevel().equals("ERROR")).toList();
        System.out.println("Found " + plcEvents.size() + " plc events");
        plcEvents.forEach(anomalyDetectionService::detectAndPersist);
    }
}
