package dependancy_bundle.repository;

import dependancy_bundle.model.Kpi;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.model.ProductionStepHasKPI;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ProductionStepHasKPIRepository extends JpaRepository<ProductionStepHasKPI, Long> {

    Optional<ProductionStepHasKPI> findByProductionStepAndKpi_KpiName(
            ProductionStep step,
            String kpiName
    );
}