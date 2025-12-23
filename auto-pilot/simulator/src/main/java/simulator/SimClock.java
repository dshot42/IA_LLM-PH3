package simulator;
import java.time.OffsetDateTime;

public class SimClock {
    private OffsetDateTime current;

    public SimClock(OffsetDateTime start) {
        this.current = start;
    }

    public OffsetDateTime now() {
        return current;
    }

    public void advanceSeconds(double seconds) {
        long nanos = (long) (seconds * 1_000_000_000L);
        current = current.plusNanos(nanos);
    }
}
