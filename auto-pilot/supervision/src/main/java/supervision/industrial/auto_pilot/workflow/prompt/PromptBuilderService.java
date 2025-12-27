package supervision.industrial.auto_pilot.service.prompt;

import com.fasterxml.jackson.databind.JsonNode;
import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.repository.PlcAnomalyRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import supervision.industrial.auto_pilot.config.AppConfig;
import supervision.industrial.auto_pilot.service.detector.dto.AnomalyToPromptDto;
import supervision.industrial.auto_pilot.service.mapper.PlcAnomalyMapper;
import supervision.industrial.auto_pilot.websocket.AnomalyWebSocketHandler;

@Slf4j
@Service
public class PromptBuilderService {

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private PlcAnomalyRepository plcAnomalyRepository;

    @Autowired
    private AnomalyWebSocketHandler anomalyWebSocketHandler;


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


    private static final String SYSTEM_PROMPT_SEVERE = """
            Tu es un ingénieur process industriel senior en mode POST-MORTEM SÉVÈRE.
            
            CONTEXTE :
            - L’anomalie est statistiquement récurrente et significative.
            - Hawkes, EWMA et récurrence indiquent un comportement non aléatoire.
            - Le scénario nominal reste la référence absolue.
            
            RÈGLE DE PRIORITÉ CAUSALE :
            - En présence d’une erreur PLC explicite :
              - Les écarts temporels ou déphasages doivent être CONSTATES.
              - Les écarts temporels ne doivent JAMAIS être considérés comme la cause racine.
              - La cause principale est STRICTEMENT événementielle.
              - Le déphasage est analysé comme une conséquence ou un symptôme.
            
            OBLIGATIONS SUPPLÉMENTAIRES :
            - Reconstituer la séquence réelle événement par événement.
            - Identifier :
              - cause déclenchante (événement PLC)
              - mécanisme aggravant (rebouclage, retry, saut de step)
              - conséquence opérationnelle (déphasage, cycle tronqué, désynchronisation).
            - Appuyer toute conclusion sur les règles déclenchées et la documentation fournie.
            
            INTERDICTIONS RENFORCÉES :
            - Aucun euphémisme.
            - Aucune inversion cause / conséquence.
            - Toute incertitude doit être explicitement qualifiée.
            
            Le rapport doit être exhaustif, rigoureux et orienté diagnostic terrain.
            """;


    String SYSTEM_PROMPT_STANDARD = """
            Tu es un ingénieur process industriel senior expert en PLC, Grafcet et supervision de lignes automatisées.
            
            RÈGLES ABSOLUES :
            - Le scénario nominal reste la référence absolue.
            - Toute analyse DOIT comparer STRICTEMENT le réel au nominal.
            - Aucune hypothèse non fondée sur les données fournies.
            - Aucune information externe.
            
            RÈGLE DE PRIORITÉ CAUSALE :
            - Si une erreur PLC est présente :
              - Le déphasage ou écart de durée doit être mentionné.
              - Le déphasage ne peut PAS être retenu comme cause principale.
              - L’analyse devient prioritairement événementielle.
            - L’analyse temporelle comme cause n’est autorisée
              QUE s’il n’existe aucune erreur PLC explicite.
            
            STYLE :
            - Rapport technique détaillé, verbeux, opérationnel.
            - Pas de Markdown. Pas de résumé exécutif.
            
            CONTRAINTE :
            - Toute conclusion doit être reliée à une règle déclenchée
              ET, le cas échéant, à la documentation fournie (RAG).
            """;


    public void buildPrompt(String scenarioNominal, PlcAnomaly a) {

        boolean severe = isSeverePostMortem(a);

        String systemPrompt = severe
                ? SYSTEM_PROMPT_SEVERE
                : SYSTEM_PROMPT_STANDARD;

        String userPrompt = String.format("""
                        OBJECTIF :
                        Produire un rapport technique détaillé sur UNE anomalie de production,
                        par comparaison stricte entre le scénario nominal officiel et les données réelles observées.
                        
                        ===============================
                        SCÉNARIO NOMINAL OFFICIEL
                        ===============================
                        %s
                        
                        ===============================
                        CONTEXTE OPÉRATIONNEL
                        ===============================
                        Pièce concernée : %s
                        Machine : %s
                        Step concerné : %s - %s
                        Cycle : %d
                        
                        Durée cycle machine mesurée : %s
                        Dépassement de durée constaté : %s
                        
                        ===============================
                        RÈGLES DE DÉTECTION DÉCLENCHÉES
                        ===============================
                        %s
                        
                        ===============================
                        INDICATEURS DE RÉCURRENCE ET DE RISQUE
                        ===============================
                        Nombre d’événements similaires observés : %d
                        EWMA ratio : %.2f
                        Rate ratio : %.2f
                        Hawkes score : %d
                        Niveau de confiance statistique : %s
                        Niveau de sévérité calculé : %s
                        
                        ===============================
                        FORMAT STRICT DU RAPPORT
                        ===============================
                        Machine :
                        Step concerné :
                        
                        Comportement nominal attendu :
                        Décrire précisément ce qui aurait dû se produire à ce step,
                        dans l’ordre nominal du workflow et dans les temps nominaux.
                        
                        Comportement réel observé :
                        Décrire factuellement ce qui s’est réellement produit,
                        en t’appuyant EXCLUSIVEMENT sur les règles déclenchées et leurs observations.
                        
                        Analyse NOMINAL vs RÉEL :
                        Comparer point par point le comportement attendu et le comportement observé.
                        Qualifier précisément la divergence (surdurée, déphasage, saut de step, etc.)
                        et justifier chaque élément par une règle déclenchée.
                        
                        Impact sur la production :
                        Analyser l’impact opérationnel déductible (temps de cycle, désynchronisation,
                        rebouclage, blocage, perte de cadence).
                        Si non déductible : indiquer explicitement que l’impact n’est pas évaluable.
                        
                        Causes techniques probables :
                        Formuler UNIQUEMENT des scénarios techniques compatibles avec les règles déclenchées.
                        Aucune cause ne doit être mentionnée sans lien explicite avec une règle.
                        
                        Actions terrain prioritaires :
                        Lister des vérifications ou actions directement liées aux règles déclenchées
                        (capteurs, séquence PLC, interverrouillages, synchronisation).
                        
                        Niveau de criticité :
                        Justifier le niveau de criticité à partir de la sévérité, de la récurrence
                        et du niveau de confiance statistique.
                        
                        """,
                scenarioNominal,
                a.getPart().getExternalPartId(),
                a.getMachine().getCode() + ", " + a.getMachine().getName() + ", description : " + a.getMachine().getDescription(),
                a.getProductionStep().getStepCode(),
                a.getProductionStep().getName() + ", description : " + a.getProductionStep().getDescription(),
                a.getCycle(),
                a.getCycleDurationS() == null ? "N/A" : String.format("%.2f s", a.getCycleDurationS()),
                a.getDurationOverrunS() == null ? "N/A" : String.format("%.2f s", a.getDurationOverrunS()),
                formatRuleReasons(a.getRuleReasons()),
                a.getEventsCount(),
                a.getEwmaRatio(),
                a.getRateRatio(),
                a.getHawkesScore(),
                a.getConfidence(),
                a.getSeverity()
        );


        System.out.println("################## LLM ANOMALY ##################");

        String report_path = sendPost(systemPrompt, userPrompt, a);
        System.out.println("report_path :" + report_path);
        a.setReportPath(report_path);
        plcAnomalyRepository.save(a);
        // push anomalie socket

        anomalyWebSocketHandler.emitAnomalieCompleted();
    }


    public record AnomalyRequest(
            String systemPrompt,
            String userPrompt,
            AnomalyToPromptDto anomaly
    ) {
    }


    public String sendPost(String systemPrompt, String userPrompt, PlcAnomaly anomaly) {
        try {
            String url = AppConfig.getUrl("/ia_api/anomaly");
            AnomalyToPromptDto dto = PlcAnomalyMapper.toDto(anomaly);
            AnomalyRequest request = new AnomalyRequest(systemPrompt, userPrompt, dto);

            return restTemplate.postForObject(url, request, String.class);
        } catch (Exception e) {
            log.error("LLM doesn't response :", e);
        }
        return null;
    }


}