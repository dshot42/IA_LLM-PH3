package supervision.industrial.auto_pilot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;


@SpringBootApplication
@ComponentScan({
        "supervision.industrial.auto_pilot",
        "dependancy_bundle"
})
@EnableJpaRepositories({
        "supervision.industrial.auto_pilot.repository",
        "dependancy_bundle.repository"
})
@EntityScan({
        "supervision.industrial.auto_pilot.model",
        "dependancy_bundle.model"
})


public class AutoPilotApplication {
    public static void main(String[] args) {
        ConfigurableApplicationContext ctx =
                SpringApplication.run(AutoPilotApplication.class, args);

        RunTimeController runtime =
                ctx.getBean(RunTimeController.class);

        if (MainConfig.runMode.equals("REALTIME"))
            runtime.startDetectorRealTime(); // thread infini => en prod
        else if (MainConfig.runMode.equals("SIMULATOR")) {
            runtime.startCheckAnomaly(); // test sur donnée anomaly existante
            runtime.startTRSAnalise();
        }

    }

}
