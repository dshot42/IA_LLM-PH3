package dependancy_bundle.model;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Type;
import dependancy_bundle.model.event_listener.PlcEventEntityListener;

import java.math.BigDecimal;
import java.time.OffsetDateTime;


@Getter
@Setter
@Entity
@EntityListeners(PlcEventEntityListener.class)
@Table(
        name = "plc_events",
        indexes = {
                @Index(name = "idx_plc_events_ts", columnList = "ts"),
                @Index(name = "idx_plc_events_part_ts", columnList = "part_id, ts"),
                @Index(name = "idx_plc_events_machine_ts", columnList = "machine, ts"),
                @Index(name = "idx_plc_events_cycle", columnList = "cycle"),
                @Index(name = "idx_plc_events_step", columnList = "step_id"),
                @Index(name = "idx_plc_events_level", columnList = "level")
        }
)
public class PlcEvent {

    // =========================
    // PK technique (obligatoire JPA)
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Colonnes DB
    // =========================

    @Column(name = "ts", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime ts;

    // si gestion par lot , null
    @Column(name = "part_id", nullable = true)
    private String partId;

    @Column(name = "machine", nullable = false)
    private String machine;

    @Column(name = "level", nullable = false)
    private String level;   // INFO / OK / ERROR

    @Column(name = "code")
    private String code;

    @Column(name = "message")
    private String message;

    @Column(name = "cycle")
    private Integer cycle;

    @Column(name = "step_id")
    private String stepId;

    @Column(name = "step_name")
    private String stepName;

    @Column(name = "duration")
    private BigDecimal duration;

    @Type(JsonType.class)
    @Column(name = "payload", columnDefinition = "jsonb")
    private JsonNode payload;

    @JsonIgnore
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "workorder_id",
            referencedColumnName = "id",
            insertable = false,
            updatable = false
    )
    private Workorder workorder;


}
