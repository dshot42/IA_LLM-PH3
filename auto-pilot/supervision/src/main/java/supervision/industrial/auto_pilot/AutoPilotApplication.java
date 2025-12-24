package supervision.industrial.auto_pilot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;


@EnableScheduling
@SpringBootApplication
public class AutoPilotApplication {
	public static void main(String[] args) {
		SpringApplication.run(AutoPilotApplication.class, args);
	}
}
