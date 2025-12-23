package supervision.industrial.auto_pilot.repository;

import supervision.industrial.auto_pilot.model.Part;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PartRepository extends JpaRepository<Part, String> {
}
