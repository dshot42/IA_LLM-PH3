package supervision.industrial.auto_pilot.service.detector.predict;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * Score Hawkes-like simple (auto-excitation) :
 * intensity(t) = mu + sum(alpha * exp(-beta * dt))
 * Renvoie un score entier 0..100.
 */
public final class HawkesLike {
    private HawkesLike() {}

    public static int score(OffsetDateTime t, List<OffsetDateTime> pastEvents,
                            double mu, double alpha, double betaPerSecond) {
        if (t == null || pastEvents == null || pastEvents.isEmpty()) return 0;

        double intensity = mu;
        for (OffsetDateTime te : pastEvents) {
            if (te == null || te.isAfter(t)) continue;
            long dt = Duration.between(te, t).getSeconds();
            double contrib = alpha * Math.exp(-betaPerSecond * dt);
            intensity += contrib;
        }

        // Mapping intensity -> 0..100 (log compress)
        double mapped = 100.0 * (1.0 - Math.exp(-0.6 * Math.max(0.0, intensity - mu)));
        int s = (int) Math.round(mapped);
        if (s < 0) s = 0;
        if (s > 100) s = 100;
        return s;
    }
}
