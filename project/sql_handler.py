
from datetime import date, datetime
from decimal import Decimal
import uuid
import psycopg2
import torch
from config import Config
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import base64
import history_handler
import  web_search_handler
import re
from playwright.async_api import async_playwright
import generate_display_html
import json

'''
spring.datasource.url=jdbc:postgresql://localhost:5432/wacdo
spring.datasource.username=postgres
spring.datasource.password=root
spring.datasource.driver-class-name=org.postgresql.Driver

'''
class Database:

    def __init__(self):
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = psycopg2.connect(
                host="localhost",
                port=  5432,
                dbname="wacdo",
                user="postgres",
                password="root"
            )

    def query(self, sql, params=None, fetch=True):
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)

                if fetch:
                    rows = cur.fetchall()
                    colnames = [desc[0] for desc in cur.description]

                    # Transforme list[tuple] → list[dict]
                    content = []
                    for row in rows:
                        row_dict = {}
                        for key, value in zip(colnames, row):
                            row_dict[key] = self.json_safe(value)
                        content.append(row_dict)

                    # Retourne le JSON structuré
                    result = {
                        "header": colnames,
                        "content": content
                    }

                    return result

                self.conn.commit()
                self.close()

        except Exception as e:
            print("Erreur SQL:", e)
            self.conn.rollback()
            raise
        
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def json_safe(self,value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, bytes):
            return base64.b64encode(value).decode()
        return value                   
            
            
    def prompt_sql_query(self, user_ip, query, model, tokenizer):
        
        # Formater l'historique en texte
                    
        schema_file = "./RAG/sql/schema_complet.sql"
        with open(schema_file, "r", encoding="utf-8", errors="ignore") as f:
            schema_text = f.read()
        
        prompt = f"""
        Tu es un générateur expert de requêtes SQL SELECT pour PostgreSQL.
        Voici le schéma de la base de données : 
        {schema_text}

        Génère **une seule et unique requête SQL SELECT valide** correspondant exactement à cette demande :
        {query}

        ⚠️ Assure toi de limité le resultat au 20 premier resultat, ne renvoie **aucune explication**, aucun commentaire, aucune répétition, aucune mise en forme Markdown. 
        Seul le code SQL doit être retourné, en une seule et unique requête au format PostgreSQL, prêt à être exécuté.
        Assure-toi qu'il n'y ait qu'un seul point-virgule à la fin.
        Seul le code SQL doit être retourné en une seule et unique requête SQL SELECT valide**.
        """
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        def run_generation():
            with torch.no_grad():
                return model.generate(
                    **inputs,
                    max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                    do_sample=False                )

        with ThreadPoolExecutor() as executor:
            future = executor.submit(run_generation)
            try:
                output = future.result(timeout=Config.SERVER_TIMEOUT)  # timeout
                # Décoder les tokens générés
                decoded_text = tokenizer.decode(output[0], skip_special_tokens=True)

                # On retire le prompt complet pour ne garder que la requête SQL
                sql_query = decoded_text[len(prompt):].strip()
                # Nettoyer les lignes qui commencent par '#' et les lignes vides
                match = re.search(r"\bSELECT\b.*?;", sql_query, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    sql_query_clean = match.group(0).strip()
                    print("### Clean SQL:", sql_query_clean)                    
                    # Exécuter la requête
                    sql_data = json.dumps(self.query(sql_query_clean), indent=2, ensure_ascii=False)    
                    print(f"### Generated DB DATA : {len(sql_data)} characters")
                    return sql_data
                     # Générer le HTML d'affichage
                    '''
                    html_template = generate_display_html.prompt_on_sql_data("none", query, sql_data, schema_text, model, tokenizer)
                    html_template = html_template.replace("```", "")
                    print("### Generated HTML:", html_template)
                    return html_template
                    '''
                
                else:
                    print("⚠️ Aucun SELECT trouvé dans la sortie.")
            except TimeoutError:
                return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"   
                 
                
