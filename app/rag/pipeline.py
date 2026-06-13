import os
import uuid
import qdrant_client
from qdrant_client import models
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from typing import Optional, List

from app.config import settings

COLLECTION_NAME = "financial_documents"
_embedding_model = None
_qdrant_client = None
_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        from app.rag.reranker import Reranker
        _reranker = Reranker()
    return _reranker

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model

def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    if settings.QDRANT_HOST:
        try:
            client = qdrant_client.QdrantClient(
                host=settings.QDRANT_HOST,
                port=int(settings.QDRANT_PORT),
                timeout=5.0
            )
            client.get_collections()
            _qdrant_client = client
            return _qdrant_client
        except Exception as e:
            print(f"Warning: Failed to connect to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. Error: {str(e)}")
            print("Falling back to local in-memory Qdrant client.")
            
    if settings.QDRANT_PATH == ":memory:":
        _qdrant_client = qdrant_client.QdrantClient(location=":memory:")
    else:
        # Resolve absolute or relative path
        db_path = settings.QDRANT_PATH
        # Ensure directories exist
        if "/" in db_path or "\\" in db_path:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _qdrant_client = qdrant_client.QdrantClient(path=db_path)
        
    return _qdrant_client

def ensure_collection(client: qdrant_client.QdrantClient):
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        if COLLECTION_NAME not in collection_names:
            embedder = get_embedding_model()
            vector_size = embedder.get_embedding_dimension() or 384
            
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
    except Exception as e:
        print(f"Error ensuring Qdrant collection: {str(e)}")

def extract_text_from_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {str(e)}")
            return ""
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text file {file_path}: {str(e)}")
            return ""

def index_document_by_id(document_id: str, db_session):
    from app.documents.models import Document
    doc = db_session.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found in database")
        
    text = extract_text_from_file(doc.file_path)
    if not text.strip():
        print(f"Warning: Extracted empty text from {doc.file_path}")
        return
        
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    if not chunks:
        return
        
    embedder = get_embedding_model()
    embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()
    
    client = get_qdrant_client()
    ensure_collection(client)
    
    # Remove existing chunks for this document (idempotency)
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )
        )
    except Exception as e:
        print(f"Warning: Failed to clear old embeddings: {str(e)}")
        
    # Generate points
    points = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = uuid.uuid4()  # Qdrant requires UUID objects, not strings
        points.append(
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "company_name": doc.company_name,
                    "text": chunk_text,
                    "chunk_index": idx
                }
            )
        )
        
    # Upload points
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"Successfully indexed document {document_id} in vector DB ({len(points)} chunks).")

def remove_document_from_vector_db(document_id: str):
    client = get_qdrant_client()
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        if COLLECTION_NAME in collection_names:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                )
            )
    except Exception as e:
        print(f"Warning: Failed to delete points from Qdrant: {str(e)}")

def get_document_chunks(document_id: str) -> list:
    client = get_qdrant_client()
    try:
        ensure_collection(client)
        res, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        chunks = []
        for point in res:
            chunks.append({
                "chunk_id": point.id,
                "text": point.payload.get("text"),
                "chunk_index": point.payload.get("chunk_index", 0),
                "company_name": point.payload.get("company_name"),
                "document_id": point.payload.get("document_id")
            })
            
        return sorted(chunks, key=lambda x: x["chunk_index"])
    except Exception as e:
        print(f"Error fetching chunks for document {document_id}: {str(e)}")
        return []

def semantic_search_rag(query: str, company_name: Optional[str] = None) -> list:
    client = get_qdrant_client()
    try:
        ensure_collection(client)
    except Exception as e:
        print(f"Error ensuring collection: {str(e)}")
        return []
        
    embedder = get_embedding_model()
    query_vector = embedder.encode(query).tolist()
    
    qdrant_filter = None
    if company_name:
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="company_name",
                    match=models.MatchValue(value=company_name)
                )
            ]
        )
        
    try:
        search_res = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=20
        )
        points = search_res.points
    except Exception as e:
        print(f"Error searching Qdrant: {str(e)}")
        return []
        
    chunks = []
    for hit in points:
        chunks.append({
            "chunk_id": hit.id,
            "text": hit.payload.get("text"),
            "document_id": hit.payload.get("document_id"),
            "company_name": hit.payload.get("company_name"),
            "chunk_index": hit.payload.get("chunk_index"),
            "score_vector": hit.score
        })
        
    reranker = get_reranker()
    top_5 = reranker.rerank(query, chunks, top_k=5)
    
    return top_5
