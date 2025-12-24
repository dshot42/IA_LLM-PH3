package dependancy_bundle.repository;


import org.springframework.data.jpa.repository.JpaRepository;
import dependancy_bundle.model.Machine;
import dependancy_bundle.model.ProductionStep;

import java.util.Optional;

public interface MachineRepository extends JpaRepository<Machine, Long> {
    Optional<Machine> findByCode(String code);

    Machine findFirstByOrderByIdDesc();
}
