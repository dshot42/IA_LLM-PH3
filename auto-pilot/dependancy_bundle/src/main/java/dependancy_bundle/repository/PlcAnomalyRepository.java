package dependancy_bundle.repository;


import dependancy_bundle.model.PlcAnomaly;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
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

    Optional<PlcAnomaly> findByPlcEventId(Long plcEventId);

    Optional<PlcAnomaly> findFirstByPlcEventIdOrderByTsDetectedAsc(Long id);


    @Query("""
                SELECT p.durationOverrunS
                FROM PlcAnomaly p
                WHERE p.machine.id = :machineId
                  AND p.productionStep.id = :stepId
                  AND p.tsDetected >= :since
                  AND p.durationOverrunS IS NOT NULL
                ORDER BY p.tsDetected DESC
            """)
    List<Double> findRecentOverruns(
            @Param("machineId") Long machineId,
            @Param("stepId") Long stepId,
            @Param("since") OffsetDateTime since
    );

    @Query("""
    select a
    from PlcAnomaly a
    join a.plcEvent e
    join e.productionStep ps
    where ps.id = :id
      and a.createdAt >= :start
      and a.createdAt < :end
    order by a.tsDetected desc
""")
    List<PlcAnomaly> findAllByIdAndCreatedAtBetween(
            @Param("id") Long id,
            @Param("start") OffsetDateTime start,
            @Param("end") OffsetDateTime end
    );



}
