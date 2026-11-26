import os
from dotenv import load_dotenv

load_dotenv()  # reads OPENAI_API_KEY (and optional QDRANT_URL) from .env


class settings:
    DOCS_DIR = "data/docs"
    CHATS_FILE = "data/chats.json"

    # ── LLM + embeddings (OpenRouter) ──
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_MODEL = "openai/gpt-4o-mini"
    EMBEDDING_MODEL = "openai/text-embedding-3-small"
    EMBEDDING_DIM = 1536        # must match the embedding model (text-embedding-3-small = 1536)
    LLM_MAX_TOKENS = 1500

    # ── Qdrant ──
    QDRANT_PATH = "data/qdrant"             # local mode: files on disk, no server needed
    QDRANT_URL = os.getenv("QDRANT_URL")    # set this to use a Qdrant server instead (e.g. http://localhost:6333)
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION = "docs"

    # ── Chunking + retrieval ──
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    TOP_K = 4

    os.makedirs(DOCS_DIR, exist_ok=True)
