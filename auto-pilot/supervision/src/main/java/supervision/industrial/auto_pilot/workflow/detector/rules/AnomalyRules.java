package supervision.industrial.auto_pilot.workflow.detector.rules;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.PlcEvent;
import dependancy_bundle.model.ProductionScenarioStep;
import dependancy_bundle.model.ProductionStep;
import supervision.industrial.auto_pilot.MainConfig;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Règles déterministes :
 * - level==ERROR ou code==ERROR
 * - déphasage timestamps (ts non monotone)
 * - intervalle anormal entre steps vs nominal
 * - saut / retour en arrière dans l'ordre workflow nominal
 */
public final class AnomalyRules {

    private static final ObjectMapper M = new ObjectMapper();

    private AnomalyRules() {
    }

    public static List<RuleHit> evaluate(RuleContext ctx) {
        List<RuleHit> hits = new ArrayList<>();
        PlcEvent e = ctx.event();

        // =====================================================
        // 1) Level / code ERROR
        // =====================================================
        if (isError(e)) {
            ObjectNode d = M.createObjectNode();
            d.put("event_level", safe(e.getLevel()));
            d.put("event_code", safe(e.getCode()));
            d.put("trigger_condition", "event.level == ERROR OR event.code == ERROR");
            d.put("observed", "PLC event explicitly flagged as ERROR");
            d.put("interpretation",
                    "L'événement PLC indique explicitement un état d'erreur au niveau automate.");
            d.put("severity_hint", "MAJOR");
            d.put("confidence", 0.85);

            hits.add(new RuleHit(
                    "PLC_ERROR_LEVEL",
                    "PLC event marked as ERROR",
                    d
            ));
        }

        // =====================================================
        // 2) Timestamp monotonic for same part
        // =====================================================
        PlcEvent prev = ctx.previousEventSamePart();
        if (prev != null && prev.getTs() != null && e.getTs() != null) {
            if (e.getTs().isBefore(prev.getTs())) {

                ObjectNode d = M.createObjectNode();
                d.put("previous_event_ts", prev.getTs().toString());
                d.put("current_event_ts", e.getTs().toString());
                d.put("trigger_condition", "current_event_ts < previous_event_ts (same part)");
                d.put(
                        "observed",
                        "Timestamp courant antérieur au timestamp précédent pour la même pièce"
                );
                d.put(
                        "interpretation",
                        "Incohérence temporelle détectée dans la séquence des événements PLC pour une même pièce."
                );
                d.put("severity_hint", "MAJOR");
                d.put("confidence", 0.85);

                hits.add(new RuleHit(
                        "TS_DEPHASAGE",
                        "Event timestamp moved backward for same part",
                        d
                ));
            }
        }

        // =====================================================
        // 3) Gap between steps vs nominal
        // =====================================================
        if (ctx.previousStepTs() != null && e.getTs() != null) {

            long gapS = Duration.between(ctx.previousStepTs(), e.getTs()).getSeconds();


            if (e.getProductionStep() != null) {

                ProductionStep ns =
                        ctx.nominalByStepId().get(e.getProductionStep().getId());

                if (ns != null && ns.getNominalDurationS() != null) {

                    double nominal = Math.max(1.0, ns.getNominalDurationS());
                    double threshold = MainConfig.toleranceOverrun * nominal;

                    if (gapS > threshold) {

                        ObjectNode d = M.createObjectNode();
                        d.put("previous_step_ts", ctx.previousStepTs().toString());
                        d.put("current_step_ts", e.getTs().toString());
                        d.put("observed_gap_seconds", gapS);
                        d.put("nominal_step_duration_seconds", nominal);
                        d.put("threshold_seconds", threshold);
                        d.put(
                                "trigger_condition",
                                "observed_gap_seconds > 1.1 * nominal_step_duration_seconds"
                        );
                        d.put(
                                "interpretation",
                                "La durée observée entre deux steps dépasse le seuil nominal autorisé."
                        );

                        hits.add(new RuleHit(
                                "INTERVAL_OVERRUN",
                                "Interval exceeds nominal ratio",
                                d
                        ));
                    }
                }

            }
        }

        // =====================================================
        // 4) Workflow order check (ProductionScenarioStep.stepOrder)
        // =====================================================
        if (prev != null
                && prev.getProductionStep() != null
                && e.getProductionStep() != null
                && e.getWorkorder() != null
                && e.getWorkorder().getProductionScenario() != null
                && e.getWorkorder().getProductionScenario().getProductionScenarioSteps() != null) {

            List<ProductionScenarioStep> scenarioSteps =
                    e.getWorkorder()
                            .getProductionScenario()
                            .getProductionScenarioSteps();

            ProductionScenarioStep prevScStep = scenarioSteps.stream()
                    .filter(s ->
                            s.getProductionStep().getId()
                                    .equals(prev.getProductionStep().getId()))
                    .findFirst()
                    .orElse(null);

            ProductionScenarioStep curScStep = scenarioSteps.stream()
                    .filter(s ->
                            s.getProductionStep().getId()
                                    .equals(e.getProductionStep().getId()))
                    .findFirst()
                    .orElse(null);

            if (prevScStep != null && curScStep != null) {

                long diff = curScStep.getStepOrder() - prevScStep.getStepOrder();

                if (diff < 0) {
                    ObjectNode d = M.createObjectNode();
                    d.put("previous_step_code", prev.getProductionStep().getStepCode());
                    d.put("current_step_code", e.getProductionStep().getStepCode());
                    d.put("previous_step_order", prevScStep.getStepOrder());
                    d.put("current_step_order", curScStep.getStepOrder());
                    d.put("trigger_condition", "current_step_order < previous_step_order");
                    d.put(
                            "observed",
                            "Retour en arrière dans l'ordre des steps du workflow"
                    );
                    d.put(
                            "interpretation",
                            "Le step courant apparaît avant le step précédent dans l'ordre nominal défini."
                    );

                    hits.add(new RuleHit(
                            "SEQUENCE_ERROR",
                            "Workflow step went backward vs nominal order",
                            d
                    ));

                } else if (diff > 1) {
                    ObjectNode d = M.createObjectNode();
                    d.put("previous_step_code", prev.getProductionStep().getStepCode());
                    d.put("current_step_code", e.getProductionStep().getStepCode());
                    d.put("previous_step_order", prevScStep.getStepOrder());
                    d.put("current_step_order", curScStep.getStepOrder());
                    d.put("skipped_steps_count", diff - 1);
                    d.put(
                            "trigger_condition",
                            "current_step_order > previous_step_order + 1"
                    );
                    d.put(
                            "observed",
                            "Un ou plusieurs steps intermédiaires non observés dans la séquence réelle"
                    );
                    d.put(
                            "interpretation",
                            "La séquence réelle saute un ou plusieurs steps définis dans le workflow nominal."
                    );

                    hits.add(new RuleHit(
                            "SEQUENCE_ERROR",
                            "Workflow step(s) skipped vs nominal order",
                            d
                    ));
                }
            }
        }

        return hits;
    }

    private static boolean isError(PlcEvent e) {
        return "ERROR".equalsIgnoreCase(safe(e.getLevel()))
                || "ERROR".equalsIgnoreCase(safe(e.getCode()));
    }

    private static String safe(String s) {
        return s == null ? "" : s;
    }
}
