package supervision.industrial.auto_pilot.workflow.prompt;

import dependancy_bundle.model.TRSRepport;
import dependancy_bundle.repository.TRSRepportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import supervision.industrial.auto_pilot.MainConfig;
import supervision.industrial.auto_pilot.api.config.AppConfig;
import supervision.industrial.auto_pilot.api.service.ProductionService;
import supervision.industrial.auto_pilot.workflow.trs.TRSMainHandler;

import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TRSPromptHandler {

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private final TRSMainHandler trsMainHandler;
    @Autowired
    private final ProductionService productionService;

    @Autowired
    private final TRSRepportRepository trsRepportRepository;


    public record TrsImpactLine(

            String machineCode,
            String stepCode,

            long occurrences,

            double totalOverrunS,
            double impactPercentTRS,

            // 🧠 CAUSALITÉ EXPLICITE
            String dominantRule,
            long dominantRuleOccurrences,
            double dominantRuleOverrunS,
            double dominantRuleImpactPercentTRS,

            // ⚠️ RISQUE
            double dangerScore,
            String dangerExplanation,

            boolean reinforcing
    ) {
    }


    private List<TrsImpactLine> computeImpact(
            ProductionService.TrsResponse trs,
            List<TRSMainHandler.StepAnomalyAggregate> aggs
    ) {

        double totalTime = trs.totalRealTimeS();
        if (totalTime <= 0) return List.of();

        return aggs.stream()
                .filter(a -> a.totalDurationOverrunS() > 0)
                .sorted(Comparator
                        .comparingDouble(TRSMainHandler.StepAnomalyAggregate::totalDurationOverrunS)
                        .reversed()
                )
                .limit(6)
                .map(a -> {

                    String dominantRule = a.dominantRule();
                    long dominantCount = a.dominantRuleOccurrences();

                    double dominantOverrun =
                            a.overrunDurationByRule().getOrDefault(dominantRule, 0.0);

                    double dominantImpactTRS =
                            round2((dominantOverrun / totalTime) * 100.0);

                    double totalImpactTRS =
                            round2((a.totalDurationOverrunS() / totalTime) * 100.0);

                    String dangerExplanation =
                            "Score calculé à partir de la sévérité moyenne, "
                                    + "des signaux statistiques (EWMA / Hawkes), "
                                    + "de la récurrence temporelle "
                                    + "et de la dominance de la règle "
                                    + dominantRule;

                    return new TrsImpactLine(
                            a.machineCode(),
                            a.stepCode(),
                            a.occurrences(),

                            a.totalDurationOverrunS(),
                            totalImpactTRS,

                            dominantRule,
                            dominantCount,
                            dominantOverrun,
                            dominantImpactTRS,

                            a.dangerScore(),
                            dangerExplanation,

                            a.isReinforcingOverTime()
                    );
                })
                .toList();
    }


    private double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }


    public void trsAnalyse(OffsetDateTime start, OffsetDateTime end) {

        ProductionService.TrsResponse trs =
                trsMainHandler.calculateTRBetween2Date(start, end);

        List<TRSMainHandler.StepAnomalyAggregate> aggregates =
                trsMainHandler.getWholeAnomalies(start, end);

        List<TrsImpactLine> impact =
                computeImpact(trs, aggregates);

        String trs_path = buildPrompt(trs, impact, start, end);
        if (trs_path != null) {
            TRSRepport trsRepport = new TRSRepport();
            trsRepport.setRepportPath(trs_path);
            trsRepportRepository.save(trsRepport);
        }

    }


    public String buildPrompt(
            ProductionService.TrsResponse trs,
            List<TrsImpactLine> impact,
            OffsetDateTime start,
            OffsetDateTime end
    ) {

        StringBuilder sb = new StringBuilder();

        sb.append("""
                TU ES UN INGÉNIEUR MÉTHODES INDUSTRIEL SENIOR.
                
                LANGUE : FRANÇAIS UNIQUEMENT.
                STYLE : TECHNIQUE, FACTUEL, CHIFFRÉ.
                INTERDICTIONS : hypothèses, conseils, généralités, texte non chiffré.
                
                PRINCIPE :
                Analyser une dégradation de TRS UNIQUEMENT à partir
                des dérives mesurées ci-dessous.
                
                DÉFINITIONS À RESPECTER STRICTEMENT :
                - Impact TRS (%) = part de perte de TRS causée par la dérive.
                - Cause dominante = anomalie responsable de la plus grande part de sur-durée.
                - Dérive STRUCTURELLE = récurrente + renforcée dans le temps.
                - Dérive PONCTUELLE = isolée ou non renforcée.
                - Score de danger (0–100) = criticité opérationnelle globale.
                """);

        sb.append(String.format("""
                        PÉRIODE : %s → %s
                        TRS global           : %.4f (Correspond à la performance * la qualité)
                        Production Performance          : %.4f (Correspond au rendement machine Réel/Nominal)
                        Qualité              : %.4f (Correspond a la production de pièce Bonne/Total)
                        Etape Bonne          : %d
                        Etape mauvaise       : %d
                        Temps réel total     : %.2f s
                        Temps nominal total  : %.2f s
                        
                        """,
                start, end,
                trs.trs(),
                trs.performance(),
                trs.quality(),
                trs.goodSteps(),
                trs.badSteps(),
                trs.totalRealTimeS(),
                trs.totalTheoreticalTimeS()

        ));

        sb.append("""
                DÉRIVES TRS OBSERVÉES (classées par impact décroissant)
                """);

        for (TrsImpactLine l : impact) {
            sb.append(String.format("""
                            ---
                            Machine / Step        : %s / %s
                            Occurrences           : %d
                            Sur-durée cumulée     : %.2f s
                            Impact TRS total      : %.2f %%
                            
                            Cause dominante       : %s
                            Occurrences associées : %d
                            Sur-durée associée    : %.2f s
                            Impact TRS associé    : %.2f %%
                            
                            Score de danger       : %.0f / 100
                            Nature de la dérive   : %s
                            """,
                    l.machineCode(),
                    l.stepCode(),
                    l.occurrences(),
                    l.totalOverrunS(),
                    l.impactPercentTRS(),

                    l.dominantRule(),
                    l.dominantRuleOccurrences(),
                    l.dominantRuleOverrunS(),
                    l.dominantRuleImpactPercentTRS(),

                    l.dangerScore(),
                    l.reinforcing() ? "STRUCTURELLE" : "PONCTUELLE"
            ));
        }

        sb.append("""
                ANALYSE ATTENDUE (FORMAT STRICT) :
                
                1. RÉCAPITULATIF TRS GLOBAL
                   - Rappeler TRS, performance, qualité, temps réel vs nominal.
                   - CHIFFRES UNIQUEMENT.
                
                2. ANALYSE DÉTAILLÉE DE CHAQUE DÉRIVE
                   Pour CHAQUE dérive :
                   - expliquer COMMENT la sur-durée dégrade le TRS
                   - quantifier son poids relatif
                   - justifier STRUCTURELLE ou PONCTUELLE uniquement par les chiffres
                
                3. CONSOLIDATION
                   - Identifier les 3 dérives les plus impactantes
                   - Calculer leur contribution cumulée exacte (% TRS)
                
                4. CONCLUSION
                   - 100 % factuel
                   - chiffres obligatoires
                """);


        return sendPost(
                sb,
                trs,
                impact,
                start,
                end
        );

    }


    public record TRSRequest(
            String prompt,
            ProductionService.TrsResponse trs,
            List<TrsImpactLine> impact,
            String start,
            String end
    ) {
    }


    public String sendPost(StringBuilder prompt, ProductionService.TrsResponse trs,
                           List<TrsImpactLine> impact,
                           OffsetDateTime start,
                           OffsetDateTime end) {
        try {
            if (!MainConfig.boowithLLM) return null;
            String url = AppConfig.getUrl("/ia_api/trs");

            TRSRequest request = new TRSRequest(prompt.toString(), trs, impact, start.toLocalDateTime().toString(), end.toLocalDateTime().toString());
            log.info("TRS -> Send PROMPT to LLM  ");

            String result = restTemplate.postForObject(url, request, String.class);
            log.info("[SUCCESS] TRS -> LLM response : {}", result);
            return result;

        } catch (Exception e) {
            log.error("[ERROR] TRS  LLM doesn't response !");
        }
        return null;
    }


}