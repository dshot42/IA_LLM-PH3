package dependancy_bundle.repository;


import dependancy_bundle.model.Machine;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface MachineRepository extends JpaRepository<Machine, Long> {
    Optional<Machine> findByCode(String code);

    Machine findFirstByOrderByIdDesc();

    List<Machine> findByLineIdOrderByIdAsc(Integer lineId);

}
