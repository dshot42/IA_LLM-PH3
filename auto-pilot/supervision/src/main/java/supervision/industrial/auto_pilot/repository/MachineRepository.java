package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import supervision.industrial.auto_pilot.model.Machine;
import supervision.industrial.auto_pilot.model.ProductionStep;

import java.util.Optional;

public interface MachineRepository extends JpaRepository<Machine, Long> {
    Optional<Machine> findByCode(String code);

    Machine findFirstByOrderByIdDesc();
}
