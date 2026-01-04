package dependancy_bundle.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;


@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})

@Getter
@Setter
@Entity
@Table(
        name = "plc_anomalies"
)
public class PlcAnomaly {


    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;


    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "part_id", referencedColumnName = "id", nullable = true)
    private Part part;

    /**
     * Événement PLC source de l’anomalie
     * (souvent STEP_OK / ERROR / CYCLE_END)
     */
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "event_id",
            referencedColumnName = "id"
    )
    private PlcEvent plcEvent;

    @Column(name = "ts_detected", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime tsDetected = OffsetDateTime.now();

    @Column(name = "cycle", nullable = false)
    private Integer cycle;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "machine_id",
            referencedColumnName = "id"
    )
    private Machine machine;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "production_step_id",
            referencedColumnName = "id"
    )
    private ProductionStep productionStep;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "workorder_id",
            referencedColumnName = "id"
    )
    private Workorder workorder;

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

    @Column(name = "n_step_errors_in_cycle")
    private Integer nStepErrorsInCycle = 0;

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
    @Column(name = "similar_events_count")
    private Integer similarEventsCount;

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
    private OffsetDateTime createdAt = OffsetDateTime.now();

    @Column(name = "report_path")
    private String reportPath;


}
