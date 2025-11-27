import sys
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config

# 🔹 Variables pour index et métadonnées
INDEX_FILE = os.path.join(Config.INDEX_FAISS, "faiss_index.idx")
META_FILE = os.path.join(Config.INDEX_FAISS, "faiss_metadata.pkl")


def load_faiss_index():
    """
    Charge l'index FAISS et les métadonnées si elles existent.
    """
    if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
        print("📂 Index FAISS trouvé, chargement...")
        index = faiss.read_index(INDEX_FILE)
        with open(META_FILE, "rb") as f:
            data = pickle.load(f)
        chunks = data["chunks"]
        metadata = data["metadata"]
        embedder = SentenceTransformer(Config.RAG_MODEL)
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
    """
    Crée un nouvel index FAISS à partir de chunks et metadata.
    """
    if not chunks:
        print("⚠️ Aucun chunk disponible")
        return None, None

    embedder = SentenceTransformer(Config.RAG_MODEL)
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    print("Shape des embeddings :", embeddings.shape)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    save_faiss_index(index, chunks, metadata)
    print(f"Index FAISS créé avec {index.ntotal} vecteurs")
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
    print(f"✅ {len(chunks_to_add)} nouveaux documents ajoutés à l'index FAISS.")

    return chunks, metadata, embedder, index


def retrieve(query, embedder, index, chunks, metadata, top_k=5):
    """
    Recherche les top_k chunks les plus proches d'une query.
    Version sécurisée pour éviter les erreurs.
    """
    if index is None or index.ntotal == 0:
        print("⚠️ L'index FAISS est vide.")
        return []

    if not chunks or not metadata:
        print("⚠️ Les chunks ou metadata sont vides.")
        return []

    # Assurer que top_k ne dépasse pas le nombre de vecteurs
    top_k = min(top_k, index.ntotal)

    query_vector = embedder.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vector, top_k)

    results = []
    for idx in indices[0]:
        if idx < len(chunks):
            results.append({
                "text": chunks[idx],
                "metadata": metadata[idx]
            })
        else:
            print(f"⚠️ Index FAISS {idx} hors limites pour chunks (len={len(chunks)})")

    return results
