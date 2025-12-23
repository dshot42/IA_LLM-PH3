package simulator;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
@Transactional(readOnly = true)
public class WorkflowLoader {

    @PersistenceContext
    private EntityManager em;

    public record StepDef(
            String id,
            String name
    ) {}

    public record WorkflowDefDb(
            List<String> machinesOrder,
            Map<String, Double> machinesNominalS,
            Map<String, List<StepDef>> microSteps
    ) {}

    public record LineDto(
            Long id
    ) {}

    public WorkflowDefDb loadWorkflow(LineDto line) {

        Long lineId = line.id;

        // =========================
        // 1️⃣ Ordre des machines
        // =========================
        List<String> machinesOrder = em.createNativeQuery("""
            select m.code
            from machine m
            where m.line_id = :lineId
            order by m.id
        """)
                .setParameter("lineId", lineId.intValue())
                .getResultList();

        // =========================
        // 2️⃣ Durées nominales
        // =========================
        Map<String, Double> machinesNominal = new HashMap<>();

        List<Object[]> nominalRows = em.createNativeQuery("""
            select m.code, m.nominal_duration_s
            from machine m
            where m.line_id = :lineId
        """)
                .setParameter("lineId", lineId.intValue())
                .getResultList();

        for (Object[] r : nominalRows) {
            machinesNominal.put(
                    (String) r[0],
                    ((Number) r[1]).doubleValue()
            );
        }

        // =========================
        // 3️⃣ Micro-steps
        // =========================
        Map<String, List<StepDef>> microSteps = new LinkedHashMap<>();

        List<Object[]> stepRows = em.createNativeQuery("""
            select m.code, ps.step_code, ps.name
            from production_step ps
            join machine m on m.id = ps.machine_id
            where m.line_id = :lineId
            order by m.id, ps.step_code
        """)
                .setParameter("lineId", lineId.intValue())
                .getResultList();

        for (Object[] r : stepRows) {
            String machine = (String) r[0];
            String stepId  = (String) r[1];
            String name    = (String) r[2];

            microSteps
                    .computeIfAbsent(machine, k -> new ArrayList<>())
                    .add(new StepDef(stepId, name));
        }

        return new WorkflowDefDb(
                machinesOrder,
                machinesNominal,
                microSteps
        );
    }
}
