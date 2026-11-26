from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings
from app.vector_store import search

llm = ChatOpenAI(
    model=settings.CHAT_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    max_tokens=settings.LLM_MAX_TOKENS,
    temperature=0,
)

rewrite_prompt = ChatPromptTemplate.from_template("""Chat history:
{history}

Rewrite the follow-up question so it makes sense on its own. Do not answer it.
Follow-up: {question}
Standalone question:""")

answer_prompt = ChatPromptTemplate.from_template("""Answer the question using only the context below.
If the answer is not in the context, say you don't know.
Reply in {language}.

Context:
{context}

Chat history:
{history}

Question: {question}""")

rewrite_chain = rewrite_prompt | llm | StrOutputParser()
answer_chain = answer_prompt | llm | StrOutputParser()


def ask(question, history="", language="English"):
    # 1. turn "what about its cost?" into a full question using the history
    search_query = question
    if history:
        search_query = rewrite_chain.invoke({"history": history, "question": question})

    # 2. RETRIEVE: embed the query, ask Qdrant for the closest chunks
    results = search(search_query)              # [(chunk, score), ...]
    chunks = [chunk for chunk, score in results]
    context = "\n\n".join(c.page_content for c in chunks)

    # 3. ask the LLM, using those chunks as context
    answer = answer_chain.invoke(
        {"context": context, "history": history, "question": question, "language": language}
    )

    sources = sorted({c.metadata["source"] for c in chunks})
    return {"answer": answer, "sources": sources}