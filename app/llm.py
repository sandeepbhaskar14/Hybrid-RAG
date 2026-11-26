"""All model providers live here. To switch to Gemini/Ollama/etc, only edit this file."""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.CHAT_MODEL,
                      api_key=settings.OPENAI_API_KEY,
                      base_url=settings.OPENAI_BASE_URL,
                      max_tokens=settings.LLM_MAX_TOKENS,
                      temperature=0)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL,
                            api_key=settings.OPENAI_API_KEY,
                            base_url=settings.OPENAI_BASE_URL)