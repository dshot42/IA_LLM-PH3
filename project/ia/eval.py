import torch
import io
from config import Config
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import base64
import ia.history_handler
import ia.web_search_handler
from ia.faiss.faiss_handler import retrieve
from ia.history_handler import filter_relevant_history,add_user_query
from ia.web_search_handler import searchWeb

def evaluate_model(model, tokenizer):
    prompts = [
        "Write a short poem about the sea.",
        "Give me a recipe for chocolate cake.",
        "Explain the theory of relativity in simple terms.",
        "quel est l'état de la Machine ABC003 avec vibration 0.95",
        "donne moi la liste des Machine avec vibration 0.95",
        "liste moi les fichiers dans le dossier :  C:/Users/come_/Desktop/ia-llm/phi3/project/ "
    ]

    print("\n --- Running Evaluation:")
    for prompt in prompts:
        prompt_query("none",prompt,model,tokenizer)
        
def timeout(signum, frame):
    raise TimeoutError("Temps d'exécution dépassé")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(100)  # 100 secondes

        
def load_image_model():
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl",use_fast=True)
    vision_model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl") #"./models/models--Salesforce--blip2-flan-t5-xl/snapshots/0eb0d3b46c14c1f8c7680bca2693baafdb90bb28")
    return processor , vision_model
       
def prompt_image(user_ip, image64,model,tokenizer):
    processor , vision_model = load_image_model()
    image_bytes = base64.b64decode(image64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    inputs = processor(images=image, return_tensors="pt")
    generated_ids = vision_model.generate(**inputs)
    image_description = processor.decode(generated_ids[0], skip_special_tokens=True)
    
    query = f"Analyse cette image : {image_description}. réponse en français"
    return faiss_search(user_ip, query, model, tokenizer)
    
def faiss_search(user_ip, query, model, tokenizer):
    """
    Recherche dans FAISS, si résultats pertinents → utilise contexte.
    Sinon → fallback vers modèle brut sans contexte.
    """

    # Récupération des chunks pertinents
    retrieved = retrieve(
        user_ip,
        query
    )

    if not retrieved:
        print("⚠️ Aucun chunk pertinent (score < threshold). Fallback vers LLM brut.")
        return prompt_query(user_ip, query, model, tokenizer)

    # Construire le contexte
    context = "\n\n".join([
        f"Texte: {r['text']}...\n"
        f"Chemin: {r['metadata'].get('path','inconnu')}\n"
        f"Source: {r['metadata'].get('source','inconnu')}\n"
        f"Page: {r['metadata'].get('page','?')}\n"
        f"Score: {round(r.get('score', 0), 3)}"
        for r in retrieved
    ])

    # Prompt final
    prompt = f"""
    Tu es un assistant français RAG. Tu dois répondre UNIQUEMENT à partir du contexte ci-dessous.
    Aucune information extérieure ne doit être ajoutée.

    === Contexte ===
    {context}

    === Question ===
    {query}

    === Instructions ===
    - Répondre de manière directe, nette et concise.
    - Ne jamais répéter le contexte ou reformuler la question.
    - Ne pas expliquer ta démarche.
    - Ne pas ajouter de détails non présents dans le contexte.
    - Ne pas utiliser de Markdown.
    - Réponse strictement informative, sans redondance.
    - Ne produire qu’un seul paragraphe si possible.
    """

   
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device) # important 
   
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                do_sample=False,
                top_p=Config.TOP_P,   
                top_k=Config.TOP_K, 
                temperature=Config.TEMPERATURE,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=Config.SERVER_TIMEOUT)  # timeout
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print("### result : " +decoded[len(prompt):].strip())
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"
        

def prompt_query(user_ip, query, model, tokenizer):
    
    history = filter_relevant_history(user_ip, query)  # cherche dans l'historique si contexte pertiant au prompt

    add_user_query(user_ip,query)   
    
    # Formater l'historique en texte
                
    history_text = ""
    if history:
        history_text = "Historique des échanges :\n"
        for i, h in enumerate(history, 1):
            history_text += f"{i}. {h}\n"

    web_results = searchWeb(query)
    context_text = ""
    if web_results:
        context_text = "Contexte Web pertinent :\n"
        for i, r in enumerate(web_results, 1):
            context_text += f"{i}. {r['title']} | {r['url']}\n"
            if r.get('snippet'):
                context_text += f"   {r['snippet']}\n"

    prompt = f"""
    Tu es un assistant français. Réponds uniquement à partir de l'historique et du contexte web.
    Réponse obligatoire : courte, précise, claire, sans reformuler la question.

    Règles strictes :
    - Ne génère pas de questions.
    - Ne répète pas la question.
    - Ne répète pas le contexte web.
    - Ne mentionne pas l'historique.
    - Ne fournis aucune explication sur ta démarche.
    - Ne commente rien.
    - Pas de Markdown.
    - Réponse directe uniquement.

    {history_text if history_text else ""}

    {context_text if context_text else ""}

    Question :
    {query}
    """

    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device) # important 
   
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                do_sample=False,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3,
                top_p=Config.TOP_P,   
                top_k=Config.TOP_K, 
                temperature=Config.TEMPERATURE
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=Config.SERVER_TIMEOUT)  # timeout
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print("### result : " +decoded[len(prompt):].strip())
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"
        
        
def eval_prompt(prompt, model, tokenizer, user_ip="sytem_workflow"):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device) # important 
   
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                do_sample=False,
                top_p=Config.TOP_P,   
                top_k=Config.TOP_K, 
                temperature=Config.TEMPERATURE,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=2000)  # timeout
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print("### result : " +decoded[len(prompt):].strip())
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({2000} sec)"
