package supervision.industrial.auto_pilot;


import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Service
public class ScheduleExecutorService {


    @PostConstruct
    public void startDailyTrsScheduler() {

        trsScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "trs-daily-scheduler");
            t.setDaemon(true);
            return t;
        });

        long initialDelay = secondsUntilNextMidnight();

        log.info("⏳ TRS scheduler démarré – premier lancement dans {} secondes", initialDelay);

        trsScheduler.scheduleAtFixedRate(
                () -> {
                    try {
                        log.info("🕛 Lancement automatique analyse TRS quotidienne");
                        startTRSAnalise();
                    } catch (Exception e) {
                        log.error("Erreur analyse TRS automatique", e);
                    }
                },
                initialDelay,
                TimeUnit.DAYS.toSeconds(1),
                TimeUnit.SECONDS
        );
    }

    private long secondsUntilNextMidnight() {
        OffsetDateTime now = OffsetDateTime.now(ZoneId.of("Europe/Paris"));
        OffsetDateTime nextMidnight = now
                .plusDays(1)
                .toLocalDate()
                .atStartOfDay()
                .atZone(ZoneId.of("Europe/Paris"))
                .toOffsetDateTime();

        return Duration.between(now, nextMidnight).getSeconds();
    }


}
