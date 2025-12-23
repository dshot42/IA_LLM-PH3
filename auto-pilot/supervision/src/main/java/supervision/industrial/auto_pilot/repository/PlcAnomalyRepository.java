package supervision.industrial.auto_pilot.repository;

import supervision.industrial.auto_pilot.model.PlcAnomaly;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface PlcAnomalyRepository extends JpaRepository<PlcAnomaly, Long> {
    Page<PlcAnomaly> findByPartIdOrderByTsDetectedDesc(String partId, Pageable pageable);
    Page<PlcAnomaly> findByMachineOrderByTsDetectedDesc(String machine, Pageable pageable);

    List<PlcAnomaly> findByStatus(String status);
    List<PlcAnomaly> findByMachineAndCycle(String machine, Integer cycle);
    List<PlcAnomaly> findByPartId(String partId);
}
