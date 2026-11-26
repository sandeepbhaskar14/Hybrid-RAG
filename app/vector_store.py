"""Everything that touches Qdrant lives here."""
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from app.config import settings

# 1. the model that turns text into vectors
embeddings = OpenAIEmbeddings(
    model=settings.EMBEDDING_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    check_embedding_ctx_length=False,   # send plain text (OpenRouter expects strings, not token arrays)
)

# 2. connect to Qdrant: a server if QDRANT_URL is set, otherwise a local folder
if settings.QDRANT_URL:
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
else:
    client = QdrantClient(path=settings.QDRANT_PATH)

# 3. make sure the collection exists (a collection = a table of vectors)
if not client.collection_exists(settings.COLLECTION):
    client.create_collection(
        collection_name=settings.COLLECTION,
        vectors_config=VectorParams(size=settings.EMBEDDING_DIM, distance=Distance.COSINE),
    )

# 4. LangChain wrapper: embeds text and reads/writes points for us
db = QdrantVectorStore(client=client, collection_name=settings.COLLECTION, embedding=embeddings)


def add_chunks(chunks, ids):
    """Embed every chunk and save (vector + text + metadata) as points in Qdrant."""
    db.add_documents(chunks, ids=ids)


def delete_source(name):
    """Delete every point that came from this file (used for re-upload and delete)."""
    client.delete(
        collection_name=settings.COLLECTION,
        points_selector=Filter(must=[
            FieldCondition(key="metadata.source", match=MatchValue(value=name))
        ]),
    )


def search(query, k=settings.TOP_K):
    """Embed the query, find the k closest points. Returns [(chunk, score), ...].
    Cosine score: closer to 1.0 = more similar."""
    return db.similarity_search_with_score(query, k=k)