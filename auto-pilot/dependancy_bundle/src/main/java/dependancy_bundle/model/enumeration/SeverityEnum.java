package dependancy_bundle.model.enumeration;

public enum Severity {
    INFO, MINOR, MAJOR, CRITICAL;

    public static Severity fromDb(String v) {
        if (v == null) return MINOR;
        try {
            return Severity.valueOf(v.toUpperCase());
        } catch (Exception e) {
            return MINOR;
        }
    }
}
