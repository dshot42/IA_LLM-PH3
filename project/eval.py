import torch
import io
from config import Config
import faiss_handler
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError


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
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-flan-t5-xl") # a telecharger localement et test img en upload
    vision_model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl")
    return processor , vision_model
       
def prompt_image(image64,model,tokenizer):
    processor , vision_model = load_image_model()
    #image = Image.open(image).convert("RGB")
    image = Image.open(io.BytesIO(image64)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    generated_ids = vision_model.generate(**inputs)
    image_description = processor.decode(generated_ids[0], skip_special_tokens=True)
    query = f"Analyse cette image : {image_description}. Que peux-tu en déduire ?"
    response_text = eval.prompt_query(query, model, tokenizer)
    print(response_text)
    
    
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
            output = future.result(timeout=100)  # timeout de 100 sec
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print(f"\nPrompt: {prompt}\nResponse: {decoded}")
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return "⏱️ La génération a dépassé le délai imparti (100 sec)"

      
def faiss_search(query,model,tokenizer):
    
    all_chunks, metadata, embedder, index = faiss_handler.load_faiss_index()

    if embedder and index and all_chunks:
        retrieved = faiss_handler.retrieve(query, embedder, index, all_chunks, metadata)

        context = "\n\n".join([
            f"Texte: {r['text'][:1000]}...\nChemin: {r['metadata'].get('path','inconnu')}\nSource: {r['metadata'].get('source','inconnu')}\nPage: {r['metadata'].get('page','?')}"
            for r in retrieved[:5] 
        ])

        prompt = f"""
            Tu es un assistant qui répond aux questions en analysant le contexte, reponse simple
            Contexte:
            {context}

            Question:
            {query}
            """
        
        # Passer au prompter
        response_text = prompt_query(prompt, model, tokenizer)
        return response_text
    else:
        print("⚠️ Aucun index disponible, impossible de faire la recherche.")