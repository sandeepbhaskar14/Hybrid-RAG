from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from app.config import settings

db = Chroma(
    collection_name="docs",
    embedding_function=OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        check_embedding_ctx_length=False,   # send plain text, not OpenAI token arrays
    ),
    persist_directory=settings.CHROMA_DIR,
)


def add_chunks(chunks, ids):
    db.add_documents(chunks, ids=ids)


def delete_source(name):
    db.delete(where={"source": name})


def search(query, k=4):
    return db.similarity_search(query, k=k)