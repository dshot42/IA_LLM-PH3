package dependancy_bundle.model;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;


@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})

@Getter
@Setter
@Entity
@Table(
        name = "plc_events"
)
public class PlcEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "ts", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime ts;

    // si gestion par lot , null
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "part_id")
    private Part part;


    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "machine_id",
            referencedColumnName = "id"
    )
    private Machine machine;

    @Column(name = "level", nullable = false)
    private String level;   // INFO / OK / ERROR

    @Column(name = "code")
    private String code;

    @Column(name = "message")
    private String message;

    @Column(name = "cycle")
    private Integer cycle;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "production_step_id",
            referencedColumnName = "id"
    )
    private ProductionStep productionStep;

    @Column(name = "duration")
    private Double duration;

    @Type(JsonType.class)
    @Column(name = "payload", columnDefinition = "jsonb")
    private JsonNode payload;

    @JsonIgnore
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "workorder_id",
            referencedColumnName = "id"
    )
    private Workorder workorder;

}
