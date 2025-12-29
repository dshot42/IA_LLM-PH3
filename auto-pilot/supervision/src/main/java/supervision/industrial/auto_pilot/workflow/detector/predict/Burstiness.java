package supervision.industrial.auto_pilot.workflow.detector.predict;

/**
 * Burstiness B = (sigma - mu) / (sigma + mu) borné [-1,1]
 * Mesure "grappes" d'événements (inter-arrivals).
 */
public final class Burstiness {
    private Burstiness() {}

    public static double compute(double mean, double std) {
        double denom = std + mean;
        if (denom <= 1e-12) return 0.0;
        double b = (std - mean) / denom;
        if (b > 1.0) b = 1.0;
        if (b < -1.0) b = -1.0;
        return b;
    }
}
