package dependancy_bundle.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.OffsetDateTime;
import java.util.List;

@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})

@Getter
@Setter
@Entity
@Table(
        name = "production_step"
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
    @Column(name = "step_code", nullable = false)
    private String stepCode;      // ex: M2.07

    @Column(name = "step_type", nullable = false)
    private String stepType= "SYSTEM"; // HUMAIN      // ex: M2.07


    @Column(name = "name", nullable = false)
    private String name;          // ROUGH_PASS_1

    @Column(name = "description")
    private String description;

    @Column(name = "nominal_duration_s", nullable = false)
    private Double nominalDurationS;

    /**
     * Relation ORM vers Machine
     * - LAZY (important)
     * - pas de cascade
     * - lecture seule côté relation
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "machine_id", nullable = false)
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

    @JsonIgnore
    @OneToMany(mappedBy = "productionStep", fetch = FetchType.LAZY)
    private List<ProductionScenarioStep> productionScenarioSteps;


}
