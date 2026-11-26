import os
from dotenv import load_dotenv

load_dotenv()  # reads OPENAI_API_KEY from .env

class settings:
    DOCS_DIR = "data/docs"
    CHROMA_DIR = "data/chroma"
    CHATS_FILE = "data/chats.json"

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_MODEL = "openai/gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"

    LLM_MAX_TOKENS = 600

    os.makedirs(DOCS_DIR, exist_ok=True)
