package supervision.industrial.auto_pilot.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class AppConfig {

    public static int port = 5000;
    public static String ip = "127.0.0.1";

    public static String iaApi =  "http://" + ip + ":" + port;

    public static String getUrl(String api) {
        return iaApi+api;
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
