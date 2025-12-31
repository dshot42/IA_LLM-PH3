package simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import dependancy_bundle.model.*;
import dependancy_bundle.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class PlcNominalRealtimeSimulator {

    private final PlcEventRepository plcEventRepository;
    private final WorkorderRepository workorderRepository;
    private final PartRepository partRepository;
    private final ProductionScenarioRepository productionScenarioRepository;
    private final RunnerConstanteRepository runnerConstanteRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private final double speedFactor = 1.0;

    private Workorder createWorkorder(ProductionScenario scenario) {
        Workorder wo = new Workorder();
        wo.setNbPartToProduce(100L);
        wo.setStatus("IN_PROGRESS");
        wo.setProductionScenario(scenario);
        return workorderRepository.save(wo);
    }

    public Part createPart(String externalPartId) {
        Part p = new Part();
        p.setExternalPartId(externalPartId);
        p.setLineId(1);
        p.setStatus("IN_PROGRESS");
        return partRepository.save(p);
    }

    @Transactional
    public void clearDb() {
        RunnerConstante runnerConstante = runnerConstanteRepository.findAll()
                .stream().findFirst()
                .orElseThrow(() -> new IllegalStateException("RunnerConstante manquant"));

        runnerConstante.setLastAnomalyAnalise(0L);
        runnerConstante.setLastCurrentEvent(0L);
        runnerConstanteRepository.save(runnerConstante);

        plcEventRepository.truncatePlcEvents();
        partRepository.truncateParts();
        workorderRepository.truncateWorkorders();
    }

    public void runForever() {

        clearDb();

        ProductionScenario scenario = productionScenarioRepository.getProductionScenarioByName("NOMINAL");
        if (scenario == null) throw new IllegalStateException("Scenario NOMINAL introuvable");

        // IMPORTANT : il faut une liste ORDONNÉE
        List<?> scenarioSteps = getOrderedScenarioSteps(scenario);

        Workorder wo = createWorkorder(scenario);

        int cycle = 1;
        int partSeq = 1;

        while (true) {

            Part part = createPart(String.format("P%06d", partSeq++));
            SimClock clock = new SimClock(OffsetDateTime.now());

            // Exécution STRICTE du scenario
            for (Object ss : scenarioSteps) {

                // A ADAPTER : selon tes classes réelles
                Machine machine = extractMachine(ss);
                ProductionStep step = extractProductionStep(ss);

                double nominalDuration = extractNominalDurationS(ss, step);

                // STEP START
                persistEvent(
                        clock.now(),
                        part,
                        machine,
                        step,
                        "INFO",
                        "STEP",
                        "STEP",
                        cycle,
                        nominalDuration,
                        Map.of("scenario", scenario.getName(), "nominal", true),
                        wo
                );

                clock.advanceSeconds(nominalDuration);
                sleepSim(nominalDuration);

                // STEP OK
                persistEvent(
                        clock.now(),
                        part,
                        machine,
                        step,
                        "OK",
                        "OK",
                        "STEP_OK",
                        cycle,
                        nominalDuration,
                        Map.of("scenario", scenario.getName(), "nominal", true),
                        wo
                );
            }

            cycle++;
        }
    }

    // -------------------------
    // ADAPTATION : mapping scenario -> steps ordonnés
    // -------------------------

    /**
     * Tu DOIS retourner la liste de steps du scenario dans l’ordre.
     * Exemple : scenario.getSteps().stream().sorted(comparingInt(ScenarioStep::getPosition)).toList()
     */
    private List<?> getOrderedScenarioSteps(ProductionScenario scenario) {
        // TODO adapte à ton modèle
        // return scenario.getScenarioSteps().stream()
        //     .sorted(Comparator.comparingInt(ScenarioStep::getPosition))
        //     .toList();
        throw new UnsupportedOperationException("À adapter à ton modèle ProductionScenario");
    }

    private Machine extractMachine(Object scenarioStep) {
        // TODO : return ((ScenarioStep)scenarioStep).getMachine();
        throw new UnsupportedOperationException("À adapter");
    }

    private ProductionStep extractProductionStep(Object scenarioStep) {
        // TODO : return ((ScenarioStep)scenarioStep).getProductionStep();
        throw new UnsupportedOperationException("À adapter");
    }

    private double extractNominalDurationS(Object scenarioStep, ProductionStep step) {
        // Priorité au lien scenarioStep si tu as une durée spécifique.
        // TODO : return ((ScenarioStep)scenarioStep).getNominalDurationS();
        // sinon: return step.getNominalDurationS();
        throw new UnsupportedOperationException("À adapter");
    }

    // -------------------------
    // PERSIST / TIME
    // -------------------------
    private void persistEvent(
            OffsetDateTime ts,
            Part part,
            Machine machine,
            ProductionStep step,
            String level,
            String code,
            String message,
            Integer cycle,
            Double duration,
            Map<String, Object> payload,
            Workorder wo
    ) {
        PlcEvent e = new PlcEvent();
        e.setTs(ts);
        e.setPart(part);
        e.setMachine(machine);
        e.setProductionStep(step);
        e.setLevel(level);
        e.setCode(code);
        e.setMessage(message);
        e.setCycle(cycle);
        e.setDuration(duration);
        e.setPayload(objectMapper.valueToTree(payload));
        e.setWorkorder(wo);

        plcEventRepository.save(e);

        System.out.println("INSERT EVENT " + machine.getCode() + " / " + step.getStepCode() + " / " + code);
    }

    private void sleepSim(double seconds) {
        try {
            Thread.sleep((long) (seconds * 1000 / speedFactor));
        } catch (InterruptedException ignored) {
        }
    }
}
