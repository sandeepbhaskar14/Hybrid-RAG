import os
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.vector_store import add_chunks, delete_source

ALLOWED = (".txt", ".md", ".pdf", ".docx")

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def load_file(path):
    if path.endswith(".pdf"):
        return PyPDFLoader(path).load()
    if path.endswith(".docx"):
        return Docx2txtLoader(path).load()
    return TextLoader(path, encoding="utf-8").load()


def ingest_file(path):
    name = os.path.basename(path)
    chunks = splitter.split_documents(load_file(path))
    for chunk in chunks:
        chunk.metadata["source"] = name

    delete_source(name)  # re-ingesting a file replaces its old chunks
    if chunks:
        ids = [f"{name}-{i}" for i in range(len(chunks))]
        add_chunks(chunks, ids)
    return len(chunks)


def ingest_all():
    result = {}
    for name in os.listdir(settings.DOCS_DIR):
        if name.endswith(ALLOWED):
            result[name] = ingest_file(os.path.join(settings.DOCS_DIR, name))
    return result