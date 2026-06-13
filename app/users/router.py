from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth.utils import PermissionChecker, get_current_user
from app.auth.models import User
from app.users.models import Role, Permission
from app.users.schemas import RoleCreate, RoleResponse, RoleAssign, UserRolesResponse, UserPermissionsResponse

router = APIRouter(tags=["roles"])

@router.post("/roles/create", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: RoleCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["roles:manage"]))
):
    existing_role = db.query(Role).filter(Role.name == role_in.name).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = Role(name=role_in.name, description=role_in.description)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    for perm_name in role_in.permissions:
        perm = db.query(Permission).filter(Permission.name == perm_name).first()
        if not perm:
            perm = Permission(name=perm_name)
            db.add(perm)
            db.commit()
            db.refresh(perm)
        new_role.permissions.append(perm)
    
    db.commit()
    db.refresh(new_role)
    return new_role

@router.post("/users/assign-role", status_code=status.HTTP_200_OK)
def assign_role(
    assign_in: RoleAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["roles:manage"]))
):
    user = db.query(User).filter(User.id == assign_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    role = db.query(Role).filter(Role.name == assign_in.role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role not in user.roles:
        user.roles.append(role)
        db.commit()
        
    return {"message": f"Role '{assign_in.role_name}' successfully assigned to user '{user.username}'"}

@router.get("/users/{id}/roles", response_model=UserRolesResponse)
def get_user_roles(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce that user can only look up themselves, or admin can look up anyone
    if current_user.id != id:
        is_admin = any(role.name == "Admin" for role in current_user.roles)
        user_permissions = {perm.name for r in current_user.roles for perm in r.permissions}
        if not is_admin and "roles:manage" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other users' roles"
            )
            
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    roles = [role.name for role in user.roles]
    return {"user_id": id, "roles": roles}

@router.get("/users/{id}/permissions", response_model=UserPermissionsResponse)
def get_user_permissions(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce that user can only look up themselves, or admin can look up anyone
    if current_user.id != id:
        is_admin = any(role.name == "Admin" for role in current_user.roles)
        user_permissions = {perm.name for r in current_user.roles for perm in r.permissions}
        if not is_admin and "roles:manage" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other users' permissions"
            )
            
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    permissions = set()
    is_admin_user = any(role.name == "Admin" for role in user.roles)
    
    if is_admin_user:
        all_perms = db.query(Permission).all()
        permissions = {perm.name for perm in all_perms}
    else:
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)
                
    return {"user_id": id, "permissions": list(permissions)}


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["roles:manage"]))
):
    """List all roles with their permissions. Admin only."""
    return db.query(Role).all()


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(["roles:manage"]))
):
    """Get a specific role by ID. Admin only."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role
