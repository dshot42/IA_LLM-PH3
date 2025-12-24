package supervision.industrial.auto_pilot.db;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.model.ProductionScenario;
import supervision.industrial.auto_pilot.model.ProductionScenarioStep;
import supervision.industrial.auto_pilot.model.ProductionStep;
import supervision.industrial.auto_pilot.model.enumeration.ProductionHandler;
import supervision.industrial.auto_pilot.repository.ProductionScenarioRepository;
import supervision.industrial.auto_pilot.repository.ProductionScenarioStepRepository;
import supervision.industrial.auto_pilot.repository.ProductionStepRepository;

import java.util.List;

@Service
@Configuration
public class InitScenario {

    @Autowired
    private ProductionStepRepository productionStepRepository;
    @Autowired
    private ProductionScenarioRepository productionScenarioRepository;
    @Autowired
    private ProductionScenarioStepRepository productionScenarioStepRepository;

    public void generateNominalScenario() {

        // generate scenario name nominal
        ProductionScenario productionScenario = new ProductionScenario();
        productionScenario.setDescription("Production Scenario Nominal");
        productionScenario.setName("NOMINAL");
        productionScenario.setProductionType(ProductionHandler.PART.toString());
        ProductionScenario scenario = productionScenarioRepository.save(productionScenario);
        Long idScenario = scenario.getId();

        // step
        List<ProductionStep> productionSteps = productionStepRepository.findAllByOrderByIdAsc();
        productionSteps.forEach(ps -> {
            ProductionScenarioStep productionScenarioStep = new ProductionScenarioStep();
            productionScenarioStep.setStepOrder(ps.getId());
            productionScenarioStep.setProductionScenario(scenario);
            productionScenarioStep.setProductionStep(ps);
            productionScenarioStepRepository.save(productionScenarioStep);
        });
        System.out.println("Inserted Scenario ID: " + idScenario);
    }

}
