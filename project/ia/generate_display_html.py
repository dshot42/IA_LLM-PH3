

import torch
from config import Config
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import re

def prompt_on_sql_data(user_ip, initial_user_query, sql_data, schema_sql, model, tokenizer):
    
    prompt = f"""
    Tu es un générateur expert de code front-end HTML/CSS/JS.

    Tu vas recevoir :
    1) Un jeu de données provenant d'une requête SQL, au format JSON (tableau d'objets),
    2) Le modèle de données (schema_sql),
    3) La demande initiale de l'utilisateur.

    Ta tâche :
    - Générer un fichier HTML + JavaScript COMPLET, self-contained, aucun CDN,
    - Inclure toutes les données SQL dans une variable `const data = [...]` en JS,
    - Générer automatiquement un tableau HTML ou un diagramme basé sur toutes les colonnes et toutes les lignes du JSON,
    - Déduire automatiquement les en-têtes de colonnes à partir des clés du JSON,
    - La page doit être directement fonctionnelle en ouvrant le fichier dans un navigateur,
    - La page doit être esthétique et facile à lire,
    - Ne rien inventer : utiliser uniquement les colonnes et valeurs fournies dans le JSON.

    Contraintes :
    - Tous les objets du JSON doivent apparaître intégralement dans le rendu final,
    - Le code ne doit contenir aucune explication, uniquement le code final HTML + JS,
    - Le code doit fonctionner quelle que soit la taille du tableau.

    Voici les données SQL JSON :
    {sql_data}

    Voici le modèle de données :
    {schema_sql}

    Demande initiale de l'utilisateur :
    {initial_user_query}
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=3000, # besoin de verbillage ici pour mon script et son esthetique // reprendre avec chunk et streaming 
                do_sample=False
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=Config.SERVER_TIMEOUT)  # timeout
            # Décoder les tokens générés
            decoded_text = tokenizer.decode(output[0], skip_special_tokens=True)

            match = re.search(r"(<html.*</html>)", decoded_text, flags=re.DOTALL | re.IGNORECASE)
            if match:
                html_template = match.group(1)
            else:
                html_template = decoded_text
                
            return html_template

        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"        