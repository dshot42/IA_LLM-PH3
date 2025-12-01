
from sklearn.preprocessing import normalize
import numpy as np
from sentence_transformers import SentenceTransformer
from config import Config 

# 🔹 Gestion de l'historique en mémoire
MAX_HISTORY = 5
user_histories = {}  # {user_ip: [history]}

def add_user_query(user_ip, query):
    """
    Ajoute une nouvelle requête à l'historique d'un utilisateur
    et garde les 5 dernières.
    """
    if user_ip not in user_histories:
        user_histories[user_ip] = []

    user_histories[user_ip].append(query)
    user_histories[user_ip] = user_histories[user_ip][-MAX_HISTORY:]
    return user_histories[user_ip]

def get_user_history(user_ip):
    """
    Récupère l'historique des requêtes pour un utilisateur donné.
    """
    return user_histories.get(user_ip, [])

def combine_query_with_history(query_vec, history_vecs):
    """
    Combine le vecteur de la query avec l'historique pondéré.
    Les requêtes les plus récentes ont plus de poids.
    """
    if not history_vecs:
        return query_vec

    n = len(history_vecs)
    # Poids linéaires : la plus récente a poids 1.0, la plus ancienne 0.2 (exemple)
    weights = np.linspace(0.2, 1.0, n)
    all_vecs = np.vstack([query_vec] + list(history_vecs))
    all_weights = np.append(1.0, weights)  # query = 1.0
    combined_vec = np.average(all_vecs, axis=0, weights=all_weights)
    return combined_vec



def filter_relevant_history(user_ip, query, top_k=3, min_similarity=0.8):
    """
    Retourne uniquement l'historique pertinent.
    """
    embedder = SentenceTransformer(Config.RAG_MODEL)
    history = get_user_history(user_ip)

    if not history:
        return []

    # Encodage
    query_vec = embedder.encode([query], convert_to_numpy=True)
    history_vecs = embedder.encode(history, convert_to_numpy=True)

    # Normalisation
    query_vec = normalize(query_vec, axis=1)
    history_vecs = normalize(history_vecs, axis=1)

    # Similarité cosine
    similarities = (history_vecs @ query_vec.T).flatten()

    # Filtrer par seuil
    relevant_indices = np.where(similarities >= min_similarity)[0]
    if not len(relevant_indices):
        return []

    # Trier selon la similarité décroissante
    sorted_idx = relevant_indices[np.argsort(-similarities[relevant_indices])]
    print(f"[HISTORY] Found {len(sorted_idx)} relevant history items for user {user_ip}.")
    return [history[i] for i in sorted_idx[:top_k]]