import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    title: str
    company_name: str
    document_type: str
    uploaded_by: Optional[int] = None
    created_at: datetime.datetime


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
