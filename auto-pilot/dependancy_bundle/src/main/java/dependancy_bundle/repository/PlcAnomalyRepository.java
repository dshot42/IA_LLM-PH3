package dependancy_bundle.repository;


import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import dependancy_bundle.model.PlcAnomaly;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.OffsetDateTime;
import java.util.List;

public interface PlcAnomalyRepository extends JpaRepository<PlcAnomaly, Long> {
    Page<PlcAnomaly> findByPartIdOrderByTsDetectedDesc(String partId, Pageable pageable);
    Page<PlcAnomaly> findByMachineOrderByTsDetectedDesc(String machine, Pageable pageable);

    List<PlcAnomaly> findByStatus(String status);
    List<PlcAnomaly> findByMachineAndCycle(String machine, Integer cycle);
    List<PlcAnomaly> findByPartId(String partId);

    @Query("select a.tsDetected from PlcAnomaly a " +
            "where a.machine = :machine and a.stepId = :stepId and a.tsDetected >= :since " +
            "order by a.tsDetected desc")
    List<OffsetDateTime> findRecentDetections(@Param("machine") String machine,
                                              @Param("stepId") String stepId,
                                              @Param("since") OffsetDateTime since);
}
