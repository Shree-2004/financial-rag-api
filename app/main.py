import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal

# Import all models to register them on Base metadata before create_all
from app.auth.models import User
from app.users.models import Role, Permission
from app.documents.models import Document
from app.rag.models import RAGQueryLog
from app.auth.utils import get_password_hash

# Include routers
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.documents.router import router as documents_router
from app.rag.router import router as rag_router

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_db()
    yield

app = FastAPI(
    title="Financial Document Management System",
    description="FastAPI DMS with Semantic Search, RAG & RBAC",
    version="1.0.0",
    lifespan=lifespan
)

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(rag_router)

def seed_db():
    db = SessionLocal()
    try:
        # 1. Seed Permissions
        permissions_data = [
            ("roles:manage", "Manage roles and permissions"),
            ("document:create", "Upload and edit documents"),
            ("document:read", "Read document metadata"),
            ("document:read_all", "Read all documents from any company"),
            ("document:delete", "Delete documents"),
            ("rag:index", "Index or remove documents in Vector DB"),
            ("rag:search", "Perform semantic search across vector store")
        ]
        
        perms = {}
        for p_name, p_desc in permissions_data:
            perm = db.query(Permission).filter(Permission.name == p_name).first()
            if not perm:
                perm = Permission(name=p_name, description=p_desc)
                db.add(perm)
                db.commit()
                db.refresh(perm)
            perms[p_name] = perm
            
        # 2. Seed Roles and associate permissions
        roles_data = {
            "Admin": list(perms.keys()),
            "Financial Analyst": ["document:create", "document:read", "document:read_all", "rag:index", "rag:search"],
            "Auditor": ["document:read", "document:read_all", "rag:search"],
            "Client": ["document:read", "rag:search"]
        }
        
        for r_name, r_perms in roles_data.items():
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name, description=f"{r_name} Role")
                db.add(role)
                db.commit()
                db.refresh(role)
                
            role.permissions = [perms[p] for p in r_perms]
            db.commit()
            
        # 3. Seed default Admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("adminpass"),
                company_name="Internal"
            )
            admin_role = db.query(Role).filter(Role.name == "Admin").first()
            if admin_role:
                admin_user.roles.append(admin_role)
            db.add(admin_user)
            db.commit()
            print("Default admin user created: admin / adminpass")
            
    except Exception as e:
        print(f"Error during seeding: {str(e)}")
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def read_root():
    static_file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file_path):
        with open(static_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Welcome to the Financial Document Management System API!</h1>", status_code=200)
