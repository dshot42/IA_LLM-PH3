package supervision.industrial.auto_pilot.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.Type;
import supervision.industrial.auto_pilot.model.enumeration.ProductionHandler;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;


@Getter
@Setter
@Entity
@Table(name = "production_scenario")
public class ProductionScenario {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;


    @Column(name = "production_type")
    private String productionType = ProductionHandler.PART.toString();

    @Column
    private String description;

    @OneToMany(
            mappedBy = "productionScenario",
            cascade = CascadeType.ALL,
            orphanRemoval = true,
            fetch = FetchType.LAZY
    )
    private List<ProductionScenarioStep> productionScenarioSteps = new ArrayList<>();
}
