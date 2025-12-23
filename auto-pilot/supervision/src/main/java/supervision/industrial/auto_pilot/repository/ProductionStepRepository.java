package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import supervision.industrial.auto_pilot.model.ProductionStep;

public interface ProductionStepRepository extends JpaRepository<ProductionStep, Long> {

    boolean existsByStepCodeAndMachineId(String stepCode, Integer machineId);
}
