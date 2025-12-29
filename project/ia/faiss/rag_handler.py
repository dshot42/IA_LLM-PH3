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

from ia.faiss.faiss_handler import retrieve, faiss_index_handler
from config import Config

# ============================================================
# CONFIG CHUNKING (≈ 500 TOKENS / CHUNK)
# ============================================================

MAX_CHARS = 1800        # chunk cible (~450–500 tokens)
HARD_MAX_CHARS = 2400   # coupure de sécurité (~650 tokens)
MIN_CHARS = 120         # évite le bruit
OVERLAP_CHARS = 120     # continuité sémantique sans explosion


# ============================================================
# UTILS
# ============================================================

def merge_small_chunks(chunks, target=400):
    merged = []
    buffer = ""

    for c in chunks:
        if len(buffer) + len(c) <= target:
            buffer = buffer + " " + c if buffer else c
        else:
            if buffer:
                merged.append(buffer.strip())
            buffer = c

    if buffer:
        merged.append(buffer.strip())

    return merged


def apply_overlap(chunks):
    out = []
    for i, c in enumerate(chunks):
        if i > 0:
            c = chunks[i - 1][-OVERLAP_CHARS:] + " " + c
        out.append(c)
    return out


# ============================================================
# SMART CHUNK TEXT (NO TOKENIZER)
# ============================================================

def smart_chunk_text(text):
    if not text:
        return []

    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    if len(text) <= MAX_CHARS:
        return [text]

    # Coupures naturelles PRIORITAIRES
    segments = re.split(
        r"\n{2,}|(?<=\.)\s+(?=[A-ZÀ-Ö])|(?<=;)\s+",
        text
    )

    chunks = []
    buffer = ""

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        if len(buffer) + len(seg) + 1 <= MAX_CHARS:
            buffer += (" " if buffer else "") + seg
            continue

        if len(buffer) >= MIN_CHARS:
            chunks.append(buffer.strip())
            buffer = ""

        if len(seg) > MAX_CHARS:
            start = 0
            while start < len(seg):
                end = min(start + HARD_MAX_CHARS, len(seg))
                part = seg[start:end].strip()
                if len(part) >= MIN_CHARS:
                    chunks.append(part)
                start = end
        else:
            buffer = seg

    if buffer and len(buffer) >= MIN_CHARS:
        chunks.append(buffer.strip())

    return merge_small_chunks(chunks)


# ============================================================
# SMART CHUNK JSON (STRUCTURE PRESERVED)
# ============================================================

def smart_chunk_json(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return smart_chunk_text(data)

    text = json.dumps(data, ensure_ascii=False, indent=2)

    if len(text) <= MAX_CHARS:
        return [text]

    return smart_chunk_text(text)


def smart_chunk_auto(content, filename=""):
    if filename.lower().endswith(".json"):
        return smart_chunk_json(content)
    return smart_chunk_text(content)


# ============================================================
# WEB SCRAPING
# ============================================================

async def scrap_page(url, start_url, to_visit, visited, documents, all_chunks, metadata):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        blocks = []
        for tag in soup.find_all(
            ["p", "li", "pre", "code", "table", "section", "article", "h1", "h2", "h3"]
        ):
            txt = tag.get_text(" ", strip=True)
            if txt and len(txt) > 40:
                blocks.append(txt)

        for b in blocks:
            chunks = apply_overlap(smart_chunk_auto(b, url))
            for i, c in enumerate(chunks):
                all_chunks.append(c)
                metadata.append({
                    "type": "web",
                    "source": start_url,
                    "path": url,
                    "chunk": i
                })

        documents.append({
            "url": url,
            "text": soup.get_text(" ", strip=True)
        })

        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link["href"])
            if urlparse(new_url).netloc == urlparse(start_url).netloc:
                if new_url not in visited and new_url not in to_visit:
                    to_visit.append(new_url)

        await asyncio.sleep(0.1)

    except Exception as e:
        print(f"[WEB ERROR] {url}: {e}")


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

    return  all_chunks, metadata


# ============================================================
# LOCAL ARCHIVE
# ============================================================

def chunk_documents_from_archive(archive):
    all_chunks, metadata = [], []

    for root, _, files in os.walk(archive):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                text = ""

                if filename.lower().endswith((".txt", ".md", ".log", ".sql", ".json")):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()

                elif filename.lower().endswith(".pdf"):
                    reader = PdfReader(path)
                    for p in reader.pages:
                        if p.extract_text():
                            text += p.extract_text() + "\n"

                elif filename.lower().endswith(".docx"):
                    doc = Document(path)
                    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

                elif filename.lower().endswith(".csv"):
                    df = pd.read_csv(path, dtype=str, sep=None, engine="python")
                    text = df.to_string(index=False)

                elif filename.lower().endswith((".xlsx", ".xls")):
                    df = pd.read_excel(path, dtype=str)
                    text = df.to_string(index=False)

                if not text.strip():
                    continue

                chunks = apply_overlap(smart_chunk_auto(text, filename))

                for i, c in enumerate(chunks):
                    all_chunks.append(c)
                    metadata.append({
                        "type": os.path.splitext(filename)[1][1:],
                        "source": filename,
                        "path": path,
                        "chunk": i
                    })

            except Exception as e:
                print(f"[ARCHIVE ERROR] {path}: {e}")

    return all_chunks, metadata


# ============================================================
# MAIN
# ============================================================

def main():

    all_chunks_local, metadata_local = chunk_documents_from_archive(Config.WORKFLOW_ARCHIVE)
    if all_chunks_local:
        faiss_index_handler(all_chunks_local, metadata_local, True)
        print("✅ Indexation workflow terminée")
        
    all_chunks_local, metadata_local = chunk_documents_from_archive(Config.RAG_ARCHIVE_PATH)
    if all_chunks_local:
        faiss_index_handler(all_chunks_local, metadata_local, False)
        print("✅ Indexation locale terminée")


    all_chunks_web, metadata_web = asyncio.run(scrap_web_ressource())
    if all_chunks_web:
        faiss_index_handler(all_chunks_web, metadata_web, False)
        print("✅ Indexation web terminée")

    print("--- SUCCESS FAISS ARCHIVE ---")


if __name__ == "__main__":
    main()
