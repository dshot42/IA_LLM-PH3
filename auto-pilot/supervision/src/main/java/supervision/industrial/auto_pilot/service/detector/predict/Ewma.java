package supervision.industrial.auto_pilot.service.detector.predict;

/**
 * EWMA sur série de comptes (ex: occurrences/jour).
 * ewma[t] = alpha*x[t] + (1-alpha)*ewma[t-1]
 */
public final class Ewma {
    private Ewma() {}

    public static double compute(double[] x, double alpha) {
        if (x == null || x.length == 0) return 0.0;
        double e = x[0];
        for (int i = 1; i < x.length; i++) {
            e = alpha * x[i] + (1.0 - alpha) * e;
        }
        return e;
    }

    public static double ratio(double recent, double baseline) {
        double denom = Math.max(1e-9, baseline);
        return recent / denom;
    }
}
