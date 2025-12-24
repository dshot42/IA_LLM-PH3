package supervision.industrial.auto_pilot.db;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import dependancy_bundle.model.Line;
import dependancy_bundle.model.Machine;
import dependancy_bundle.model.ProductionStep;
import dependancy_bundle.repository.LineRepository;
import dependancy_bundle.repository.MachineRepository;
import dependancy_bundle.repository.ProductionStepRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

@Configuration
public class InitDb {

    @Autowired
    private InitScenario initScenario;

    // =========================
    // BOOTSTRAP RUNNER
    // =========================
    @Bean
    CommandLineRunner initWorkflow(
            ObjectMapper mapper,
            LineRepository lineRepo,
            MachineRepository machineRepo,
            ProductionStepRepository stepRepo
    ) {
        return args -> {
            InputStream is = InitDb.class
                    .getResourceAsStream("/workflow.json");

            if (is == null) {
                throw new IllegalStateException("workflow.json introuvable");
            }

            WorkflowRoot wf = mapper.readValue(is, WorkflowRoot.class);

            initDatabase(wf, lineRepo, machineRepo, stepRepo);
            System.out.println("✅ Workflow industriel initialized");
        };
    }

    // =========================
    // CORE INIT LOGIC
    // =========================
    @Transactional
    void initDatabase(
            WorkflowRoot wf,
            LineRepository lineRepo,
            MachineRepository machineRepo,
            ProductionStepRepository stepRepo
    ) {
        // ---------- LINE ----------
        Line line = lineRepo
                .findByCode("LINE_MAIN")
                .orElseGet(() -> {
                    Line l = new Line();
                    l.setCode("LINE_MAIN");
                    l.setName(wf.ligneIndustrielle.nom());
                    l.setNominalCycleS(wf.ligneIndustrielle.cycleNominalS());
                    return lineRepo.save(l);
                });

        // ---------- MACHINES ----------
        AtomicInteger order = new AtomicInteger(1);

        for (var entry : wf.machines.entrySet()) {
            String machineCode = entry.getKey();
            MachineDTO m = entry.getValue();

            Machine machine = machineRepo
                    .findByCode(machineCode)
                    .orElseGet(() -> {
                        Machine mc = new Machine();
                        mc.setCode(machineCode);
                        mc.setName(m.nom());
                        mc.setDescription(m.description());
                        mc.setIpAddress(m.ip());
                        mc.setPlcProtocol(m.communication().get("PLC"));
                        mc.setOpcuaEndpoint(m.communication().get("OPC_UA"));
                        mc.setLineId(line.getId().intValue());
                        mc.setOrderIndex(order.getAndIncrement());
                        mc.setNominalDurationS(
                                wf.workflowGlobal.dureesNominalesS().get(machineCode)
                        );
                        return machineRepo.save(mc);
                    });

            // ---------- STEPS ----------
            for (StepDTO s : m.steps()) {
                if (!stepRepo.existsByStepCodeAndMachineId(
                        s.id(), machine.getId().intValue()
                )) {
                    ProductionStep ps = new ProductionStep();
                    ps.setStepCode(s.id());
                    ps.setName(s.name());
                    ps.setDescription(s.description());
                    ps.setMachine(machine);
                    ps.setNominalDurationS(s.durationS());
                    stepRepo.save(ps);
                }
            }
        }
        initScenario.generateNominalScenario ();
    }

    // =========================
    // RECORD DTOs
    // =========================

    public record WorkflowRoot(
            @JsonProperty("ligne_industrielle")
            LigneIndustrielle ligneIndustrielle,

            @JsonProperty("workflow_global")
            WorkflowGlobal workflowGlobal,

            @JsonProperty("machines")
            Map<String, MachineDTO> machines
    ) {}


    public record LigneIndustrielle(
            String nom,
            @JsonProperty("cycle_nominal_s")
            Integer cycleNominalS
    ) {
    }

    public record WorkflowGlobal(
            @JsonProperty("ordre_machines")
            List<String> ordreMachines,

            @JsonProperty("durees_nominales_s")
            Map<String, Integer> dureesNominalesS
    ) {
    }

    public record MachineDTO(
            String nom,
            String ip,
            String description,
            Map<String, String> communication,
            List<StepDTO> steps
    ) {
    }

    public record StepDTO(
            String id,
            String name,
            String description,
            @JsonProperty("duration_s")
            Double durationS
    ) {
    }
}
