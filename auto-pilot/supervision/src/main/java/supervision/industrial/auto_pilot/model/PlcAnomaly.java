package supervision.industrial.auto_pilot.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;

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

    // =========================
    // Getters
    // =========================


    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }


    public String getPartId() {
        return partId;
    }

    public void setPartId(String partId) {
        this.partId = partId;
    }

    public Part getPart() {
        return part;
    }

    public void setPart(Part part) {
        this.part = part;
    }

    public PlcEvent getPlcEvent() {
        return plcEvent;
    }

    public void setPlcEvent(PlcEvent plcEvent) {
        this.plcEvent = plcEvent;
    }

    public OffsetDateTime getTsDetected() {
        return tsDetected;
    }

    public void setTsDetected(OffsetDateTime tsDetected) {
        this.tsDetected = tsDetected;
    }

    public Integer getCycle() {
        return cycle;
    }

    public void setCycle(Integer cycle) {
        this.cycle = cycle;
    }

    public String getMachine() {
        return machine;
    }

    public void setMachine(String machine) {
        this.machine = machine;
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

    public Double getAnomalyScore() {
        return anomalyScore;
    }

    public void setAnomalyScore(Double anomalyScore) {
        this.anomalyScore = anomalyScore;
    }

    public Boolean getRuleAnomaly() {
        return ruleAnomaly;
    }

    public void setRuleAnomaly(Boolean ruleAnomaly) {
        this.ruleAnomaly = ruleAnomaly;
    }

    public JsonNode getRuleReasons() {
        return ruleReasons;
    }

    public void setRuleReasons(JsonNode ruleReasons) {
        this.ruleReasons = ruleReasons;
    }

    public Boolean getHasStepError() {
        return hasStepError;
    }

    public void setHasStepError(Boolean hasStepError) {
        this.hasStepError = hasStepError;
    }

    public Integer getnStepErrors() {
        return nStepErrors;
    }

    public void setnStepErrors(Integer nStepErrors) {
        this.nStepErrors = nStepErrors;
    }

    public Double getCycleDurationS() {
        return cycleDurationS;
    }

    public void setCycleDurationS(Double cycleDurationS) {
        this.cycleDurationS = cycleDurationS;
    }

    public Double getDurationOverrunS() {
        return durationOverrunS;
    }

    public void setDurationOverrunS(Double durationOverrunS) {
        this.durationOverrunS = durationOverrunS;
    }

    public Integer getEventsCount() {
        return eventsCount;
    }

    public void setEventsCount(Integer eventsCount) {
        this.eventsCount = eventsCount;
    }

    public Integer getWindowDays() {
        return windowDays;
    }

    public void setWindowDays(Integer windowDays) {
        this.windowDays = windowDays;
    }

    public Double getEwmaRatio() {
        return ewmaRatio;
    }

    public void setEwmaRatio(Double ewmaRatio) {
        this.ewmaRatio = ewmaRatio;
    }

    public Double getRateRatio() {
        return rateRatio;
    }

    public void setRateRatio(Double rateRatio) {
        this.rateRatio = rateRatio;
    }

    public Double getBurstiness() {
        return burstiness;
    }

    public void setBurstiness(Double burstiness) {
        this.burstiness = burstiness;
    }

    public Integer getHawkesScore() {
        return hawkesScore;
    }

    public void setHawkesScore(Integer hawkesScore) {
        this.hawkesScore = hawkesScore;
    }

    public String getConfidence() {
        return confidence;
    }

    public void setConfidence(String confidence) {
        this.confidence = confidence;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getSeverity() {
        return severity;
    }

    public void setSeverity(String severity) {
        this.severity = severity;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public String getReportPath() {
        return reportPath;
    }

    public void setReportPath(String reportPath) {
        this.reportPath = reportPath;
    }
}
