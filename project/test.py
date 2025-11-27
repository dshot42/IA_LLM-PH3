import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import faiss_handler

# 🔹 Charger le modèle (Phi-2 mini, CPU)
model_name = "./models/Phi-3-mini-128k-instruct"  # ou ton modèle Phi-2 mini
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
# 🔹 Prompt simple
query = "donne moi le n° france travail de monsieur dubost en une réponse simple"


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

# 🔹 Tokenizer
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
print("Tokens input shape:", inputs['input_ids'].shape)

# 🔹 Génération
with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=50,
        do_sample=True,
        top_p=0.9,
        temperature=0.7
    )

# 🔹 Décodage
decoded = tokenizer.decode(output[0], skip_special_tokens=True)
print("Réponse du modèle :"+decoded )