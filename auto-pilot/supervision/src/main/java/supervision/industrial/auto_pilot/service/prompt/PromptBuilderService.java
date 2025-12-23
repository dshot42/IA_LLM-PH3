package supervision.industrial.auto_pilot.service.prompt;

import org.springframework.stereotype.Service;
import supervision.industrial.auto_pilot.model.PlcAnomaly;

@Service
public class PromptBuilderService {

    public String buildPrompt(String scenarioNominal, PlcAnomaly a) {

        return String.format("""
                        [INST]
                        RÔLE : Ingénieur process industrielle senior (PLC / Grafcet).
                        
                        OBJECTIF :
                        Analyser une anomalie de production par comparaison STRICTE
                        au scénario nominal officiel.
                        
                        PRINCIPE :
                        Le scénario nominal est la référence absolue.
                        Toute conclusion doit être fondée sur les données disponibles.
                        
                        SCÉNARIO NOMINAL :
                        %s
                        
                        DONNÉES RÉELLES OBSERVÉES :
                        Machine = %s
                        Cycle = %d
                        Durée cycle machine mesurée = %.2f s
                        Dépassement de durée constaté = %.2f s
                        Règle de détection déclenchée = %s
                        Niveau de sévérité = %s
                        
                        FORMAT STRICT DU RAPPORT :
                        Machine :
                        Step concerné :
                        Comportement nominal attendu :
                        Comportement réel observé :
                        Analyse NOMINAL vs RÉEL :
                        Impact sur la production :
                        Causes techniques probables :
                        Actions terrain prioritaires :
                        Niveau de criticité :
                        FAIBLE / MODÉRÉ / ÉLEVÉ / CRITIQUE
                        
                        FIN_RAPPORT
                        [/INST]
                        """,
                scenarioNominal,
                a.getMachine(),
                a.getCycle(),
                a.getCycleDurationS(),
                a.getDurationOverrunS(),
                a.getRuleReasons(),
                a.getSeverity()
        );
    }

}