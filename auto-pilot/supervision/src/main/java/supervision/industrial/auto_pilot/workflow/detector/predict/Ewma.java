package supervision.industrial.auto_pilot.workflow.detector.predict;

/**
 * EWMA sur série de comptes (ex: occurrences/jour).
 * ewma[t] = alpha*x[t] + (1-alpha)*ewma[t-1]
 */
public final class Ewma {
    private Ewma() {
    }

    public static double compute(double[] x, double alpha) {
        if (x == null || x.length == 0) return 0.0;
        double e = x[0];
        for (int i = 1; i < x.length; i++) {
            e = alpha * x[i] + (1.0 - alpha) * e;
        }
        return e;
    }

    public static double ratio(double recent, double baseline) {

        // Aucun historique significatif
        if (baseline < 0.5) {
            if (recent < 0.5) return 1.0;   // stable
            return 1.5;                     // apparition récente modérée
        }

        double raw = recent / baseline;

        // Sécurité numérique
        if (Double.isNaN(raw) || Double.isInfinite(raw)) {
            return 1.0;
        }

        // Compression logarithmique (clé)
        double logRatio = Math.log1p(raw);

        // Normalisation finale
        return Math.min(logRatio, 3.0);
    }


}
