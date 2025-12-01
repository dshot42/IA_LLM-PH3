from sentence_transformers import SentenceTransformer, util
from config import Config
import eval
import faiss_handler
import requests
import torch
from sentence_transformers import SentenceTransformer, util
from urllib.parse import quote

def searchWeb(query, min_score=0.3):
    # TF-IDF boost
    embedder = SentenceTransformer(Config.RAG_MODEL)
    tf_prompt, query_vec = faiss_handler.apply_tfidf_sort(query, embedder)
    safe_prompt = quote(tf_prompt)
    
    # API Wikipédia
    url = f"https://fr.wikipedia.org/w/api.php?action=query&prop=extracts&format=json&exintro=&titles={safe_prompt}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Aucun résultat Wikipédia pour '{tf_prompt}'")
        return []

    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    results = []
    for page_id, page_data in pages.items():
        snippet = page_data.get("extract", "")
        title = page_data.get("title", "")
        page_url = f"https://fr.wikipedia.org/wiki/{quote(title)}"

        # Embeddings et score
        snippet_emb = embedder.encode(snippet, convert_to_tensor=True)
        query_emb = torch.tensor(query_vec, dtype=snippet_emb.dtype)
        score = util.cos_sim(query_emb, snippet_emb).item()

        if score >= min_score:
            results.append({
                "title": title,
                "url": page_url,
                "snippet": snippet,
                "score": score
            })
            print(f"Score: {score:.4f} | Title: {title}")
            print(f"URL: {page_url}")
            print(f"Snippet: {snippet[:500]}...\n")

    return results

