package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import supervision.industrial.auto_pilot.model.Workorder;

import java.util.Optional;

public interface WorkorderRepository extends JpaRepository<Workorder, Long> {
    Optional<Workorder> findById(Long id);

}
