package dependancy_bundle.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Setter
@Getter
@Entity
@Table(name = "production_scenario_step")
public class ProductionScenarioStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "step_order", nullable = false)
    private Long stepOrder;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "production_scenario_id", nullable = false)
    private ProductionScenario productionScenario;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "production_step_id", nullable = false)
    private ProductionStep productionStep;


}

