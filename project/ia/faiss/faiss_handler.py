import os, pickle, re, json, numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize as sk_normalize
import faiss
from config import Config
from ia.history_handler import filter_relevant_history

# 🔹 Paramètres
INDEX_FILE = os.path.join(Config.INDEX_FAISS, "faiss_index.idx")
META_FILE = os.path.join(Config.INDEX_FAISS, "faiss_metadata.pkl")

INDEX_WORKFLOW_FILE = os.path.join(Config.INDEX_FAISS, "faiss_index_workflow.idx")
META_WORKFLOW_FILE = os.path.join(Config.INDEX_FAISS, "faiss_metadata_workflow.pkl")

DIM = 1024  # dimension forcée pour BGE

# ----------------- Préprocessing stopwords -----------------
def preprocess_stopwords():
    with open("./ressources/french_stopwords.json", "r", encoding="utf-8") as f:
        stopwords = json.load(f)
    clean = []
    for w in stopwords:
        tok = re.findall(r"[a-zA-Z0-9éèêàùôîç]+", w.lower())
        clean.extend(tok)
    return list(set(clean))

# ----------------- Projection embeddings -----------------
def project_to_1024(vec):
    """
    vec : np.array shape (n, 1024)
    retourne : np.array shape (n, 1024)
    """
    if vec.shape[1] == DIM:
        return vec.astype(np.float32)
    
    np.random.seed(42)  # pour reproductibilité
    proj = np.random.randn(vec.shape[1], DIM).astype(np.float32) / np.sqrt(vec.shape[1])
    return np.dot(vec, proj)

# ----------------- Index FAISS -----------------
def load_faiss_index(workflow: bool):
    if workflow:
        if not (os.path.exists(INDEX_WORKFLOW_FILE) and os.path.exists(META_WORKFLOW_FILE)):
            return None, None, None, None
        index = faiss.read_index(INDEX_WORKFLOW_FILE)
        meta_path = META_WORKFLOW_FILE
    else:
        if not (os.path.exists(INDEX_FILE) and os.path.exists(META_FILE)):
            return None, None, None, None
        index = faiss.read_index(INDEX_FILE)
        meta_path = META_FILE

    with open(meta_path, "rb") as f:
        data = pickle.load(f)

    chunks = data["chunks"]
    metadata = data["metadata"]

    embedder = SentenceTransformer(Config.RAG_MODEL)

    # 🔥 Sécurité dimension
    test_emb = embedder.encode(
        ["__faiss_dim_check__"],
        normalize_embeddings=True
    )

    test_emb = np.atleast_2d(test_emb)

    if test_emb.shape[1] != index.d:
        raise RuntimeError(
            f"Incompatible FAISS index dimension:\n"
            f"FAISS index.d = {index.d}\n"
            f"Embedding dim = {test_emb.shape[1]}\n"
            f"Model = {Config.RAG_MODEL}"
        )

    print(f"✅ FAISS index chargé ({index.ntotal} vecteurs, dim={index.d})")

    return chunks, metadata, embedder, index


def save_faiss_index(index, chunks, metadata, workflow: bool = False):
    """
    Sauvegarde :
    - index FAISS (.idx)
    - chunks + metadata (.pkl)
    """

    if workflow:
        index_path = INDEX_WORKFLOW_FILE
        meta_path = META_WORKFLOW_FILE
    else:
        index_path = INDEX_FILE
        meta_path = META_FILE

    os.makedirs(os.path.dirname(index_path), exist_ok=True)

    # --- Sauvegarde FAISS ---
    faiss.write_index(index, index_path)

    # --- Sauvegarde metadata ---
    with open(meta_path, "wb") as f:
        pickle.dump(
            {
                "chunks": chunks,
                "metadata": metadata
            },
            f
        )

    print(
        f"💾 FAISS index sauvegardé :\n"
        f"   - {index_path}\n"
        f"   - {meta_path}\n"
        f"   - vectors = {index.ntotal}, dim = {index.d}"
    )


def build_faiss_index(chunks, metadata,workflow):
    if not chunks:
        return [], [], None, None

    embedder = SentenceTransformer(Config.RAG_MODEL)
    embeddings = embedder.encode(chunks, convert_to_numpy=True).astype("float32")

    # Projection sur 1024
    embeddings = project_to_1024(embeddings)
    embeddings = sk_normalize(embeddings, axis=1)

    index = faiss.IndexFlatIP(DIM)
    index.add(embeddings)
    save_faiss_index(index, chunks, metadata,workflow)

    return chunks, metadata, embedder, index

def faiss_index_handler(new_chunks, new_metadata, workflow:bool):
    chunks, metadata, embedder, index = load_faiss_index(workflow)
    if not chunks:
        return build_faiss_index(new_chunks, new_metadata,workflow)
    
    existing_files = [m.get("path") for m in metadata]
    new_entries = [(c, m) for c, m in zip(new_chunks, new_metadata) if m.get("path") not in existing_files]
    
    if not new_entries:
        return chunks, metadata, embedder, index

    chunks_to_add, metadata_to_add = zip(*new_entries)
    embeddings_to_add = embedder.encode(list(chunks_to_add), convert_to_numpy=True).astype("float32")

    # Projection sur 1024
    embeddings_to_add = project_to_1024(embeddings_to_add)
    embeddings_to_add = sk_normalize(embeddings_to_add, axis=1)

    index.add(embeddings_to_add)
    chunks.extend(chunks_to_add)
    metadata.extend(metadata_to_add)
    save_faiss_index(index, chunks, metadata,workflow)
    return chunks, metadata, embedder, index

# ----------------- TF-IDF boost -----------------
def apply_tfidf_sort(
        query,
        embedder,
        stopword_factor=0.05,
        length_factor=0.12,
        pos_factor=0.08,
        rare_factor=0.2,
        mix_query=0.30,
        mode="sum"
    ):
    """
    PONDÉRATION SANS CORPUS :
    - importance = combinaison longueur + rareté + position + non-stopword
    - self-contained, stable, aucune dépendance extérieure
    - excellent pour moteurs RAG web
    """

    import numpy as np
    import re

    # -----------------------------
    # 1) Tokenisation
    # -----------------------------
    tokens = re.findall(r"[a-zA-Z0-9éàèùçêôî]+", query.lower())
    if not tokens:
        emb = embedder.encode([query], convert_to_numpy=True)[0]
        return query, emb

    stopwords = set(preprocess_stopwords())

    # -----------------------------
    # 2) Embeddings batch
    # -----------------------------
    token_emb = embedder.encode(tokens, convert_to_numpy=True)

    # -----------------------------
    # 3) Pondération SELF-IDF
    # -----------------------------
    weights = []
    total_tokens = len(tokens)

    for idx, tok in enumerate(tokens):

        # stopword → faible importance
        if tok in stopwords:
            w = stopword_factor

        else:
            # Longueur du mot → plus il est long, plus il est technique
            w_len = length_factor * (len(tok) / 8)

            # Rare = longueur + caractères rares
            w_rare = rare_factor * sum(1 for c in tok if c not in "aeiounrt")

            # Position : les premiers mots sont souvent les plus importants
            w_pos = pos_factor * (1 - idx / total_tokens)

            w = w_len + w_rare + w_pos + 0.1  # offset minimum

        weights.append(w)

    weights = np.array(weights)

    # Normalisation softmax → stabilité
    weights = np.exp(weights) / np.sum(np.exp(weights))

    # -----------------------------
    # 4) Vecteur pondéré
    # -----------------------------
    weighted = token_emb * weights[:, None]

    if mode == "sum":
        vec = weighted.sum(axis=0)
    else:
        vec = weighted.mean(axis=0)

    vec = vec / (np.linalg.norm(vec) + 1e-8)

    # -----------------------------
    # 5) Blending avec embedding brut
    # -----------------------------
    orig = embedder.encode([query], convert_to_numpy=True)[0]
    orig = orig / (np.linalg.norm(orig) + 1e-8)

    vec = (1 - mix_query) * vec + mix_query * orig
    vec = vec / (np.linalg.norm(vec) + 1e-8)

    return " ".join(tokens), vec


# ----------------- Boost metadata -----------------
def augment_query_with_metadata(query_vec: np.ndarray, query: str, metadata_list: list, embedder):
    # Extraire les mots du query
    tokens = re.findall(r"[a-zA-Z0-9éèêàùôîç]+", query.lower())

    # Charger stopwords
    stopwords = set(preprocess_stopwords())

    matched_vecs = []

    for meta in metadata_list:
        source = meta.get("source", "")
        if not isinstance(source, str):
            continue

        source_low = source.lower()

        # For each word in query (not in stopwords)
        for tok in tokens:
            if tok in stopwords:
                continue

            # search word inside metadata source
            if re.search(re.escape(tok), source_low):
                #print(f"[BOOST] '{tok}' found in metadata source '{source_low}'")
                m_vec = embedder.encode([tok], convert_to_numpy=True)
                matched_vecs.append(m_vec)

    # Si des mots matchent → booster
    if matched_vecs:
        matched_vecs = np.vstack(matched_vecs)
        boosted = np.mean(np.vstack([query_vec, matched_vecs]), axis=0, keepdims=True)
        return boosted

    print("Metadata not matched in query.")
    return query_vec


# ----------------- Ultra ReRanking -----------------
def ultra_reranker_scores(sims, eps=1e-9):
    sims = np.array(sims, dtype=float)
    similarities = np.clip(sims, 0, 1)
    top_sim = np.max(similarities)
    contrasts = top_sim - similarities
    alpha = 50
    boosts = 1 / (1 + np.exp(-alpha * (contrasts - 0.05)))
    raw_scores = 0.6 * similarities + 0.4 * boosts
    final_scores = (1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + eps)) * sims # * sims important
    return final_scores, similarities, contrasts, boosts

# ----------------- Retrieval -----------------


from rank_bm25 import BM25Okapi
import re
import numpy as np
from sklearn.preprocessing import normalize as sk_normalize

def retrieve(user_ip: str, query: str, top_k: int = Config.nb_chunks_to_use, query_weight: float = 1):
    print("--- FAISS →  filtrage fin with BM25 rerank ---")
    chunks, metadata, embedder, index = load_faiss_index(False)
    if not embedder or not chunks or not index:
        return []

    # ---------------- TF-IDF boost pour query
    tf_prompt, query_vec = apply_tfidf_sort(query, embedder)

    # ---------------- Fusion avec historique
    filtered_history = filter_relevant_history(user_ip, query)
    if filtered_history:
        hist_vecs = sk_normalize(embedder.encode(filtered_history, convert_to_numpy=True), axis=1)
        hist_mean = np.mean(hist_vecs, axis=0, keepdims=True)
        hist_w = min(0.5, len(filtered_history)/10)
        query_vec = sk_normalize(query_weight * query_vec + (1 - hist_w) * hist_mean, axis=1)

    # ---------------- Metadata boost
    query_vec = augment_query_with_metadata(query_vec, query, metadata, embedder)

    # ---------------- FAISS retrieval sur tout le corpus
    query_vec = project_to_1024(query_vec)
    query_vec = sk_normalize(query_vec, axis=1)
    sims, indices = index.search(query_vec, top_k)
    faiss_scores, _, _, _ = ultra_reranker_scores(sims[0])

    # ---------------- BM25 rerank sur les résultats FAISS
    candidate_chunks = [chunks[i] for i in indices[0]]
    candidate_metadata = [metadata[i] for i in indices[0]]

    tokenized_candidates = [re.findall(r"\b[a-zA-Z0-9éèêàùôîç]+\b", c.lower()) for c in candidate_chunks]
    bm25 = BM25Okapi(tokenized_candidates)
    query_tokens = re.findall(r"\b[a-zA-Z0-9éèêàùôîç]+\b", tf_prompt.lower())
    bm25_scores = bm25.get_scores(query_tokens)

    # ---------------- Normalisation BM25
    bm25_scores = bm25_scores / (bm25_scores.max() + 1e-10)

    # ---------------- Combinaison FAISS + BM25
    combined_scores = 0.7 * faiss_scores + 0.3 * bm25_scores

    # ---------------- Construction des résultats
    
    results = []
    for score, chunk, meta in zip(combined_scores, candidate_chunks, candidate_metadata):
        print(f"[RESULT] {meta.get('source','-')} score_combined: {score:.6f}")
        if score >= Config.RAG_MIN_SCORE:
            results.append({
                "text": chunk,
                "metadata": meta,
                "score": float(score)
            })
            print(f"[ADD] {meta.get('source','-')} score_combined: {score:.6f}")

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results