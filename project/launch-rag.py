import sys
import os
import pickle
import faiss
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config
import eval  # prompter
import model as model_utils
import faiss_handler



def split_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def chunkDocuments():
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
    all_chunks, metadata = chunkDocuments()
    all_chunks, metadata, embedder, index = faiss_handler.faiss_index_handler(all_chunks, metadata)     
    
    def faiss_search(query,all_chunks, metadata):
        tokenizer = model_utils.load_tokenizer()

        print(" --- Loading model with QLoRA...")
        model = model_utils.load_model_with_qlora()
        
        if embedder and index and all_chunks:
            retrieved = faiss_handler.retrieve(query, embedder, index, all_chunks, metadata)

            # Construire le contexte
            context = "\n\n".join([
                f"{r['text']} (source: {r['metadata']['source']}, page: {r['metadata']['page']})"
                for r in retrieved
            ])

            # Passer au prompter
            response_text = eval.prompt_query(context, model, tokenizer)
            print(response_text)
        else:
            print("⚠️ Aucun index disponible, impossible de faire la recherche.")
            
            
    faiss_search(  query = "Quels sont les concepts clés du document '2965fe23-bb38-document-de-synthese-j00171777071-v1.pdf' ?",all_chunks=all_chunks, metadata=metadata)