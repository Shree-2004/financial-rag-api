"""
LLM Manager for RAG generation.
Supports Ollama (default), OpenAI, and Google Gemini via LangChain.
Configured through environment variables:
  LLM_PROVIDER = ollama | openai | gemini
  LLM_MODEL    = llama3 | gpt-4o | gemini-1.5-flash | etc.
"""
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings

_llm = None

FINANCIAL_SYSTEM_PROMPT = """You are a financial document analyst. Your job is to answer questions about financial documents accurately and concisely.

You will be given relevant excerpts from financial documents as context. Use ONLY this context to answer the question.
If the context does not contain enough information to answer the question, say so clearly.

Always cite which document or company the information comes from when possible.

Context from financial documents:
{context}
"""

def get_llm():
    """Return the configured LLM instance (singleton)."""
    global _llm
    if _llm is not None:
        return _llm

    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            _llm = ChatOllama(
                model=settings.LLM_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.1
            )
        except ImportError:
            raise ImportError(
                "langchain-ollama is not installed. Run: pip install langchain-ollama"
            )

    elif provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set in .env")
            _llm = ChatOpenAI(
                model=settings.LLM_MODEL or "gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
        except ImportError:
            raise ImportError(
                "langchain-openai is not installed. Run: pip install langchain-openai"
            )

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is not set in .env")
            _llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL or "gemini-1.5-flash",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.1
            )
        except ImportError:
            raise ImportError(
                "langchain-google-genai is not installed. Run: pip install langchain-google-genai"
            )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. Must be one of: ollama, openai, gemini"
        )

    return _llm


def build_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a readable context block for the LLM."""
    if not chunks:
        return "No relevant document excerpts found."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        doc_id = chunk.get("document_id", "unknown")
        company = chunk.get("company_name", "unknown")
        text = chunk.get("text", "")
        parts.append(
            f"[Excerpt {i} | Company: {company} | Document ID: {doc_id}]\n{text}"
        )

    return "\n\n---\n\n".join(parts)


def generate_answer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Generate a natural language answer using the LLM with retrieved chunks as context.

    Args:
        query: The user's financial question.
        chunks: Top-k retrieved and reranked document chunks.

    Returns:
        A synthesized answer string from the LLM.
    """
    llm = get_llm()
    context = build_context(chunks)

    prompt = ChatPromptTemplate.from_messages([
        ("system", FINANCIAL_SYSTEM_PROMPT),
        ("human", "{question}")
    ])

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "context": context,
        "question": query
    })

    return answer
