package supervision.industrial.auto_pilot.workflow.detector.predict;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * Score Hawkes-like simple (auto-excitation) :
 * intensity(t) = mu + sum(alpha * exp(-beta * dt))
 * Renvoie un score entier 0..100.
 */
public final class HawkesLike {
    private HawkesLike() {
    }

    public static int score(
            OffsetDateTime now,
            List<OffsetDateTime> events,
            double alpha,
            double beta,
            double decayPerSecond
    ) {
        if (events == null || events.isEmpty()) return 0;

        double intensity = 0.0;

        for (OffsetDateTime t : events) {
            long dt = Duration.between(t, now).getSeconds();
            if (dt < 0) continue;

            // noyau exponentiel
            intensity += alpha * Math.exp(-decayPerSecond * dt);
        }

        // normalisation logarithmique
        double normalized = Math.log1p(intensity);

        // projection sur une échelle lisible [0–100]
        int score = (int) Math.round(20.0 * normalized);

        return Math.min(score, 100);
    }

}
