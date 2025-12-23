package simulator;


import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;

@SpringBootApplication
public class SimulatorApplication {

    private final PlcRealtimeSimulator sim;

    public SimulatorApplication(PlcRealtimeSimulator sim) {
        this.sim = sim;
    }

    public static void main(String[] args) {
        SpringApplication.run(SimulatorApplication.class, args);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void start() {
        new Thread(sim::runForever, "plc-simulator").start();
    }
}


