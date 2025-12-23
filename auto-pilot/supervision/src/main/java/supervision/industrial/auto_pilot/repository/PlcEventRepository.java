package supervision.industrial.auto_pilot.repository;

import supervision.industrial.auto_pilot.model.PlcEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;

public interface PlcEventRepository extends JpaRepository<PlcEvent, OffsetDateTime> {
    Page<PlcEvent> findByPartIdOrderByTsDesc(String partId, Pageable pageable);
    Page<PlcEvent> findByMachineOrderByTsDesc(String machine, Pageable pageable);
}
