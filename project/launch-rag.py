import sys
import os
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config
import eval  # prompter
import model as model_utils
import faiss_handler
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import json
import requests
import time


def scrap_web_ressource():
    print ("Load web archive where url in ./RAG/web_ressources/")
    urls = []
    # 1. Charger toutes les URLs depuis les fichiers JSON
    for file in os.listdir(Config.RAG_WEB_ARCHIVE_PATH):
        if file.endswith(".json"):
            path = os.path.join(Config.RAG_WEB_ARCHIVE_PATH, file)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                urls.extend(data.get("urls", []))

    print(f"Total URLs racines chargées: {len(urls)}")

    documents = []
    all_chunks = []
    metadata = []

    # 2. Pour chaque URL racine, lancer un petit crawler
    for start_url in urls:
        visited = set()
        to_visit = [start_url]

        while to_visit and len(visited) < 10:  # continue tant qu'il reste des pages à visiter
        #while to_visit # scrap jusqu'a la derniere page de l'aboressence
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)

                # Découpage en chunks
                for i in range(0, len(text), Config.CHUNK_SIZE):
                    chunk = text[i:i+Config.CHUNK_SIZE]
                    all_chunks.append(chunk)
                    metadata.append({
                        "type":"web",
                        "path": url,
                        "source": start_url,
                        "parent": start_url,
                        "page": (i // Config.CHUNK_SIZE) + 1,
                        "chunk_id": i // Config.CHUNK_SIZE
                    })

                documents.append({"url": url, "text": text})
                print("ADD : "+url)
                if (i == 10): # on break apres 10 page
                    break 


                # Ajouter les liens internes à visiter
                for link in soup.find_all("a", href=True):
                    new_url = urljoin(url, link["href"])
                    if urlparse(new_url).netloc == urlparse(start_url).netloc:
                        if new_url not in visited:
                            to_visit.append(new_url)

                time.sleep(0.5)  # éviter de surcharger le site

            except Exception as e:
                print(f"Erreur sur {url}: {e}")

    print(f"Nombre total de documents: {len(documents)}")
    print(f"Nombre total de chunks: {len(all_chunks)}")
    return  all_chunks, metadata



def split_text(text, chunk_size=Config.CHUNK_SIZE, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def chunkDocuments():
    print ("Load local archive in folder ./RAG/archive/")
    all_chunks = []
    metadata = []
    for root, dirs, files in os.walk(Config.RAG_ARCHIVE_PATH):
        for filename in files:
            if filename.endswith((".pdf", ".txt", ".docx")):
                file_path = os.path.join(root, filename)
                if filename.endswith(".pdf"):
                    reader = PdfReader(file_path)
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text:
                            chunks = split_text(text)
                            for chunk in chunks:
                                all_chunks.append(chunk)
                                metadata.append({
                                    "type":"doc",
                                    "source": filename,
                                    "path": file_path,
                                    "parent": root,
                                    "page": i+1
                                })
                elif filename.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        if text.strip():
                            chunks = split_text(text)
                            for chunk in chunks:
                                all_chunks.append(chunk)
                                metadata.append({
                                    "source": filename,
                                    "path": file_path,
                                    "parent": root,
                                    "page": None
                                })
                elif filename.endswith(".docx"):
                    doc = Document(file_path)
                    full_text = [para.text for para in doc.paragraphs]
                    text = "\n".join(full_text)
                    if text.strip():
                        chunks = split_text(text)
                        for chunk in chunks:
                            all_chunks.append(chunk)
                            metadata.append({
                                "source": filename,
                                "path": file_path,
                                "parent": root,
                                "page": None
                            })
    print(f"Nombre total de chunks : {len(all_chunks)}")
    return all_chunks, metadata



if __name__ == "__main__":
    
    all_chunks, metadata = scrap_web_ressource()
    all_chunks, metadata, embedder, index = faiss_handler.faiss_index_handler(all_chunks, metadata)  
    
    all_chunks, metadata = chunkDocuments()
    all_chunks, metadata, embedder, index = faiss_handler.faiss_index_handler(all_chunks, metadata)  
    
    def faiss_search(): 
        query = "donne moi le n° france travail de monsieur dubost en une réponse simple"
        tokenizer = model_utils.load_tokenizer()
        model = model_utils.load_model_with_qlora()
        print(" --- Model with QLoRA Loaded ...")
        
        eval.faiss_search(query, model, tokenizer)
        
            
    faiss_search()