package dependancy_bundle.repository;


import dependancy_bundle.model.Part;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.Workorder;
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

public interface PlcEventRepository extends JpaRepository<PlcEvent, OffsetDateTime> {
    Page<PlcEvent> findByPartIdOrderByTsDesc(String partId, Pageable pageable);

    Page<PlcEvent> findByMachineOrderByTsDesc(String machine, Pageable pageable);

    Optional<PlcEvent> findFirstByPartIdAndTsBeforeOrderByTsDesc(
            Long partId,
            OffsetDateTime ts
    );

    List<PlcEvent> findByPartAndTsBetween(
            Part part,
            OffsetDateTime start,
            OffsetDateTime end
    );


    List<PlcEvent> findByPart(
            Part part
    );

    @Query("select max(p.id) from PlcEvent p")
    Long findMaxId();

    PlcEvent findFirstByIdGreaterThanOrderByIdAsc(Long id);


    List<PlcEvent> findAllByIdGreaterThanOrderByIdAsc(Long id);

    @Modifying
    @Transactional
    @Query(value = "DELETE FROM plc_events", nativeQuery = true)
    void truncatePlcEvents();



    List<PlcEvent> findAllByTsBetween(
            OffsetDateTime start,
            OffsetDateTime end
    );


}
