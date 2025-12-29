package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import dependancy_bundle.model.Part;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

public interface PartRepository extends JpaRepository<Part, Long> {

     Optional<Part> findByExternalPartId(String id);

    @Query("select max(p.id) from Part p")
    Long findMaxId();

    List<Part> findByIdGreaterThan(Long id);

    @Modifying
    @Transactional
    @Query(value = "DELETE FROM part", nativeQuery = true)
    void truncateParts();
}
