from duckduckgo_search import DDGS
from sentence_transformers import SentenceTransformer, util
import torch
import re
from config import Config
import ia.faiss_handler


def clean_text(t: str) -> str:
    """Nettoie et compresse le texte pour un meilleur scoring."""
    if not t:
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    return t


def searchWeb(query, top_k=5, min_score=0.30, max_results=5):
    """
    Recherche Web optimisée :
    - DDG text search (gratuit)
    - Nettoyage snippet
    - Cosine similarity + densité d’information
    - TF-IDF boost automatique
    """

    embedder = SentenceTransformer(Config.RAG_MODEL)
    tf_prompt, query_vec = faiss_handler.apply_tfidf_sort(query, embedder)

    collected = []

    with DDGS() as ddgs:
        ddg_results = ddgs.text(query, max_results=top_k)

        for r in ddg_results:
            title = clean_text(r.get("title", ""))
            snippet = clean_text(r.get("body", ""))
            url = r.get("href", "")

            if len(snippet) < 25:   # trop court = non utile
                continue

            # Embedding snippet
            sn_emb = embedder.encode(snippet, convert_to_tensor=True)
            cos_score = util.cos_sim(query_vec, sn_emb).item()

            # Score densité d'information (pénalise les snippets trop vagues)
            density = min(len(snippet) / 300, 1.0)

            # Score final pondéré
            final_score = (cos_score * 0.7) + (density * 0.3)

            if final_score >= min_score:
                collected.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "score": final_score,
                    "cosine": cos_score,
                    "density": density,
                })

    # Tri final
    collected.sort(key=lambda x: x["score"], reverse=True)

    # Retirer les doublons de domaine ou titres
    seen_titles = set()
    filtered = []
    for r in collected:
        if r["title"] in seen_titles:
            continue
        seen_titles.add(r["title"])
        filtered.append(r)
        if len(filtered) >= max_results:
            break

    return filtered
