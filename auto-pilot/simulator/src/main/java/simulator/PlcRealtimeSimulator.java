package simulator;

import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.*;

/**
 * Simulateur temps réel PLC
 * - 100% basé sur le workflow BDD
 * - timestamps cohérents avec durées
 * - anomalies industrielles réalistes
 * - compatible détection anomalies / LLM
 */
@Service
public class PlcRealtimeSimulator {

    // =========================
    // CONFIG TEMPS
    // =========================
    private final double speedFactor = 1.0;   // 1.0 = temps réel
    private final double jitterRatio = 0.10;  // +/- 10 %

    // =========================
    // CONFIG ANOMALIES
    // =========================
    private final double slowdownMultiplier = 2.0; // x2 sur certains steps
    private final double dephasingDelayS = 0.6;

    private final double pSlowdown = 0.20;   // 20% des cycles
    private final double pDephasing = 0.15;  // 15% des cycles
    private final double pPlcError = 0.10;   // 10% des cycles

    // =========================
    // DEPENDENCIES
    // =========================
    private final PlcEventDao dao;
    private final WorkflowLoader workflowLoader;

    private final Random rnd = new Random();

    public PlcRealtimeSimulator(
            PlcEventDao dao,
            WorkflowLoader workflowLoader
    ) {
        this.dao = dao;
        this.workflowLoader = workflowLoader;
    }

    // =========================
    // MAIN LOOP
    // =========================
    public void runForever() {

        // 🔹 Charger la ligne depuis la BDD
        WorkflowLoader.LineDto line = new WorkflowLoader.LineDto(1L);

        // 🔹 Charger le workflow runtime depuis la BDD
        WorkflowLoader.WorkflowDefDb wf =
                workflowLoader.loadWorkflow(line);

        // 🔹 Reset tables
        dao.clearTables();

        int cycle = 1;
        int partSeq = 1;

        while (true) {

            String partId = String.format("P%06d", partSeq++);
            dao.insertPart(partId);

            SimClock clock = new SimClock(OffsetDateTime.now());

            // =========================
            // ANOMALIES ACTIVES (aléatoires)
            // =========================
            boolean slowdownM2 = rnd.nextDouble() < pSlowdown;
            boolean dephasing = rnd.nextDouble() < pDephasing;
            boolean plcError = rnd.nextDouble() < pPlcError;

            // =========================
            // CYCLE START
            // =========================
            dao.insertEvent(
                    clock.now(),
                    partId,
                    "SYSTEM",
                    "INFO",
                    "SIM",
                    "CYCLE_START",
                    cycle,
                    "S1",
                    "CYCLE",
                    null,
                    Map.of(
                            "slowdownM2", slowdownM2,
                            "dephasing", dephasing,
                            "plcError", plcError
                    )
            );

            // =========================
            // MACHINES
            // =========================
            for (String machine : wf.machinesOrder()) {

                List<WorkflowLoader.StepDef> steps =
                        wf.microSteps().get(machine);

                double nominalMachine =
                        wf.machinesNominalS().get(machine);

                List<Double> baseDurations =
                        splitNominal(nominalMachine, steps);

                // =========================
                // DEPHASING (désynchro Grafcet)
                // =========================
                if (dephasing && machine.equals("M2")) {
                    dao.insertEvent(
                            clock.now(),
                            partId,
                            machine,
                            "INFO",
                            "SIM",
                            "DEPHASING_DELAY",
                            cycle,
                            "M2.01",
                            "WAIT_M1_READY",
                            dephasingDelayS,
                            Map.of("delay_s", dephasingDelayS)
                    );
                    clock.advanceSeconds(dephasingDelayS);
                    sleepSim(dephasingDelayS);
                }

                // =========================
                // STEPS
                // =========================
                for (int i = 0; i < steps.size(); i++) {

                    WorkflowLoader.StepDef step = steps.get(i);
                    double duration = jitter(baseDurations.get(i));

                    // ---------- SLOWDOWN M2 ----------
                    if (slowdownM2
                            && machine.equals("M2")
                            && Set.of("M2.07", "M2.08", "M2.12").contains(step.id())) {
                        duration *= slowdownMultiplier;
                    }

                    // ---------- STEP START ----------
                    dao.insertEvent(
                            clock.now(),
                            partId,
                            machine,
                            "INFO",
                            "STEP",
                            "STEP",
                            cycle,
                            step.id(),
                            step.name(),
                            duration,
                            Map.of(
                                    "slowdown", slowdownM2,
                                    "dephasing", dephasing
                            )
                    );

                    // ---------- PLC ERROR ----------
                    if (plcError
                            && machine.equals("M2")
                            && Set.of("M2.07", "M2.08").contains(step.id())
                            && rnd.nextDouble() < 0.6) {

                        double errDur = Math.max(duration * 0.3, 0.5);

                        dao.insertEvent(
                                clock.now(),
                                partId,
                                machine,
                                "ERROR",
                                "E-M2-011",
                                "SPINDLE_OVERCURRENT",
                                cycle,
                                step.id(),
                                step.name(),
                                errDur,
                                Map.of(
                                        "error", true,
                                        "cause", "OVERLOAD",
                                        "linked_slowdown", slowdownM2
                                )
                        );

                        clock.advanceSeconds(errDur);
                        sleepSim(errDur);
                    }

                    // ---------- TEMPS QUI PASSE ----------
                    clock.advanceSeconds(duration);
                    sleepSim(duration);

                    // ---------- STEP OK ----------
                    dao.insertEvent(
                            clock.now(),
                            partId,
                            machine,
                            "OK",
                            "OK",
                            "STEP_OK",
                            cycle,
                            step.id(),
                            step.name(),
                            duration,
                            Map.of()
                    );

                    System.out.println("insert event " +step.name());
                }
            }

            // =========================
            // CYCLE END
            // =========================
            dao.insertEvent(
                    clock.now(),
                    partId,
                    "SYSTEM",
                    "INFO",
                    "SIM",
                    "CYCLE_END",
                    cycle,
                    "S6",
                    "CYCLE",
                    null,
                    Map.of()
            );

            cycle++;
        }
    }

    // =========================
    // UTILS
    // =========================

    private void sleepSim(double seconds) {
        double s = Math.max(seconds / Math.max(speedFactor, 1e-9), 0.0);
        try {
            Thread.sleep((long) (s * 1000));
        } catch (InterruptedException ignored) {
        }
    }

    private double jitter(double base) {
        double factor = 1.0 + (rnd.nextDouble() * 2 - 1) * jitterRatio;
        return Math.max(base * factor, 0.05);
    }

    private List<Double> splitNominal(
            double nominal,
            List<WorkflowLoader.StepDef> steps
    ) {
        double[] weights = new double[steps.size()];

        for (int i = 0; i < steps.size(); i++) {
            weights[i] = weight(steps.get(i).name());
        }

        double sum = Arrays.stream(weights).sum();
        if (sum <= 0) sum = 1.0;

        List<Double> durs = new ArrayList<>();
        for (double w : weights) {
            durs.add(nominal * (w / sum));
        }
        return durs;
    }

    private double weight(String stepName) {
        String u = stepName.toUpperCase();
        if (u.contains("PASS") || u.contains("EXEC")) return 0.18;
        if (u.contains("MEASURE") || u.contains("FEATURE")) return 0.12;
        if (u.contains("COMPARE")) return 0.10;
        if (u.contains("ACQ")) return 0.08;
        if (u.contains("WAIT")) return 0.05;
        if (u.contains("CHECK")) return 0.06;
        if (u.contains("RAMP")) return 0.06;
        if (u.contains("CLEAN") || u.contains("CHIP")) return 0.05;
        if (u.contains("SIGNAL")) return 0.03;
        return 0.06;
    }
}
