package supervision.industrial.auto_pilot.model;

import jakarta.persistence.*;

import java.time.OffsetDateTime;
import java.util.List;

@Entity
@Table(
        name = "machine",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_machine_code", columnNames = "code")
        }
)
public class Machine {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Business fields
    // =========================
    @Column(name = "code", nullable = false, unique = true, length = 10)
    private String code;          // M1, M2, M3, ...

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "description")
    private String description;

    // =========================
    // Connectivity
    // =========================
    @Column(name = "ip_address")
    private String ipAddress;

    @Column(name = "plc_protocol")
    private String plcProtocol;

    @Column(name = "opcua_endpoint")
    private String opcuaEndpoint;

    // =========================
    // Line & ordering
    // =========================
    @Column(name = "line_id", nullable = false)
    private Integer lineId;

    @Column(name = "order_index", nullable = false)
    private Integer orderIndex;

    @Column(name = "nominal_duration_s", nullable = false)
    private Integer nominalDurationS;

    // =========================
    // Relations
    // =========================

    /**
     * Steps nominaux de la machine.
     * - relation logique (machine_id)
     * - LAZY
     * - non propriétaire
     * - pas de cascade
     */
    @OneToMany(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "machine_id",        // production_step.machine_id
            referencedColumnName = "id",
            insertable = false,
            updatable = false
    )
    private List<ProductionStep> productionSteps;

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

    public String getIpAddress() {
        return ipAddress;
    }

    public void setIpAddress(String ipAddress) {
        this.ipAddress = ipAddress;
    }

    public String getPlcProtocol() {
        return plcProtocol;
    }

    public void setPlcProtocol(String plcProtocol) {
        this.plcProtocol = plcProtocol;
    }

    public String getOpcuaEndpoint() {
        return opcuaEndpoint;
    }

    public void setOpcuaEndpoint(String opcuaEndpoint) {
        this.opcuaEndpoint = opcuaEndpoint;
    }

    public Integer getLineId() {
        return lineId;
    }

    public void setLineId(Integer lineId) {
        this.lineId = lineId;
    }

    public Integer getOrderIndex() {
        return orderIndex;
    }

    public void setOrderIndex(Integer orderIndex) {
        this.orderIndex = orderIndex;
    }

    public Integer getNominalDurationS() {
        return nominalDurationS;
    }

    public void setNominalDurationS(Integer nominalDurationS) {
        this.nominalDurationS = nominalDurationS;
    }

    public List<ProductionStep> getProductionSteps() {
        return productionSteps;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
