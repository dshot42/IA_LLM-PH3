package supervision.industrial.auto_pilot.workflow.prompt;

import com.fasterxml.jackson.databind.JsonNode;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import supervision.industrial.auto_pilot.MainConfig;
import supervision.industrial.auto_pilot.api.config.AppConfig;
import supervision.industrial.auto_pilot.api.dto.AnomalyContext;
import supervision.industrial.auto_pilot.api.dto.PlcAnomalyDto;
import supervision.industrial.auto_pilot.api.service.AnomalyContextBuilder;
import supervision.industrial.auto_pilot.api.websocket.AnomalyWebSocketHandler;
import supervision.industrial.auto_pilot.workflow.detector.dto.AnomalyToPromptDto;
import supervision.industrial.auto_pilot.workflow.mapper.PlcAnomalyMapper;

import java.time.OffsetDateTime;
import java.util.List;

@Slf4j
@Service
public class AnomalyPromptService {

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private PlcAnomalyRepository plcAnomalyRepository;

    @Autowired
    private AnomalyWebSocketHandler anomalyWebSocketHandler;

    @Autowired
    private AnomalyContextBuilder anomalyContextBuilder;


    private boolean isSeverePostMortem(PlcAnomaly a) {
        return
                a.getHawkesScore() >= 5 &&
                        a.getEwmaRatio() >= 1.5 &&
                        a.getEventsCount() >= 3;
    }


    private String formatRuleReasons(JsonNode ruleReasons) {
        if (ruleReasons == null || !ruleReasons.isArray() || ruleReasons.isEmpty()) {
            return "Aucune règle déclenchée exploitable.";
        }

        StringBuilder sb = new StringBuilder();
        int i = 1;

        for (JsonNode r : ruleReasons) {

            String ruleName = r.path("rule").asText("N/A");
            String message = r.path("message").asText("N/A");

            sb.append("RÈGLE ").append(i++).append(" : ").append(ruleName).append("\n");
            sb.append("Description brute : ").append(message).append("\n");

            JsonNode d = r.path("details");
            if (d != null && d.isObject()) {

                if (d.has("trigger_condition")) {
                    sb.append("Condition de déclenchement : ")
                            .append(d.get("trigger_condition").asText())
                            .append("\n");
                }

                if (d.has("observed")) {
                    sb.append("Observation mesurée / constatée : ")
                            .append(d.get("observed").asText())
                            .append("\n");
                }

                if (d.has("nominal_ref")) {
                    sb.append("Référence nominale associée : ")
                            .append(d.get("nominal_ref").asText())
                            .append("\n");
                }

                if (d.has("interpretation")) {
                    sb.append("Interprétation fournie par la règle : ")
                            .append(d.get("interpretation").asText())
                            .append("\n");
                }

                if (d.has("confidence")) {
                    sb.append("Niveau de confiance interne à la règle : ")
                            .append(d.get("confidence").asText())
                            .append("\n");
                }

                if (d.has("severity_hint")) {
                    sb.append("Indice de sévérité suggéré par la règle : ")
                            .append(d.get("severity_hint").asText())
                            .append("\n");
                }
            }

            sb.append("----\n");
        }

        return sb.toString().trim();
    }


    private static final String SYSTEM_PROMPT = """
            Tu es un ingénieur process industriel senior spécialisé en analyse d’anomalies PLC.
            
            LANGUE OBLIGATOIRE : FRANÇAIS UNIQUEMENT.
            INTERDICTION ABSOLUE :
            - anglais
            - hypothèses non déduites des données
            - extrapolation
            - justification méthodologique
            - conseil générique
            
            PRINCIPE :
            - Les règles déclenchées constituent la base causale.
            - Le nominal est déjà intégré dans les règles.
            - L’analyse doit rester strictement factuelle.
            
            STYLE :
            - Technique
            - Direct
            - Orienté terrain
            - Aucun ton narratif
            """;


    public String getTemporalDeviationType(PlcAnomaly a) {
        double tolerance = 0.5; // sec a définir avec client
        String temporalDeviationType = "UNKNOWN";

        if (a.getCycleDurationS() != null && a.getProductionStep().getNominalDurationS() != null) {
            double diff = a.getCycleDurationS() - a.getProductionStep().getNominalDurationS();

            if (diff < tolerance) {
                temporalDeviationType = "REAL_SHORTER_THAN_NOMINAL";
                //temporalDeviationType = "production réel inférieur au nominal"
            } else if (diff > tolerance) {
                temporalDeviationType = "REAL_LONGER_THAN_NOMINAL";
                //temporalDeviationType = "production réel supérieur au nominal (anormal)"

            } else {
                temporalDeviationType = "EQUAL_TO_NOMINAL";
                //temporalDeviationType = "production réel conforme nominal (anormal)"
            }
        }
        return temporalDeviationType;
    }

    public void buildPrompt(PlcAnomaly a) {
        AnomalyContext anomalyContext = anomalyContextBuilder.build(a);


        var r = anomalyContext.reccurenceAnomalyAnalyseDto();

        String recurrenceBlock = r == null ? "" : String.format("""
                        
                        ANALYSE DE RÉCURRENCE TEMPORELLE :
                        - Fenêtre d’analyse        : %d jours
                        - Occurrences observées   : %d
                        - Intervalle moyen        : %.2f s
                        - Écart-type intervalle   : %.2f s
                        - Overrun moyen           : %.2f s
                        - Écart-type overrun      : %.2f s
                        - Fréquence en hausse     : %s
                        - Impact temporel en hausse : %s
                        - Tendance globale : %s
                        """,
                r.windowDays(),
                r.totalOccurrences(),
                r.meanIntervalS(),
                r.stdDevIntervalS(),
                r.meanOverrunS(),
                r.stdDevOverrunS(),
                r.frequencyIncreasing() ? "OUI" : "NON",
                r.overrunIncreasing() ? "OUI" : "NON",
                r.trendConclusion()
        );


        /// ////////////////////

        List<PlcAnomalyDto> similar = anomalyContext.allSimilarAnomalies();

        int similarCount = similar != null ? similar.size() : 0;

        boolean veryRecentRecurrence = false;
        if (similarCount > 0) {
            OffsetDateTime last = OffsetDateTime.parse(similar.get(0).plcEventTs()); // si tri DESC
            veryRecentRecurrence = last.isAfter(OffsetDateTime.now().minusMinutes(10));
        }
        String similarHistoryBlock = similarCount == 0 ? "" : String.format("""
                        
                        HISTORIQUE DES ANOMALIES SIMILAIRES :
                        - Nombre d’anomalies similaires récentes : %d
                        - Récurrence très récente (< 10 min)     : %s
                        - Analyse :
                          Ces anomalies concernent des étapes comparables du workflow
                          et doivent être prises en compte dans l’évaluation de la criticité.
                        """,
                similarCount,
                veryRecentRecurrence ? "OUI" : "NON"
        );


        String userPrompt = String.format("""
                        OBJECTIF :
                        Analyser UNE anomalie de production par comparaison stricte
                        entre comportement nominal et comportement réel observé.
                        
                        DONNÉES OPÉRATIONNELLES :
                        - Pièce              : %s
                        - Machine            : %s
                        - Step               : %s
                        - Cycle              : %d
                        
                        DONNÉES TEMPORELLES :
                        - Durée nominale     : %.2f s
                        - Durée réelle       : %s
                        - Écart mesuré       : %s
                        - Type d’écart       : %s
                        
                        RÈGLES DÉCLENCHÉES :
                        %s
                        
                        INDICATEURS STATISTIQUES :
                        - Occurrences        : %d
                        - EWMA ratio         : %.2f
                        - Rate ratio         : %.2f
                        - Hawkes score       : %d
                        - Confiance          : %s
                        - Sévérité           : %s
                        
                        %s
                        
                        %s
                        
                        FORMAT DE SORTIE OBLIGATOIRE :
                        
                        ANOMALIE :
                        Décrire factuellement l’anomalie détectée.
                        
                        COMPORTEMENT RÉEL :
                        Décrire la séquence réelle observée à partir des règles.
                        
                        ÉCART NOMINAL / RÉEL :
                        Qualifier l’écart sans inversion cause / conséquence.
                        
                        IMPACT PRODUCTION :
                        Indiquer l’impact opérationnel mesurable.
                        Si non quantifiable, écrire explicitement : NON ÉVALUABLE.
                        
                        CRITICITÉ :
                        Justifier la criticité à partir :
                        - de l’écart mesuré
                        - des règles déclenchées
                        - des indicateurs statistiques
                        - des tendances de récurrence temporelle
                        - de l’historique des anomalies similaires
                        
                        CONCLUSION :
                        Conclusion explicite, factuelle et complète.
                        """,
                a.getPart().getExternalPartId(),
                a.getMachine().getCode(),
                a.getProductionStep().getStepCode(),
                a.getCycle(),
                a.getProductionStep().getNominalDurationS(),
                a.getCycleDurationS() == null ? "N/A" : String.format("%.2f s", a.getCycleDurationS()),
                a.getDurationOverrunS() == null ? "N/A" : String.format("%.2f s", a.getDurationOverrunS()),
                getTemporalDeviationType(a),
                formatRuleReasons(a.getRuleReasons()),
                a.getEventsCount(),
                a.getEwmaRatio(),
                a.getRateRatio(),
                a.getHawkesScore(),
                a.getConfidence(),
                a.getSeverity(),
                recurrenceBlock,
                similarHistoryBlock
        );


        String reportPath = sendPost(SYSTEM_PROMPT, userPrompt, a, anomalyContext);
        a.setReportPath(reportPath);
        plcAnomalyRepository.save(a);
        anomalyWebSocketHandler.emitAnomalieCompleted(a);
    }


    public record AnomalyRequest(
            String systemPrompt,
            String userPrompt,
            AnomalyToPromptDto anomaly
    ) {
    }


    public String sendPost(String systemPrompt, String userPrompt, PlcAnomaly anomaly, AnomalyContext anomalyContext) {
        try {
            if (!MainConfig.boowithLLM) return null;
            String url = AppConfig.getUrl("/ia_api/anomaly");
            AnomalyToPromptDto dto = PlcAnomalyMapper.toDto(anomaly, anomalyContext);
            AnomalyRequest request = new AnomalyRequest(systemPrompt, userPrompt, dto);

            log.info("Anomaly -> Send Anomaly PROMPT to LLM  ");
            String result = restTemplate.postForObject(url, request, String.class);
            log.info("[SUCCESS] Anomaly -> LLM response : {}", result);
            return result;
        } catch (Exception e) {
            log.error("[ERROR] Anomaly -> LLM doesn't response !");
        }
        return null;
    }


}