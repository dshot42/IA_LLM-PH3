import torch
import io
from config import Config
import faiss_handler
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import base64

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
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl")
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
    response_text = prompt_query(query, model, tokenizer)
    return response_text
    
      
def faiss_search(query, model, tokenizer, threshold=0.7):
    """
    Cherche dans FAISS, si résultat pertinent → utilise contexte.
    Sinon → fallback sans contexte.
    """
    all_chunks, metadata, embedder, index = faiss_handler.load_faiss_index()

    if embedder and index and all_chunks:
        retrieved = faiss_handler.retrieve(query, embedder, index, all_chunks, metadata)

        # Si aucun résultat ou score trop faible → fallback
        if not retrieved or retrieved[0].get("score", 1.0) > threshold:
            print("⚠️ Pas de contexte pertinent, fallback vers modèle brut.")
            return prompt_query(query, model, tokenizer)

        # Construire le contexte
        context = "\n\n".join([
            f"Texte: {r['text'][:Config.CHUNK_SIZE]}...\nChemin: {r['metadata'].get('path','inconnu')}\nSource: {r['metadata'].get('source','inconnu')}\nPage: {r['metadata'].get('page','?')}"
            for r in retrieved[:10]
        ])

        prompt = f"""
        Tu es un assistant qui répond aux questions en analysant le contexte.
        Lis attentivement les archives et donne une réponse courte et claire.

        Contexte:
        {context}

        Question:
        {query}
        
        Réponse courte :
        """
        return prompt_query(prompt, model, tokenizer)

    else:
        print("⚠️ Aucun index disponible, fallback direct.")
        return prompt_query(query, model, tokenizer)


def prompt_query(prompt, model, tokenizer):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=Config.MAX_OUTPUT_TOKEN,
                do_sample=True,
                top_p=Config.TOP_P,
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