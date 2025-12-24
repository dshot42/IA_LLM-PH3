package dependancy_bundle.repository;

import dependancy_bundle.model.Line;
import org.springframework.data.jpa.repository.JpaRepository;


import java.util.Optional;

public interface LineRepository extends JpaRepository<Line, Long> {

    Optional<Line> findByCode(String code);
}
