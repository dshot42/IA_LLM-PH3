package supervision.industrial.auto_pilot.model;

import jakarta.persistence.*;

import java.time.OffsetDateTime;

@Entity
@Table(
        name = "production_step",
        indexes = {
                @Index(name = "idx_production_step_step_code", columnList = "step_code"),
                @Index(name = "idx_production_step_machine_id", columnList = "machine_id")
        }
)
public class ProductionStep {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Business fields
    // =========================
    @Column(name = "step_code", nullable = false, length = 10)
    private String stepCode;      // ex: M2.07

    @Column(name = "name", nullable = false)
    private String name;          // ROUGH_PASS_1

    @Column(name = "description")
    private String description;

    @Column(name = "duration")
    private Long duration;

    // =========================
    // Machine reference (FK)
    // =========================
    @Column(name = "machine_id", nullable = false)
    private Integer machineId;    // accès rapide sans JOIN

    /**
     * Relation ORM vers Machine
     * - LAZY (important)
     * - pas de cascade
     * - lecture seule côté relation
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "machine_id",
            referencedColumnName = "id",
            insertable = false,
            updatable = false
    )
    private Machine machine;

    // =========================
    // Step nature
    // =========================
    @Column(name = "is_technical")
    private Boolean isTechnical = false;

    // =========================
    // Timestamps
    // =========================
    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    // =========================
    // Lifecycle
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

    public String getStepCode() {
        return stepCode;
    }

    public void setStepCode(String stepCode) {
        this.stepCode = stepCode;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Integer getMachineId() {
        return machineId;
    }

    public void setMachineId(Integer machineId) {
        this.machineId = machineId;
    }

    public Machine getMachine() {
        return machine;
    }

    public Boolean getIsTechnical() {
        return isTechnical;
    }

    public void setIsTechnical(Boolean isTechnical) {
        this.isTechnical = isTechnical;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
