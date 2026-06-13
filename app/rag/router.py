from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import datetime

from app.database import get_db
from app.auth.utils import PermissionChecker, get_current_user, is_client, is_admin
from app.auth.models import User
from app.documents.models import Document
from app.rag.pipeline import index_document_by_id, remove_document_from_vector_db, get_document_chunks, semantic_search_rag
from app.rag.models import RAGQueryLog

router = APIRouter(prefix="/rag", tags=["rag"])


class IndexRequest(BaseModel):
    document_id: str


class SearchRequest(BaseModel):
    query: str


class QueryRequest(BaseModel):
    query: str


def _log_query(db: Session, user: User, endpoint: str, query: str, results_count: int, company_filter: Optional[str] = None):
    """Helper to write a RAG query audit log entry."""
    try:
        log = RAGQueryLog(
            user_id=user.id,
            username=user.username,
            endpoint=endpoint,
            query=query,
            results_count=results_count,
            company_filter=company_filter,
            created_at=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Warning: Failed to write RAG audit log: {str(e)}")


@router.post("/index-document", status_code=status.HTTP_200_OK)
def index_document(
    req: IndexRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["rag:index"]))
):
    doc = db.query(Document).filter(Document.document_id == req.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    try:
        index_document_by_id(req.document_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")
        
    return {"message": f"Document {req.document_id} successfully indexed in vector DB"}


@router.delete("/remove-document/{id}", status_code=status.HTTP_200_OK)
def remove_document(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["rag:index"]))
):
    try:
        remove_document_from_vector_db(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove embeddings: {str(e)}")
        
    return {"message": f"Embeddings for document {id} successfully removed from vector DB"}


@router.post("/search", status_code=status.HTTP_200_OK)
def search_rag(
    req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["rag:search"]))
):
    """Semantic search: returns top-5 most relevant document chunks (no LLM generation)."""
    company_name = None
    if is_client(current_user):
        company_name = current_user.company_name or ""
        
    try:
        results = semantic_search_rag(req.query, company_name=company_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute semantic search: {str(e)}")

    _log_query(db, current_user, "/rag/search", req.query, len(results), company_name)
    return results


@router.post("/query", status_code=status.HTTP_200_OK)
def query_rag(
    req: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["rag:search"]))
):
    """
    Full RAG endpoint: retrieves relevant chunks → passes to LLM → returns a generated answer.
    
    Use this for natural language financial Q&A.
    Use /rag/search if you want raw chunks without generation.
    """
    company_name = None
    if is_client(current_user):
        company_name = current_user.company_name or ""

    # Step 1: Retrieve and rerank top-5 chunks
    try:
        chunks = semantic_search_rag(req.query, company_name=company_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    if not chunks:
        _log_query(db, current_user, "/rag/query", req.query, 0, company_name)
        return {
            "answer": "No relevant financial documents found for your query.",
            "sources": []
        }

    # Step 2: Generate answer using LLM
    try:
        from app.rag.llm import generate_answer
        answer = generate_answer(req.query, chunks)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM generation failed: {str(e)}. Ensure Ollama is running or check your LLM_PROVIDER settings."
        )

    _log_query(db, current_user, "/rag/query", req.query, len(chunks), company_name)

    return {
        "answer": answer,
        "sources": chunks
    }


@router.get("/context/{document_id}", status_code=status.HTTP_200_OK)
def get_context(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:read"]))
):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    is_admin_user = is_admin(current_user)
    user_permissions = {perm.name for r in current_user.roles for perm in r.permissions}
    has_read_all = is_admin_user or "document:read_all" in user_permissions
    
    if not has_read_all and doc.company_name != current_user.company_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view context for this document"
        )
        
    try:
        chunks = get_document_chunks(document_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")
        
    return chunks


@router.get("/audit-log", status_code=status.HTTP_200_OK)
def get_audit_log(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["roles:manage"]))
):
    """Admin-only: retrieve the RAG query audit log."""
    logs = db.query(RAGQueryLog).order_by(RAGQueryLog.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": log.id,
            "username": log.username,
            "endpoint": log.endpoint,
            "query": log.query,
            "results_count": log.results_count,
            "company_filter": log.company_filter,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]
