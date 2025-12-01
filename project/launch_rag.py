import sys
import os
import re
import json
import asyncio
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from docx import Document
from playwright.async_api import async_playwright
from transformers import AutoTokenizer

import faiss_handler
from config import Config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ================= Smart chunking =================

# ================= Smart chunking =================


def smart_chunk(text, model_name="BAAI/bge-base-en-v1.5", max_tokens=512):
    """
    Découpe un texte en chunks <= max_tokens.
    - Découpe d'abord par retour à la ligne (\n), fin de phrase (.) et point-virgule (;)
    - Si le tokenizer lève une erreur de longueur, on redécoupe par virgule (,)
    - Re-chunke ensuite si un segment dépasse la limite
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Nettoyage
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    if not text:
        return []

    # Découpage initial par retour à la ligne, fin de phrase et point-virgule
    raw_segments = re.split(r'[\n]', text)
    raw_segments = [seg.strip() for seg in raw_segments if seg.strip()]

    chunks = []
    for seg in raw_segments:
        try:
            tokens = tokenizer.encode(seg, add_special_tokens=False)
        except Exception as e:
            print(f"[WARN] Erreur encodage: {e}, découpage par virgule appliqué.")
            # Si le tokenizer lève une erreur, on redécoupe par virgule
            sub_segments = [s.strip() for s in seg.split(".") if s.strip()]
            for sub in sub_segments:
                sub_tokens = tokenizer.encode(sub, add_special_tokens=False)
                if len(sub_tokens) <= max_tokens:
                    chunks.append(sub)
                else:
                    # Re-chunk si encore trop long
                    start = 0
                    while start < len(sub_tokens):
                        end = min(start + max_tokens, len(sub_tokens))
                        chunk_tokens = sub_tokens[start:end]
                        chunk_text = tokenizer.decode(chunk_tokens, clean_up_tokenization_spaces=True)
                        chunks.append(chunk_text.strip())
                        start = end
            continue  # passer au segment suivant

        # Cas normal
        if len(tokens) <= max_tokens:
            chunks.append(seg)
        else:
            # Re-chunk si un segment est trop long
            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = tokenizer.decode(chunk_tokens, clean_up_tokenization_spaces=True)
                chunks.append(chunk_text.strip())
                start = end

    return chunks




# ================= Scrap web pages =================

async def scrap_page(url, start_url, to_visit, visited, documents, all_chunks, metadata):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            html_content = await page.content()
            await browser.close()

        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "noscript", "form", "aside"]):
            tag.decompose()

        # Découpage par blocs HTML structurants
        text_blocks = []
        for tag in soup.find_all(["p","table", "h1", "h2", "h3", "h4", "h5", "h6", "div","section"]):
            txt = tag.get_text(" ", strip=True)
            if txt and len(txt.split()) >= 5:  # ignorer les blocs trop courts
                # Limite par caractères avant smart_chunk
                if len(txt) > 2000:
                    text_blocks.extend([txt[i:i+2000] for i in range(0, len(txt), 2000)])
                else:
                    text_blocks.append(txt)

        # Application du smart_chunk sur chaque bloc
        for b in text_blocks:
            try:
                for idx, chunk in enumerate(smart_chunk(b)):
                    all_chunks.append(chunk)
                    metadata.append({
                        "type": "web",
                        "path": url,
                        "source": start_url,
                        "parent": start_url,
                        "page": idx + 1,
                        "chunk_id": idx
                    })
            except Exception as e:
                print(f"[WARN] Chunking error on {url}: {e}")

        # Sauvegarde du texte brut complet (optionnel)
        full_text = soup.get_text(" ", strip=True)
        documents.append({"url": url, "text": full_text})

        # Internal links
        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link["href"])
            if urlparse(new_url).netloc == urlparse(start_url).netloc:
                if new_url not in visited and new_url not in to_visit:
                    to_visit.append(new_url)

        await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Erreur sur {url}: {e}")
        
        

async def scrap_web_ressource(max_pages_per_site=10):
    urls = []
    for file in os.listdir(Config.RAG_WEB_ARCHIVE_PATH):
        if file.endswith(".json"):
            with open(os.path.join(Config.RAG_WEB_ARCHIVE_PATH, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                urls.extend(data.get("urls", []))

    documents, all_chunks, metadata = [], [], []
    for start_url in urls:
        visited, to_visit = set(), [start_url]
        while to_visit and len(visited) < max_pages_per_site:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            await scrap_page(url, start_url, to_visit, visited, documents, all_chunks, metadata)

    return documents, all_chunks, metadata

# ================= Local archive =================

def chunk_documents_from_archive():
    all_chunks, metadata = [], []
    for root, dirs, files in os.walk(Config.RAG_ARCHIVE_PATH):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                text = ""
                if filename.lower().endswith(".pdf"):
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
                elif filename.lower().endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                elif filename.lower().endswith(".docx"):
                    doc = Document(file_path)
                    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                elif filename.lower().endswith(".csv"):
                    try:
                        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", sep=None, engine="python")
                    except:
                        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", engine="python")
                    text = df.to_string(index=False)
                elif filename.lower().endswith((".xlsx", ".xls")):
                    try:
                        df = pd.read_excel(file_path, dtype=str, engine="openpyxl")
                    except:
                        df = pd.read_excel(file_path, dtype=str)
                    text = df.to_string(index=False)
                else:
                    continue

                if not text.strip():
                    continue

                chunks = smart_chunk(text)
                for idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    metadata.append({
                        "type": os.path.splitext(filename)[1][1:],
                        "source": filename,
                        "path": file_path,
                        "parent": root,
                        "page": idx + 1
                    })
            except Exception as e:
                print(f"Erreur extraction fichier {file_path}: {e}")

    return all_chunks, metadata

# ================= Entrypoint =================

def main():
    # Web scraping
    documents_web, all_chunks_web, metadata_web = asyncio.run(scrap_web_ressource())
    if all_chunks_web:
        print("Indexation web...")
        chunks, metadata, embedder, index = faiss_handler.faiss_index_handler(all_chunks_web, metadata_web)

    # Local archive
    all_chunks_local, metadata_local = chunk_documents_from_archive()
    if all_chunks_local:
        print("Indexation locale...")
        chunks, metadata, embedder, index = faiss_handler.faiss_index_handler(all_chunks_local, metadata_local)

    # Test search
    query = "quel est le numero france travail de monsieur dubost"
    query_chunks = smart_chunk(query)  # chunk query <=512 tokens
    results = []
    for chunk in query_chunks:
        results.extend(faiss_handler.retrieve("none", chunk))

    for r in results:
        text_clean = r['text'][:180].replace("\n", " ")
        print(f"[{r['score']:.3f}] {r['metadata'].get('source','-')} - {text_clean}...")

if __name__ == "__main__":
    main()
