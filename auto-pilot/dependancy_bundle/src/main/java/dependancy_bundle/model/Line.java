package dependancy_bundle.model;

import jakarta.persistence.*;

import java.time.OffsetDateTime;

@Entity
@Table(
        name = "industrial_line",
        indexes = {
                @Index(name = "idx_industrial_line_code", columnList = "code")
        }
)
public class Line {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Business identity
    // =========================
    @Column(name = "code", nullable = false, unique = true, length = 50)
    private String code;              // ex: LINE_01, USINAGE_A, L5

    @Column(name = "name", nullable = false)
    private String name;              // Ligne 5 machines – Usinage complet

    @Column(name = "description")
    private String description;

    // =========================
    // Nominal characteristics
    // =========================
    @Column(name = "nominal_cycle_s")
    private Integer nominalCycleS;    // Durée cycle cible (ex: 90s)

    // =========================
    // Optional / Evolution fields
    // =========================

    @Column(name = "site")
    private String site;              // usine / pays / client (optionnel)

    @Column(name = "process_type")
    private String processType;       // USINAGE / ASSEMBLAGE / CONTROLE / ...

    @Column(name = "technology")
    private String technology;        // CNC / ROBOT / MANUAL / MIXED

    @Column(name = "owner")
    private String owner;             // responsable ligne (optionnel)

    @Column(name = "external_ref")
    private String externalRef;        // ERP / MES / client ref

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
        if (createdAt == null) createdAt = OffsetDateTime.now();
        if (updatedAt == null) updatedAt = OffsetDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now();
    }

    // =========================
    // Getters / Setters
    // =========================

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
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

    public Integer getNominalCycleS() {
        return nominalCycleS;
    }

    public void setNominalCycleS(Integer nominalCycleS) {
        this.nominalCycleS = nominalCycleS;
    }

    public String getSite() {
        return site;
    }

    public void setSite(String site) {
        this.site = site;
    }

    public String getProcessType() {
        return processType;
    }

    public void setProcessType(String processType) {
        this.processType = processType;
    }

    public String getTechnology() {
        return technology;
    }

    public void setTechnology(String technology) {
        this.technology = technology;
    }

    public String getOwner() {
        return owner;
    }

    public void setOwner(String owner) {
        this.owner = owner;
    }

    public String getExternalRef() {
        return externalRef;
    }

    public void setExternalRef(String externalRef) {
        this.externalRef = externalRef;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public void setIsActive(Boolean active) {
        isActive = active;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
