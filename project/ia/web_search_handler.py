from duckduckgo_search import DDGS
from sentence_transformers import SentenceTransformer, util
import torch
import re
from config import Config
from ia.faiss.faiss_handler import apply_tfidf_sort


def clean_text(t: str) -> str:
    """Nettoie et compresse le texte pour un meilleur scoring."""
    if not t:
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    return t

from functools import lru_cache

@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer(Config.RAG_MODEL)


def searchWeb(query, top_k=5, min_score=0.30, max_results=5):

    embedder = get_embedder()
    tf_prompt, query_vec = apply_tfidf_sort(query, embedder)

    collected = []

    with DDGS() as ddgs:
        try:
            ddg_results = list(ddgs.text(query, max_results=top_k))
        except Exception as e:
            print("⚠️ DDG search failed:", e)
            return []

    for r in ddg_results:
        title = clean_text(r.get("title", ""))
        snippet = clean_text(r.get("body", ""))
        url = r.get("href", "")

        if len(snippet) < 25:
            continue

        try:
            sn_emb = embedder.encode(snippet, convert_to_tensor=True)
        except Exception:
            continue

        cos_score = util.cos_sim(query_vec, sn_emb).item()
        density = min(len(snippet) / 300, 1.0)
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

    collected.sort(key=lambda x: x["score"], reverse=True)

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

