package supervision.industrial.auto_pilot.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;

@Entity
@Table(
        name = "production_scenario",
        indexes = {
                @Index(name = "idx_scenario_line", columnList = "line_id"),
                @Index(name = "idx_scenario_part_ref", columnList = "part_reference"),
                @Index(name = "idx_scenario_lot", columnList = "lot_id"),
                @Index(name = "idx_scenario_active", columnList = "is_active")
        }
)
public class ProductionScenario {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Line scope
    // =========================
    @Column(name = "line_id", nullable = false)
    private Long lineId;   // FK logique vers industrial_line.id

    // =========================
    // Piece / Lot identification
    // =========================
    @Column(name = "part_reference", nullable = false)
    private String partReference;      // ex: REF-AXE-2025-A

    @Column(name = "lot_id")
    private String lotId;               // ex: LOT-2025-03 (nullable)

    // =========================
    // Scenario identity
    // =========================
    @Column(name = "name", nullable = false)
    private String name;                // ex: Axe acier – finition renforcée

    @Column(name = "description")
    private String description;

    // =========================
    // Nominal targets
    // =========================
    @Column(name = "nominal_cycle_s")
    private Integer nominalCycleS;      // override cycle nominal ligne (optionnel)

    // =========================
    // Scenario parameters
    // =========================
    @Type(JsonType.class)
    @Column(name = "parameters", columnDefinition = "jsonb")
    private JsonNode parameters;
    /*
        Exemple :
        {
          "enable_m5_vision": true,
          "max_overrun_s": 5,
          "allowed_error_codes": ["E-M2-011"],
          "anomaly_sensitivity": "HIGH"
        }
    */

    // =========================
    // Validity window
    // =========================
    @Column(name = "valid_from", columnDefinition = "timestamptz")
    private OffsetDateTime validFrom;

    @Column(name = "valid_to", columnDefinition = "timestamptz")
    private OffsetDateTime validTo;

    // =========================
    // Status
    // =========================
    @Column(name = "is_active")
    private Boolean isActive = true;

    // =========================
    // Metadata
    // =========================
    @Column(name = "created_at", columnDefinition = "timestamptz")
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", columnDefinition = "timestamptz")
    private OffsetDateTime updatedAt;

    // =========================
    // Lifecycle
    // =========================
    @PrePersist
    protected void onCreate() {
        OffsetDateTime now = OffsetDateTime.now();
        if (createdAt == null) createdAt = now;
        if (updatedAt == null) updatedAt = now;
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now();
    }

    // =========================
    // Getters / Setters
    // =========================

    public Long getId() { return id; }

    public Long getLineId() { return lineId; }
    public void setLineId(Long lineId) { this.lineId = lineId; }

    public String getPartReference() { return partReference; }
    public void setPartReference(String partReference) { this.partReference = partReference; }

    public String getLotId() { return lotId; }
    public void setLotId(String lotId) { this.lotId = lotId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public Integer getNominalCycleS() { return nominalCycleS; }
    public void setNominalCycleS(Integer nominalCycleS) { this.nominalCycleS = nominalCycleS; }

    public JsonNode getParameters() { return parameters; }
    public void setParameters(JsonNode parameters) { this.parameters = parameters; }

    public OffsetDateTime getValidFrom() { return validFrom; }
    public void setValidFrom(OffsetDateTime validFrom) { this.validFrom = validFrom; }

    public OffsetDateTime getValidTo() { return validTo; }
    public void setValidTo(OffsetDateTime validTo) { this.validTo = validTo; }

    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean active) { isActive = active; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
}
