package dependancy_bundle.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.OffsetDateTime;
import java.util.List;

@Getter
@Setter
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
    @JsonIgnore
    @OneToMany(mappedBy = "part", fetch = FetchType.LAZY)
    private List<PlcEvent> plcEvents;
    /**
     * Toutes les anomalies détectées pour cette pièce.
     */
    @JsonIgnore
    @OneToMany(mappedBy = "part", fetch = FetchType.LAZY)
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


}
