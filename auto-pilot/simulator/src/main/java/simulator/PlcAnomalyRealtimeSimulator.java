package simulator;

import com.fasterxml.jackson.databind.ObjectMapper;
import dependancy_bundle.model.*;
import dependancy_bundle.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
public class PlcAnomalyRealtimeSimulator {


    private final PlcEventRepository plcEventRepository;
    private final MachineRepository machineRepository;
    private final WorkorderRepository workorderRepository;
    private final PartRepository partRepository;
    private final ProductionScenarioRepository productionScenarioRepository;
    private final PlcAnomalyRepository plcAnomalyRepository;
    private final RunnerConstanteRepository runnerConstanteRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Random rnd = new Random();

    private final double speedFactor = 1.0;
    private final double jitterRatio = 0.10;

    // =========================
    // CONFIG ANOMALIES
    // =========================
    private final double slowdownMultiplier = 2.0;
    private final double dephasingDelayS = 3;

    private final double pSlowdown = 0.20;
    private final double pDephasing = 0.15;
    private final double pPlcError = 0.10;
    private final double pSkipStep = 0.12; // 🆕 skip step

    // =========================
    // MAIN LOOP
    // =========================

    private Workorder createWorkorder() {
        Workorder wo = new Workorder();
        wo.setNbPartToProduce(100L);
        wo.setStatus("IN_PROGRESS");
        wo.setProductionScenario(
                productionScenarioRepository.getProductionScenarioByName("NOMINAL")
        );
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

        RunnerConstante runnerConstante = runnerConstanteRepository.findAll().stream().findFirst().get();
        runnerConstante.setLastAnomalyAnalise(0L);
        runnerConstante.setLastCurrentEvent(0L);
        runnerConstanteRepository.save(runnerConstante);

        plcAnomalyRepository.truncatePlcAnomalies();
        plcEventRepository.truncatePlcEvents();
        partRepository.truncateParts();
        workorderRepository.truncateWorkorders();
    }


    public void runForever() {

        clearDb();
        List<Machine> machines =
                machineRepository.findByLineIdOrderByIdAsc(1);

        Workorder wo = createWorkorder();

        int cycle = 1;
        int partSeq = 1;

        while (true) {

            Part part = createPart(String.format("P%06d", partSeq++));
            SimClock clock = new SimClock(OffsetDateTime.now());

            boolean slowdownM2 = rnd.nextDouble() < pSlowdown;
            boolean dephasing = rnd.nextDouble() < pDephasing;
            boolean plcError = rnd.nextDouble() < pPlcError;

            for (Machine machine : machines) {

                List<ProductionStep> steps = machine.getProductionSteps();
                if (steps == null || steps.isEmpty()) continue;

                double nominalMachine = machine.getNominalDurationS();
                List<Double> baseDurations = splitNominal(nominalMachine, steps);

                int expectedIndex = 0;

                for (int i = 0; i < steps.size(); i++) {

                    ProductionStep step = steps.get(i);

                    // =========================
                    // STEP SKIP (ANOMALY)
                    // =========================
                    boolean skipStep =
                            rnd.nextDouble() < pSkipStep
                                    && machine.getCode().equals("M2")
                                    && Set.of("M2.07", "M2.08").contains(step.getStepCode());

                    if (skipStep) {
                        System.out.println(
                                "[ANOMALY][STEP_SKIP] machine=" + machine.getCode()
                                        + " part=" + part.getExternalPartId()
                                        + " cycle=" + cycle
                                        + " step=" + step.getStepCode()
                        );
                        continue; // ⛔ step non exécuté
                    }

                    // =========================
                    // STEP ORDER CHECK (INCHANGÉ)
                    // =========================
                    if (i != expectedIndex) {
                        System.out.println(
                                "[ANOMALY][STEP_ORDER] machine=" + machine.getCode()
                                        + " part=" + part.getExternalPartId()
                                        + " cycle=" + cycle
                                        + " expected_index=" + expectedIndex
                                        + " actual_index=" + i
                                        + " step=" + step.getStepCode()
                        );
                    }
                    expectedIndex++;

                    double duration = jitter(baseDurations.get(i));

                    // =========================
                    // SLOWDOWN (INCHANGÉ)
                    // =========================
                    if (slowdownM2
                            && machine.getCode().equals("M2")
                            && Set.of("M2.07", "M2.08", "M2.12")
                            .contains(step.getStepCode())) {
                        duration *= slowdownMultiplier;
                    }

                    // =========================
                    // DEPHASING = OVERUN TRS
                    // =========================
                    if (dephasing && machine.getCode().equals("M2")) {
                        duration = duration * dephasingDelayS; // 🔥 overrun réel
                        System.out.println("Dephasing " + step.getStepCode());
                    }

                    // =========================
                    // STEP START
                    // =========================
                    persistEvent(
                            clock.now(),
                            part,
                            machine,
                            step,
                            "INFO",
                            "STEP",
                            "STEP",
                            cycle,
                            duration,
                            Map.of(
                                    "slowdown", slowdownM2,
                                    "dephasing", dephasing,
                                    "skip", false
                            ),
                            wo
                    );


                    if (plcError
                            && machine.getCode().equals("M2")
                            && Set.of("M2.07", "M2.08")
                            .contains(step.getStepCode())
                            && rnd.nextDouble() < 0.6) {

                        double errDur = Math.max(duration * 0.3, 0.5);
                        System.out.println("ERROR " + step.getStepCode());

                        persistEvent(
                                clock.now(),
                                part,
                                machine,
                                step,
                                "ERROR",
                                "E-M2-011",
                                "SPINDLE_OVERCURRENT",
                                cycle,
                                errDur,
                                Map.of("error", true),
                                wo
                        );

                        clock.advanceSeconds(errDur);
                        sleepSim(errDur);
                    }

                    clock.advanceSeconds(duration);
                    sleepSim(duration);

                    // =========================
                    // STEP OK
                    // =========================
                    persistEvent(
                            clock.now(),
                            part,
                            machine,
                            step,
                            "OK",
                            "OK",
                            "STEP_OK",
                            cycle,
                            duration,
                            Map.of(),
                            wo
                    );
                }
            }

            cycle++;
        }
    }

    // =========================
    // UTILS
    // =========================

    // =========================
    // PERSIST EVENT
    // =========================
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

        e = plcEventRepository.save(e);

        System.out.println(
                "INSERT EVENT "
                        + machine.getCode()
                        + " / "
                        + step.getStepCode()
                        + " / "
                        + code
        );
    }

    private void sleepSim(double seconds) {
        try {
            Thread.sleep((long) (seconds * 1000 / speedFactor));
        } catch (InterruptedException ignored) {
        }
    }

    private double jitter(double base) {
        double factor = 1.0 + (rnd.nextDouble() * 2 - 1) * jitterRatio;
        return Math.max(base * factor, 0.05);
    }

    private List<Double> splitNominal(
            double nominal,
            List<ProductionStep> steps
    ) {
        double w = 1.0 / steps.size();
        List<Double> durs = new LinkedList<>();
        for (int i = 0; i < steps.size(); i++) {
            durs.add(nominal * w);
        }
        return durs;
    }
}

