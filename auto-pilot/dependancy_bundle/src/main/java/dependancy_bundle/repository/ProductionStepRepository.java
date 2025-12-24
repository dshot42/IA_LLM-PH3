package dependancy_bundle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import dependancy_bundle.model.ProductionStep;

import java.util.List;

public interface ProductionStepRepository extends JpaRepository<ProductionStep, Long> {

    boolean existsByStepCodeAndMachineId(String stepCode, Integer machineId);

    List<ProductionStep> findAllByOrderByIdAsc();
    /**
     * ORDRE NOMINAL ABSOLU
     */
    @Query("""
        select ps
        from ProductionStep ps
        where ps.machine.code = :machine
        order by ps.id asc
    """)
    List<ProductionStep> findNominalSteps(@Param("machine") String machine);


    ProductionStep findFirstByOrderByIdDesc();
}
