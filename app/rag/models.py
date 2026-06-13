import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.database import Base


class RAGQueryLog(Base):
    """Audit log for all RAG search and query requests."""
    __tablename__ = "rag_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)       # /rag/search or /rag/query
    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    company_filter = Column(String, nullable=True)  # company_name filter applied (for Clients)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
