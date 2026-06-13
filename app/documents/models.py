import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company_name = Column(String, nullable=False, index=True)
    document_type = Column(String, nullable=False)  # invoice / report / contract
    file_path = Column(String, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    uploader = relationship("User", back_populates="documents")
