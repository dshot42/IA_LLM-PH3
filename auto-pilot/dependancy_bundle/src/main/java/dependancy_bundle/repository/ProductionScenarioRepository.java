package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import dependancy_bundle.model.ProductionScenario;
import dependancy_bundle.model.ProductionStep;

import java.util.List;
import java.util.Optional;

public interface ProductionScenarioRepository extends JpaRepository<ProductionScenario, Long> {

    ProductionScenario getProductionScenarioByName(String name);

    Optional<ProductionScenario> findFirstByOrderByIdAsc();
}
