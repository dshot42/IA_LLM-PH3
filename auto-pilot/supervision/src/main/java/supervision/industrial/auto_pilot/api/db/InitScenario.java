package supervision.industrial.auto_pilot.api.db;

import dependancy_bundle.repository.ProductionScenarioRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Service;
import dependancy_bundle.model.ProductionScenario;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.enumeration.ProductionHandler;
import dependancy_bundle.repository.ProductionScenarioStepRepository;
import dependancy_bundle.repository.ProductionStepRepository;

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
