package supervision.industrial.auto_pilot.service.detector;


import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.repository.ProductionStepRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Charge le workflow nominal depuis la BDD (machine + production_step).
 * Cache en mémoire pour éviter de relire tout le temps.
 */
@Service
@RequiredArgsConstructor

public class WorkflowNominalService {

    private final ProductionStepRepository productionStepRepository;

    private final Map<Long, List<ProductionStep>> cachedSequence = new ConcurrentHashMap<>();
    private final Map<Long, Map<Long, ProductionStep>> cachedByStepId = new ConcurrentHashMap<>();

    public List<ProductionStep> loadNominalSequence(Long idWo) {
        return cachedSequence.computeIfAbsent(idWo, k -> {
            List<ProductionStep> steps = productionStepRepository.findAll();
            return List.copyOf(steps);
        });
    }

    public Map<Long, ProductionStep> loadNominalByStepId(Long idWo) {
        return cachedByStepId.computeIfAbsent(idWo, k -> {
            Map<Long, ProductionStep> m = new HashMap<>();
            for (ProductionStep s : loadNominalSequence(idWo)) {
                if (s.getId() != null) {
                    m.put(s.getId(), s);
                }
            }
            return m;
        });
    }

    public void invalidateCache() {
        cachedSequence.clear();
        cachedByStepId.clear();
    }
}

