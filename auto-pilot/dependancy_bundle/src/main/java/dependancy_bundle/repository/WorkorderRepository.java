package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import dependancy_bundle.model.Workorder;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

public interface WorkorderRepository extends JpaRepository<Workorder, Long> {
    Optional<Workorder> findById(Long id);

    @Modifying
    @Transactional
    @Query(value = "DELETE FROM workorder", nativeQuery = true)
    void truncateWorkorders();

    List<Workorder> findAllByStartedAtBetween(
            OffsetDateTime start,
            OffsetDateTime end
    );

}
