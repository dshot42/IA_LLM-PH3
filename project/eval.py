import torch
from config import Config
import faiss_handler

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
       

def prompt_query(prompt,model,tokenizer):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=Config.MAX_OUTPUT_TOKEN,
            do_sample=True,
            top_p=Config.TOP_P,
            temperature=Config.TEMPERATURE
        )
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    print(f"\nPrompt: {prompt}\nResponse: {decoded}")
    return decoded

def faiss_search(query,model,tokenizer):
        
        all_chunks, metadata, embedder, index = faiss_handler.load_faiss_index(all_chunks, metadata);       
        
        if embedder and index and all_chunks:
            retrieved = faiss_handler.retrieve(query, embedder, index, all_chunks, metadata)

            # Construire le contexte
            context = "\n\n".join([
                f"{r['text']} (source: {r['metadata']['source']}, page: {r['metadata']['page']})"
                for r in retrieved
            ])

            # Passer au prompter
            response_text = eval.prompt_query(context, model, tokenizer)
            print(response_text)
        else:
            print("⚠️ Aucun index disponible, impossible de faire la recherche.")