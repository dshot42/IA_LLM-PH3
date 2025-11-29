import sys
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config
import math

# 🔹 Variables pour index et métadonnées
INDEX_FILE = os.path.join(Config.INDEX_FAISS, "faiss_index.idx")
META_FILE = os.path.join(Config.INDEX_FAISS, "faiss_metadata.pkl")


def load_faiss_index():
    if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
        print("📂 Index FAISS trouvé, chargement...")
        index = faiss.read_index(INDEX_FILE)
        with open(META_FILE, "rb") as f:
            data = pickle.load(f)
        chunks = data["chunks"]
        metadata = data["metadata"]
        embedder = SentenceTransformer(Config.RAG_MODEL)
        print("Load count chunks:", len(chunks))
        return chunks, metadata, embedder, index
    else:
        print("⚠️ Aucun index existant.")
        return None, None, None, None


def save_faiss_index(index, chunks, metadata):
    """
    Sauvegarde l'index FAISS et les métadonnées.
    """
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "wb") as f:
        pickle.dump({"chunks": chunks, "metadata": metadata}, f)

    doc_names = [m.get("path", "inconnu") for m in metadata]
    print("✅ Index FAISS et métadonnées sauvegardés pour les documents :", ", ".join(doc_names))
    print("--------------------------")


def build_faiss_index(chunks, metadata):
    if not chunks:
        print("⚠️ Aucun chunk à indexer")
        return None, None

    embedder = SentenceTransformer(Config.RAG_MODEL)
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    embeddings = normalize(embeddings, axis=1)  # ||v|| = 1

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)  # inner product = cosine similarity
    index.add(embeddings)

    save_faiss_index(index, chunks, metadata)
    print(f"✅ Index FAISS créé avec {index.ntotal} vecteurs normalisés")
    return embedder, index


def faiss_index_handler(new_chunks, new_metadata):
    """
    Ajoute de nouveaux chunks à l'index existant ou crée un nouvel index si nécessaire.
    """
    chunks, metadata, embedder, index = load_faiss_index()

    # Si aucun index existant, on le crée directement
    if chunks is None or metadata is None or index is None:
        print("⚠️ Création d'un nouvel index FAISS pour les nouveaux documents...")
        embedder, index = build_faiss_index(new_chunks, new_metadata)
        return new_chunks, new_metadata, embedder, index  # <-- Retourne bien 4 valeurs

    # Détecter les nouveaux documents pour éviter les doublons
    new_entries = []
    existing_filenames = [m.get("path") for m in metadata]
    for chunk, meta in zip(new_chunks, new_metadata):
        if meta.get("path") not in existing_filenames:
            new_entries.append((chunk, meta))

    if not new_entries:
        print("ℹ️ Aucun nouveau document à ajouter.")
        return chunks, metadata, embedder, index

    # Ajouter les embeddings des nouveaux chunks
    chunks_to_add, metadata_to_add = zip(*new_entries)
    embeddings_to_add = embedder.encode(list(chunks_to_add), convert_to_numpy=True)
    index.add(embeddings_to_add)

    # Mettre à jour les listes
    chunks.extend(chunks_to_add)
    metadata.extend(metadata_to_add)

    save_faiss_index(index, chunks, metadata)
    for f in  list({m.get("path") for m in metadata_to_add}):
      print(f"Ajout du Document  : {f}")
      
    print(f"✅ {len(chunks_to_add)} nouveaux documents ajoutés à l'index FAISS.")
    return chunks, metadata, embedder, index


import numpy as np

def retrieve(query, top_k=5, min_score=Config.RAG_MIN_SCORE): # 0.5 tolerance 0.7 strict
    chunks, metadata, embedder, index = load_faiss_index()
    if not embedder or index is None or not chunks or not metadata:
        return []

    top_k = min(top_k, index.ntotal)

    # Embedding de la query et normalisation
    query_vector = embedder.encode([query], convert_to_numpy=True)
    query_vector = normalize(query_vector, axis=1).astype("float32")

    # Recherche FAISS
    scores, indices = index.search(query_vector, top_k)

    results = []

    for dist, idx in zip(scores[0], indices[0]):
        if idx >= len(chunks):
            continue
       
        alpha = 1.0
        score = math.exp(-alpha * dist) # lissage exp 0-1
        
        print("score:", score, "doc:", metadata[idx]["source"])
        if score >= min_score:  #  plus le score est proche de 1 plus la prediction est bonne ! 
            results.append({
                "text": chunks[idx],
                "metadata": metadata[idx],
                "score": float(score)
            })

    return results
