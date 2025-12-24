package dependancy_bundle.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;

@Getter
@Setter
@Entity
@Table(
        name = "plc_anomalies",
        indexes = {
                @Index(name = "idx_plc_anomaly_machine", columnList = "machine"),
                @Index(name = "idx_plc_anomaly_cycle", columnList = "cycle"),
                @Index(name = "idx_plc_anomaly_part", columnList = "part_id"),
                @Index(name = "idx_plc_anomaly_status", columnList = "status"),
                @Index(name = "idx_plc_anomaly_created_at", columnList = "created_at")
        }
)
public class PlcAnomaly {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;


    /**
     * Clé métier – écriture directe (PLC / Python / batch)
     */
    @Column(name = "part_id")
    private String partId;

    /**
     * Relation Part (lecture uniquement)
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "part_id",
            referencedColumnName = "external_part_id",
            insertable = false,
            updatable = false
    )
    private Part part;

    /**
     * Événement PLC source de l’anomalie
     * (souvent STEP_OK / ERROR / CYCLE_END)
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "event_id",
            referencedColumnName = "id",
            insertable = false,
            updatable = false
    )
    private PlcEvent plcEvent;

    @Column(name = "ts_detected", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime tsDetected = OffsetDateTime.now();

    @Column(name = "cycle", nullable = false)
    private Integer cycle;

    @Column(name = "machine", nullable = false)
    private String machine;

    @Column(name = "step_id")
    private String stepId;

    @Column(name = "step_name")
    private String stepName;

    // =========================
    // Detection
    // =========================
    @Column(name = "anomaly_score")
    private Double anomalyScore;

    @Column(name = "rule_anomaly", nullable = false)
    private Boolean ruleAnomaly;

    @Type(JsonType.class)
    @Column(name = "rule_reasons", columnDefinition = "jsonb")
    private JsonNode ruleReasons;

    // =========================
    // Step-related
    // =========================
    @Column(name = "has_step_error")
    private Boolean hasStepError = false;

    @Column(name = "n_step_errors")
    private Integer nStepErrors = 0;

    // =========================
    // Cycle metrics
    // =========================
    @Column(name = "cycle_duration_s")
    private Double cycleDurationS;

    @Column(name = "duration_overrun_s")
    private Double durationOverrunS;

    // =========================
    // Predictive metrics
    // =========================
    @Column(name = "events_count")
    private Integer eventsCount;

    @Column(name = "window_days")
    private Integer windowDays;

    @Column(name = "ewma_ratio")
    private Double ewmaRatio;

    @Column(name = "rate_ratio")
    private Double rateRatio;

    @Column(name = "burstiness")
    private Double burstiness;

    @Column(name = "hawkes_score")
    private Integer hawkesScore;

    @Column(name = "confidence")
    private String confidence;

    // =========================
    // Business status
    // =========================
    @Column(name = "status")
    private String status = "OPEN";

    @Column(name = "severity")
    private String severity;

    // =========================
    // Metadata
    // =========================
    @Column(name = "created_at", columnDefinition = "timestamptz")
    private OffsetDateTime createdAt;

    @Column(name = "report_path")
    private String reportPath;

    // =========================
    // Lifecycle
    // =========================
    @PrePersist
    protected void onCreate() {
        if (createdAt == null) createdAt = OffsetDateTime.now();
        if (tsDetected == null) tsDetected = OffsetDateTime.now();
    }

}
