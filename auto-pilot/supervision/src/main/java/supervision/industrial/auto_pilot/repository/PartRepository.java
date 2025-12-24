package supervision.industrial.auto_pilot.repository;

import org.springframework.data.jpa.repository.Query;
import supervision.industrial.auto_pilot.model.Part;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PartRepository extends JpaRepository<Part, String> {

     Optional<Part> findByExternalPartId(String id);

    @Query("select max(p.id) from Part p")
    Long findMaxId();

    List<Part> findByIdGreaterThan(Long id);
}
