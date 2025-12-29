package simulator;


import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.EventListener;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;


@Configuration
@ComponentScan(basePackages = {
        "simulator",
        "dependancy_bundle"
})
@EnableJpaRepositories(basePackages = "dependancy_bundle.repository")
@EntityScan(basePackages = "dependancy_bundle.model")
@SpringBootApplication
public class SimulatorApplication {

    private final PlcRealtimeSimulator sim;

    @Autowired
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


