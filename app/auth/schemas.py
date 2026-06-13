from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class UserRegister(BaseModel):
    username: str
    password: str
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RoleNameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    company_name: Optional[str] = None
    roles: List[RoleNameResponse] = []
