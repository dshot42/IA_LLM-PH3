package dependancy_bundle.repository;


import dependancy_bundle.model.Machine;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionStep;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import dependancy_bundle.model.PlcAnomaly;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

public interface PlcAnomalyRepository extends JpaRepository<PlcAnomaly, Long> {
    Page<PlcAnomaly> findByPartIdOrderByTsDetectedDesc(String partId, Pageable pageable);


    @Query("""
select a.tsDetected
from PlcAnomaly a
where a.machine.id = :machineId
  and a.productionStep.id = :stepId
  and a.tsDetected >= :since
order by a.tsDetected desc
""")
    List<OffsetDateTime> findRecentDetections(
            @Param("machineId") Long machineId,
            @Param("stepId") Long stepId,
            @Param("since") OffsetDateTime since
    );

    @Modifying
    @Transactional
    @Query(value = "DELETE FROM plc_anomalies", nativeQuery = true)
    void truncatePlcAnomalies();


    List<PlcAnomaly> findAllByWorkorderId(Long workorderId);

    List<PlcAnomaly> findAllByCreatedAtBetween(
            OffsetDateTime start,
            OffsetDateTime end
    );

    List<PlcAnomaly> findAllByPlcEventId(Long id);

    boolean existsByPlcEventId(Long plcEventId);

    Optional<PlcAnomaly> findFirstByPlcEventIdOrderByTsDetectedAsc(Long id);
}
