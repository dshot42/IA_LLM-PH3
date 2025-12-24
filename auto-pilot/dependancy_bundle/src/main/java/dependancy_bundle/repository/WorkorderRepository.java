package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import dependancy_bundle.model.Workorder;

import java.util.Optional;

public interface WorkorderRepository extends JpaRepository<Workorder, Long> {
    Optional<Workorder> findById(Long id);

}
