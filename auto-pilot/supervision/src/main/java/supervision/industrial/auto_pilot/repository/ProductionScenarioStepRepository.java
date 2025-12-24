package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import supervision.industrial.auto_pilot.model.ProductionScenario;
import supervision.industrial.auto_pilot.model.ProductionScenarioStep;
import supervision.industrial.auto_pilot.model.ProductionStep;

import java.util.List;

public interface ProductionScenarioStepRepository extends JpaRepository<ProductionScenarioStep, Long> {

    List<ProductionScenarioStep> findByProductionScenarioId(Long productionScenarioId);
}
