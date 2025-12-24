package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import dependancy_bundle.model.ProductionScenario;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;

import java.util.List;

public interface ProductionScenarioStepRepository extends JpaRepository<ProductionScenarioStep, Long> {

    List<ProductionScenarioStep> findByProductionScenarioId(Long productionScenarioId);
}
