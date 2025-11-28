import torch
import io
from config import Config
import faiss_handler
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import base64
from playwright.async_api import async_playwright

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
        prompt_query(prompt,model,tokenizer)
        
def timeout(signum, frame):
    raise TimeoutError("Temps d'exécution dépassé")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(100)  # 100 secondes

        
def load_image_model():
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl",use_fast=True)
    vision_model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl") #"./models/models--Salesforce--blip2-flan-t5-xl/snapshots/0eb0d3b46c14c1f8c7680bca2693baafdb90bb28")
    return processor , vision_model
       
def prompt_image(image64,model,tokenizer):
    processor , vision_model = load_image_model()
    image_bytes = base64.b64decode(image64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    inputs = processor(images=image, return_tensors="pt")
    generated_ids = vision_model.generate(**inputs)
    image_description = processor.decode(generated_ids[0], skip_special_tokens=True)
    
    query = f"Analyse cette image : {image_description}. réponse en français"
    return faiss_search(query, model, tokenizer)
    
def faiss_search(query, model, tokenizer):
    """
    Recherche dans FAISS, si résultats pertinents → utilise contexte.
    Sinon → fallback vers modèle brut sans contexte.
    """

    # Récupération des chunks pertinents
    retrieved = faiss_handler.retrieve(
        query,
        top_k=2,  # ajustable
    )

    if not retrieved:
        print("⚠️ Aucun chunk pertinent (score < threshold). Fallback vers LLM brut.")
        return prompt_query(query, model, tokenizer)

    # Construire le contexte
    context = "\n\n".join([
        f"Texte: {r['text'][:Config.CHUNK_SIZE]}...\n"
        f"Chemin: {r['metadata'].get('path','inconnu')}\n"
        f"Source: {r['metadata'].get('source','inconnu')}\n"
        f"Page: {r['metadata'].get('page','?')}\n"
        f"Score: {round(r.get('score', 0), 3)}"
        for r in retrieved[:2]
    ])

    # Prompt final
    prompt = f"""
    Tu es un assistant français RAG. Tu dois répondre uniquement à partir du contexte fourni.
    Ne répète jamais le texte original, synthétise uniquement l'information utile.
    Réponse courte et précise, maximum {Config.MAX_OUTPUT_TOKEN} tokens.
    Contexte :
    {context}

    Question : 
    {query}
    """.strip()
    return prompt_query(prompt, model, tokenizer, with_context=True)




def prompt_query(prompt, model, tokenizer,with_context=False):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    if with_context == False:
        prompt = f"""
        Tu es un assistant intelligent en français.
        Réponse courte, claire et précise, en maximum {Config.MAX_OUTPUT_TOKEN} tokens.
        
        Question:
        {prompt}
        """
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                do_sample=True,
                top_p=Config.TOP_P,      # <-- warning
                top_k=Config.TOP_K,      # <-- warning
                temperature=Config.TEMPERATURE
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=200)  # timeout de 100 sec
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print(f"\nPrompt: {prompt}\nResponse: {decoded}")
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return "⏱️ La génération a dépassé le délai imparti (200 sec)"