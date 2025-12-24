package supervision.industrial.auto_pilot.service.detector;


import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.repository.ProductionStepRepository;
import supervision.industrial.auto_pilot.service.detector.dto.NominalStep;

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

    private final Map<String, List<NominalStep>> cachedSequence = new ConcurrentHashMap<>();
    private final Map<String, Map<String, NominalStep>> cachedByStepId = new ConcurrentHashMap<>();

    public List<NominalStep> loadNominalSequence(String lineKey) {
        return cachedSequence.computeIfAbsent(lineKey, k -> {
            List<ProductionStep> steps = productionStepRepository.findAll();
            List<NominalStep> seq = new ArrayList<>();
            int idx = 0;
            for (ProductionStep ps : steps) {
                String machine = ps.getMachine() != null ? ps.getMachine().getCode() : null;
                seq.add(new NominalStep(
                        machine,
                        ps.getStepCode(),
                        ps.getName(),
                        idx++,
                        ps.getNominalDurationS()
                ));
            }
            return Collections.unmodifiableList(seq);
        });
    }

    public Map<String, NominalStep> loadNominalByStepId(String lineKey) {
        return cachedByStepId.computeIfAbsent(lineKey, k -> {
            Map<String, NominalStep> m = new HashMap<>();
            for (NominalStep s : loadNominalSequence(lineKey)) {
                if (s.stepId() != null) m.put(s.stepId(), s);
            }
            return Collections.unmodifiableMap(m);
        });
    }

    public void invalidateCache() {
        cachedSequence.clear();
        cachedByStepId.clear();
    }
}
