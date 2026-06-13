import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth.utils import PermissionChecker, get_current_user, is_client, is_admin
from app.auth.models import User
from app.documents.models import Document
from app.documents.schemas import DocumentResponse, DocumentUpdate
from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_DOC_TYPES = {"invoice", "report", "contract"}

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    title: str = Form(...),
    company_name: str = Form(...),
    document_type: str = Form(...),  # invoice / report / contract
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:create"]))
):
    if is_client(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to upload documents"
        )

    # Validate document_type
    if document_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. Must be one of: {', '.join(sorted(ALLOWED_DOC_TYPES))}"
        )

    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
        
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    
    doc_id = str(uuid.uuid4())
    file_name = f"{doc_id}{file_ext}"
    file_path = os.path.join(settings.STORAGE_DIR, file_name)
    
    try:
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    new_doc = Document(
        document_id=doc_id,
        title=title,
        company_name=company_name,
        document_type=document_type,
        file_path=file_path,
        uploaded_by=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # Automatically index the document in the vector DB
    try:
        from app.rag.pipeline import index_document_by_id
        index_document_by_id(doc_id, db)
    except Exception as e:
        print(f"Warning: RAG indexing failed for {doc_id}: {str(e)}")
        
    return new_doc

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:read"]))
):
    query = db.query(Document)
    
    if is_client(current_user):
        company = current_user.company_name or ""
        query = query.filter(Document.company_name == company)
    else:
        user_permissions = {perm.name for r in current_user.roles for perm in r.permissions}
        if "document:read_all" not in user_permissions and not is_admin(current_user):
            company = current_user.company_name or ""
            query = query.filter(Document.company_name == company)
            
    return query.offset(skip).limit(limit).all()

@router.get("/search", response_model=List[DocumentResponse])
def search_documents(
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    uploaded_by: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:read"]))
):
    # Validate document_type filter if provided
    if document_type and document_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type filter. Must be one of: {', '.join(sorted(ALLOWED_DOC_TYPES))}"
        )

    query = db.query(Document)
    
    user_permissions = {perm.name for r in current_user.roles for perm in r.permissions}
    has_read_all = is_admin(current_user) or "document:read_all" in user_permissions
    
    if not has_read_all:
        company_filter = current_user.company_name or ""
        query = query.filter(Document.company_name == company_filter)
    else:
        if company_name:
            query = query.filter(Document.company_name == company_name)
            
    if title:
        query = query.filter(Document.title.ilike(f"%{title}%"))
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if uploaded_by:
        query = query.filter(Document.uploaded_by == uploaded_by)
        
    return query.offset(skip).limit(limit).all()

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
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
            detail="You do not have permission to access this document"
        )
        
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:delete"]))
):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            print(f"Warning: Failed to delete physical file {doc.file_path}: {str(e)}")
            
    try:
        from app.rag.pipeline import remove_document_from_vector_db
        remove_document_from_vector_db(document_id)
    except Exception as e:
        print(f"Warning: Failed to remove embeddings for {document_id}: {str(e)}")
        
    db.delete(doc)
    db.commit()
    
    return {"message": "Document and its embeddings successfully deleted"}


@router.patch("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["document:create"]))
):
    """Update document metadata (title, company_name, document_type). Admin or Analyst only."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Non-admin users can only update documents within their company
    is_admin_user = is_admin(current_user)
    if not is_admin_user and doc.company_name != current_user.company_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update documents belonging to your company"
        )

    company_changed = False

    if update_data.title is not None:
        doc.title = update_data.title
    if update_data.document_type is not None:
        if update_data.document_type not in ALLOWED_DOC_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document_type. Must be one of: {', '.join(sorted(ALLOWED_DOC_TYPES))}"
            )
        doc.document_type = update_data.document_type
    if update_data.company_name is not None:
        company_changed = update_data.company_name != doc.company_name
        doc.company_name = update_data.company_name

    db.commit()
    db.refresh(doc)

    # Re-index in Qdrant if company_name changed (payload filter depends on it)
    if company_changed:
        try:
            from app.rag.pipeline import index_document_by_id
            index_document_by_id(document_id, db)
        except Exception as e:
            print(f"Warning: RAG re-indexing failed after update for {document_id}: {str(e)}")

    return doc
