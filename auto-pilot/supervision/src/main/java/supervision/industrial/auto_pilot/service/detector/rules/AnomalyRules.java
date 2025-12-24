package supervision.industrial.auto_pilot.service.detector.rules;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.PlcEvent;
import supervision.industrial.auto_pilot.service.detector.dto.NominalStep;


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

    private AnomalyRules() {}

    public static List<RuleHit> evaluate(RuleContext ctx) {
        List<RuleHit> hits = new ArrayList<>();
        PlcEvent e = ctx.event();

        // 1) Level / code ERROR
        if (isError(e)) {
            ObjectNode d = M.createObjectNode();
            d.put("level", safe(e.getLevel()));
            d.put("code", safe(e.getCode()));
            hits.add(new RuleHit("PLC_ERROR_LEVEL", "PLC event marked as ERROR", d));
        }

        // 2) Timestamp monotonic for same part
        PlcEvent prev = ctx.previousEventSamePart();
        if (prev != null && prev.getTs() != null && e.getTs() != null) {
            if (e.getTs().isBefore(prev.getTs())) {
                ObjectNode d = M.createObjectNode();
                d.put("prev_ts", prev.getTs().toString());
                d.put("cur_ts", e.getTs().toString());
                hits.add(new RuleHit("TS_DEPHASAGE", "Event timestamp moved backward for same part", d));
            }
        }

        // 3) Gap between steps vs nominal
        if (ctx.previousStepTs() != null && e.getTs() != null) {
            long gapS = Duration.between(ctx.previousStepTs(), e.getTs()).getSeconds();
            if (gapS < 0) {
                ObjectNode d = M.createObjectNode();
                d.put("gap_s", gapS);
                hits.add(new RuleHit("NEGATIVE_INTERVAL", "Negative interval between steps", d));
            } else {
                NominalStep ns = ctx.nominalByStepId().get(e.getStepId());
                if (ns != null && ns.nominalDurationS() != null) {
                    double nominal = Math.max(1.0, ns.nominalDurationS());
                    if (gapS > 3.0 * nominal) {
                        ObjectNode d = M.createObjectNode();
                        d.put("gap_s", gapS);
                        d.put("nominal_s", nominal);
                        hits.add(new RuleHit("INTERVAL_OVERRUN", "Interval exceeds nominal ratio", d));
                    }
                }
            }
        }

        // 4) Workflow order check
        if (prev != null) {
            NominalStep prevNs = ctx.nominalByStepId().get(prev.getStepId());
            NominalStep curNs  = ctx.nominalByStepId().get(e.getStepId());
            if (prevNs != null && curNs != null && prevNs.orderIndex() != null && curNs.orderIndex() != null) {
                int diff = curNs.orderIndex() - prevNs.orderIndex();
                if (diff < 0) {
                    ObjectNode d = M.createObjectNode();
                    d.put("prev_step", safe(prev.getStepId()));
                    d.put("cur_step", safe(e.getStepId()));
                    d.put("prev_idx", prevNs.orderIndex());
                    d.put("cur_idx", curNs.orderIndex());
                    hits.add(new RuleHit("WORKFLOW_BACKWARD", "Step went backward vs nominal order", d));
                } else if (diff > 1) {
                    ObjectNode d = M.createObjectNode();
                    d.put("prev_step", safe(prev.getStepId()));
                    d.put("cur_step", safe(e.getStepId()));
                    d.put("skipped", diff - 1);
                    hits.add(new RuleHit("WORKFLOW_SKIP", "Workflow step(s) skipped vs nominal order", d));
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
