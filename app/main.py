import os
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app import memory, rag
from app.config import settings
from app.ingestion import ALLOWED, ingest_all, ingest_file
from app.vector_store import delete_source

app = FastAPI()


class ChatBody(BaseModel):
    question: str
    chat_id: int | None = None        # None = start a new chat
    language: str = "English"
    attachment: str | None = None     # file name shown with the message
    regenerate: bool = False   # redo the last answer


class RenameBody(BaseModel):
    title: str


@app.get("/health")
def health():
    return {"status": "ok"}


# ── chat ─────────────────────────────────────────────
@app.post("/chat")
def chat(body: ChatBody):
    history = ""
    if body.chat_id is not None:
        if not memory.exists(body.chat_id):
            raise HTTPException(404, "Chat not found")
        if body.regenerate:
            memory.drop_last_turn(body.chat_id, body.question)
        history = memory.get_history(body.chat_id)

    result = rag.ask(body.question, history, body.language)

    chat_id = body.chat_id
    if chat_id is None:
        title = body.question.strip()
        chat_id = memory.create_chat(title[:40] + ("…" if len(title) > 40 else ""))
    memory.add_turn(chat_id, body.question, result["answer"], result["sources"], body.attachment)

    return {"chat_id": chat_id, **result}


@app.get("/chats")
def list_chats():
    return memory.list_chats()


@app.get("/chats/{chat_id}")
def get_chat(chat_id: int):
    chat = memory.get_chat(chat_id)
    if chat is None:
        raise HTTPException(404, "Chat not found")
    return chat


@app.patch("/chats/{chat_id}")
def rename_chat(chat_id: int, body: RenameBody):
    if not memory.exists(chat_id):
        raise HTTPException(404, "Chat not found")
    memory.rename_chat(chat_id, body.title.strip() or "Untitled")
    return {"id": chat_id, "title": body.title}


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    memory.delete_chat(chat_id)
    return {"deleted": chat_id}


# ── documents ────────────────────────────────────────
@app.get("/documents")
def list_documents():
    docs = []
    for name in sorted(os.listdir(settings.DOCS_DIR)):
        if name.endswith(ALLOWED):
            docs.append({"name": name, "size": os.path.getsize(os.path.join(settings.DOCS_DIR, name))})
    return docs


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    name = os.path.basename(file.filename)
    if not name.endswith(ALLOWED):
        raise HTTPException(400, f"Supported types: {', '.join(ALLOWED)}")
    path = os.path.join(settings.DOCS_DIR, name)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"file": name, "chunks": ingest_file(path)}


@app.delete("/documents/{name}")
def delete_document(name: str):
    name = os.path.basename(name)
    path = os.path.join(settings.DOCS_DIR, name)
    if os.path.exists(path):
        os.remove(path)
    delete_source(name)
    return {"deleted": name}


@app.post("/ingest")
def ingest():
    """Re-index every file in data/docs/."""
    return ingest_all()