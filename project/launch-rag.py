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
from playwright.async_api import async_playwright
import json
import requests
import time
import asyncio
import re
import pandas as pd

async def scrap_page(url, start_url, to_visit, visited, documents, all_chunks, metadata):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            html_content = await page.content()
            await browser.close()

        # --- Parse HTML ---
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)

        # --- Chunking ---
        for i in range(0, len(text), Config.CHUNK_SIZE):
            chunk = text[i:i + Config.CHUNK_SIZE]
            all_chunks.append(chunk)
            metadata.append({
                "type": "web",
                "path": url,
                "source": start_url,
                "parent": start_url,
                "page": i  + 1,
                "chunk_id": i
            })

        documents.append({"url": url, "text": text})
        print(f"ADD : {url}")

        # --- Liens internes ---
        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link["href"])
            if urlparse(new_url).netloc == urlparse(start_url).netloc:
                if new_url not in visited:
                    to_visit.append(new_url)

        await asyncio.sleep(0.3)

    except Exception as e:
        print(f"Erreur sur {url}: {e}")


async def scrap_web_ressource():
    print("Load web archive from ./RAG/web_ressources/")

    urls = []
    for file in os.listdir(Config.RAG_WEB_ARCHIVE_PATH):
        if file.endswith(".json"):
            with open(os.path.join(Config.RAG_WEB_ARCHIVE_PATH, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                urls.extend(data.get("urls", []))

    print(f"Total URLs racines chargées: {len(urls)}")

    documents, all_chunks, metadata = [], [], []

    for start_url in urls:
        visited, to_visit = set(), [start_url]

        while to_visit and len(visited) < 10:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            await scrap_page(
                url=url,
                start_url=start_url,
                to_visit=to_visit,
                visited=visited,
                documents=documents,
                all_chunks=all_chunks,
                metadata=metadata
            )

    print(f"Nombre total de documents: {len(documents)}")
    print(f"Nombre total de chunks: {len(all_chunks)}")
    return documents, all_chunks, metadata



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
                try :
                    if filename.endswith(".pdf"):
                        reader = PdfReader(file_path)
                        for i, page in enumerate(reader.pages):

                                text = page.extract_text()
                                if text:
                                    chunks = split_text(text)
                                    for chunk in chunks:
                                        all_chunks.append(chunk)
                                        metadata.append({
                                            "type":"pdf",
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
                                        "type":"txt",
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
                                    "type":"docx",
                                    "source": filename,
                                    "path": file_path,
                                    "parent": root,
                                    "page": None
                                })
                    elif filename.endswith(".csv"):
                        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", sep=None, engine="python")
                        text = df.to_string(index=False)
                        if text.strip():
                            chunks = split_text(text)
                            for chunk in chunks:
                                all_chunks.append(chunk)
                                metadata.append({
                                    "type": "csv",
                                    "source": filename,
                                    "path": file_path,
                                    "parent": root,
                                    "page": None
                                })
                    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                        df = pd.read_excel(file_path, dtype=str, engine="openpyxl")
                        text = df.to_string(index=False)
                        if text.strip():
                            chunks = split_text(text)
                            for chunk in chunks:
                                all_chunks.append(chunk)
                                metadata.append({
                                    "type": "excel",
                                    "source": filename,
                                    "path": file_path,
                                    "parent": root,
                                    "page": None
                                })
                                
                except Exception as e:
                    print(f"Erreur lors de l'extraction du texte du document :  {e}")
    print(f"[Archive] Nombre total de chunks : {len(all_chunks)}")
    return all_chunks, metadata



if __name__ == "__main__":
    
    documents, all_chunks, metadata = asyncio.run(scrap_web_ressource())
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