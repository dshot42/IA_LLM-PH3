package dependancy_bundle.repository;

import dependancy_bundle.model.Kpi;
import dependancy_bundle.model.KpiMeasure;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

public interface KpiMeasureRepository extends JpaRepository<KpiMeasure, Long> {
    @Modifying
    @Transactional
    @Query(value = "DELETE FROM kpi_measure", nativeQuery = true)
    void truncateKpiMeasure();

}