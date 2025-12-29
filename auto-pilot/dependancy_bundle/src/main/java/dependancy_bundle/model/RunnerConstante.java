package dependancy_bundle.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;


@Getter
@Setter
@Entity
@Table(
        name = "runner_constante"
)
public class RunnerConstante {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;


    @Column(name = "last_current_id_event", nullable = false)
    private Long lastCurrentEvent = 0L;

    @Column(name = "last_anomaly_id_analise", nullable = false)
    private Long lastAnomalyAnalise = 0L;


}
