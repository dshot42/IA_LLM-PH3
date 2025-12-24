package supervision.industrial.auto_pilot.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import supervision.industrial.auto_pilot.model.PlcEvent;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

public interface PlcEventRepository extends JpaRepository<PlcEvent, OffsetDateTime> {
    Page<PlcEvent> findByPartIdOrderByTsDesc(String partId, Pageable pageable);

    Page<PlcEvent> findByMachineOrderByTsDesc(String machine, Pageable pageable);

    @Query("select e from PlcEvent e " +
            "where e.partId = :partId and e.ts < :ts " +
            "order by e.ts desc")
    Optional<PlcEvent> findPreviousEventSamePart(@Param("partId") String partId,
                                                 @Param("ts") OffsetDateTime ts);


    @Query("""
                select e
                from PlcEvent e
                where e.machine = :machine
                  and e.stepId = :stepId
                  and e.ts >= :since
                order by e.ts asc
            """)
    List<PlcEvent> history(
            @Param("machine") String machine,
            @Param("stepId") String stepId,
            @Param("since") OffsetDateTime since
    );

    List<PlcEvent> findByPartIdAndTsBetween(
            String partId,
            OffsetDateTime start,
            OffsetDateTime end
    );

    @Query("select max(p.id) from ProductionStep p")
    Long findMaxId();

    PlcEvent findFirstByIdGreaterThanOrderByIdAsc(Long id);


    List<PlcEvent> findAllByIdGreaterThanOrderByIdAsc(Long id);

}
