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
    @OneToMany(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "machine_id",        // ✅ FK réelle
            referencedColumnName = "id"
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
}
