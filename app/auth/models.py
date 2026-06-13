from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for User <-> Role (defined here so both models can reference it)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    company_name = Column(String, nullable=True)

    # Many-to-many with Role via shared association table
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    # One-to-many with Document — use string so Document can be defined later
    documents = relationship("Document", back_populates="uploader", lazy="select")
