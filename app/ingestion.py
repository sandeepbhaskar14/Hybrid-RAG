"""INGESTION PIPELINE:  file -> load -> split -> tag -> embed + store in Qdrant."""
import os
import uuid

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.vector_store import add_chunks, delete_source

ALLOWED = (".txt", ".md", ".pdf", ".docx")

splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)


def load_file(path):
    """Step 1 - LOAD: file -> list of Documents (a PDF gives one Document per page)."""
    if path.endswith(".pdf"):
        return PyPDFLoader(path).load()
    if path.endswith(".docx"):
        return Docx2txtLoader(path).load()
    return TextLoader(path, encoding="utf-8").load()


def make_id(name, i):
    """Qdrant point ids must be UUIDs. Same file + same chunk number = same id,
    so ingesting a file twice overwrites instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}-{i}"))


def ingest_file(path):
    name = os.path.basename(path)

    # Step 1 - LOAD
    docs = load_file(path)

    # Step 2 - SPLIT: long text -> small overlapping chunks (so each one has a single focus)
    chunks = splitter.split_documents(docs)

    # Step 3 - TAG: metadata travels with each chunk, we use it for sources + deleting
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = name
        chunk.metadata["chunk"] = i

    # Step 4 - STORE: remove old chunks of this file, then embed + save the new ones
    delete_source(name)
    if chunks:
        ids = [make_id(name, i) for i in range(len(chunks))]
        add_chunks(chunks, ids)

    print(f"[ingest] {name}: {len(docs)} document(s) -> {len(chunks)} chunks stored")
    return len(chunks)


def ingest_all():
    result = {}
    for name in os.listdir(settings.DOCS_DIR):
        if name.endswith(ALLOWED):
            result[name] = ingest_file(os.path.join(settings.DOCS_DIR, name))
    return result