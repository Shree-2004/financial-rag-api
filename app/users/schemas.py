from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []  # Names of permissions to assign to this role

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[PermissionResponse] = []

class RoleAssign(BaseModel):
    user_id: int
    role_name: str

class UserRolesResponse(BaseModel):
    user_id: int
    roles: List[str]

class UserPermissionsResponse(BaseModel):
    user_id: int
    permissions: List[str]
