package supervision.industrial.auto_pilot.model;
import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import org.hibernate.annotations.Type;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Entity
@Table(
        name = "plc_events",
        indexes = {
                @Index(name = "idx_plc_events_ts", columnList = "ts"),
                @Index(name = "idx_plc_events_part_ts", columnList = "part_id, ts"),
                @Index(name = "idx_plc_events_machine_ts", columnList = "machine, ts"),
                @Index(name = "idx_plc_events_cycle", columnList = "cycle"),
                @Index(name = "idx_plc_events_step", columnList = "step_id"),
                @Index(name = "idx_plc_events_level", columnList = "level")
        }
)
public class PlcEvent {

    // =========================
    // PK technique (obligatoire JPA)
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Colonnes DB
    // =========================

    @Column(name = "ts", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime ts;

    @Column(name = "part_id")
    private String partId;

    @Column(name = "machine", nullable = false)
    private String machine;

    @Column(name = "level", nullable = false)
    private String level;   // INFO / OK / ERROR

    @Column(name = "code")
    private String code;

    @Column(name = "message")
    private String message;

    @Column(name = "cycle")
    private Integer cycle;

    @Column(name = "step_id")
    private String stepId;

    @Column(name = "step_name")
    private String stepName;

    @Column(name = "duration")
    private BigDecimal duration;

    @Type(JsonType.class)
    @Column(name = "payload", columnDefinition = "jsonb")
    private JsonNode payload;

    // =========================
    // Getters / Setters
    // =========================

    public Long getId() {
        return id;
    }

    public OffsetDateTime getTs() {
        return ts;
    }

    public void setTs(OffsetDateTime ts) {
        this.ts = ts;
    }

    public String getPartId() {
        return partId;
    }

    public void setPartId(String partId) {
        this.partId = partId;
    }

    public String getMachine() {
        return machine;
    }

    public void setMachine(String machine) {
        this.machine = machine;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Integer getCycle() {
        return cycle;
    }

    public void setCycle(Integer cycle) {
        this.cycle = cycle;
    }

    public String getStepId() {
        return stepId;
    }

    public void setStepId(String stepId) {
        this.stepId = stepId;
    }

    public String getStepName() {
        return stepName;
    }

    public void setStepName(String stepName) {
        this.stepName = stepName;
    }

    public BigDecimal getDuration() {
        return duration;
    }

    public void setDuration(BigDecimal duration) {
        this.duration = duration;
    }

    public JsonNode getPayload() {
        return payload;
    }

    public void setPayload(JsonNode payload) {
        this.payload = payload;
    }
}
