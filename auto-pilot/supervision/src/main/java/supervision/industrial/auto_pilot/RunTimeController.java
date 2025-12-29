package supervision.industrial.auto_pilot;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.concurrent.ExecutorService;

@Service
@Slf4j
public class RunTimeController {

    private ExecutorService pollExecutor;
    private ExecutorService anomalyExecutor;
    private final CheckAnomalyRunner anomalyRunner;

    private final LaunchDetector launchDetector;
    private Thread pollThread;



    public RunTimeController(CheckAnomalyRunner anomalyRunner, LaunchDetector launchDetector) {
        this.anomalyRunner = anomalyRunner;
        this.launchDetector = launchDetector;
    }

    public synchronized void startDetectorRealTime() {
        System.out.println(">>> StartupRunner runTrsAnalyse");
        if (pollThread != null && pollThread.isAlive()) {
            log.warn("Polling déjà actif");
            return;
        }

        pollThread = new Thread(() -> {
            log.info("EVENT POLLING STARTED");
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    launchDetector.pollNewEvents();
                    Thread.sleep(30_000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } catch (Exception e) {
                    log.error("Polling error", e);
                }
            }
        }, "event-poll-runtime");

        pollThread.start();
    }

    public synchronized void stopEventPolling() {
        if (pollThread != null) {
            pollThread.interrupt();
            pollThread = null;
            log.info("EVENT POLLING STOPPED");
        }
    }

    public synchronized void startCheckAnomaly() {
    anomalyRunner.runCheckAnomaly();
    }


    public synchronized void startTRSAnalise() {
        anomalyRunner.runTrsAnalyse();
    }


}