package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import supervision.industrial.auto_pilot.model.Line;

import java.util.Optional;

public interface LineRepository extends JpaRepository<Line, Long> {

    Optional<Line> findByCode(String code);
}
