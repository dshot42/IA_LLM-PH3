package dependancy_bundle.repository;

import dependancy_bundle.model.Line;
import dependancy_bundle.model.RunnerConstante;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface RunnerConstanteRepository extends JpaRepository<RunnerConstante, Long> {

}
