package dependancy_bundle.model;

import jakarta.persistence.*;

import java.time.OffsetDateTime;
import java.util.List;

@Entity
@Table(
        name = "part",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_part_external_part_id", columnNames = "external_part_id")
        }
)
public class Part {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Business Identifier
    // =========================
    @Column(name = "external_part_id", nullable = false, unique = true)
    private String externalPartId;

    // =========================
    // Foreign Key (industrial_line)
    // =========================
    @Column(name = "line_id", nullable = false)
    private Integer lineId;

    // =========================
    // Status
    // =========================
    @Column(name = "status", nullable = false)
    private String status = "IN_PROGRESS";

    // =========================
    // Timestamps
    // =========================
    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @Column(name = "finished_at")
    private OffsetDateTime finishedAt;

    // =========================
    // Relations (READ-ONLY)
    // =========================

    /**
     * Tous les événements PLC liés à cette pièce.
     * Relation basée sur external_part_id.
     * LAZY + non propriétaire = SAFE.
     */
    @OneToMany(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "part_id",                // plc_events.part_id
            referencedColumnName = "external_part_id",
            insertable = false,
            updatable = false
    )
    private List<PlcEvent> plcEvents;

    /**
     * Toutes les anomalies détectées pour cette pièce.
     */
    @OneToMany(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "part_id",                // plc_anomalies.part_id
            referencedColumnName = "external_part_id",
            insertable = false,
            updatable = false
    )
    private List<PlcAnomaly> plcAnomalies;

    // =========================
    // Lifecycle Hooks
    // =========================
    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = OffsetDateTime.now();
        }
    }

    // =========================
    // Getters / Setters
    // =========================

    public Long getId() {
        return id;
    }

    public String getExternalPartId() {
        return externalPartId;
    }

    public void setExternalPartId(String externalPartId) {
        this.externalPartId = externalPartId;
    }

    public Integer getLineId() {
        return lineId;
    }

    public void setLineId(Integer lineId) {
        this.lineId = lineId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(OffsetDateTime finishedAt) {
        this.finishedAt = finishedAt;
    }

    public List<PlcEvent> getPlcEvents() {
        return plcEvents;
    }

    public List<PlcAnomaly> getPlcAnomalies() {
        return plcAnomalies;
    }
}
