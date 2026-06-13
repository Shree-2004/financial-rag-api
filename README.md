# Financial Document Management System with RAG

A FastAPI application for managing financial documents with semantic search, AI-powered Q&A (RAG), and role-based access control.

---

## Tech Stack

| Component | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Relational DB | SQLAlchemy + SQLite |
| Vector DB | Qdrant (local folder) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM / Generation | Ollama (`llama3`) — local & free |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Auth | JWT Bearer tokens |

---

## Step-by-Step: How to Run

### Step 1 — Prerequisites

Make sure you have installed:
- **Python 3.10+** → https://python.org/downloads
- **Git** (optional, to clone)

Check your Python version:
```bash
python --version
```

---

### Step 2 — Navigate to the Project

```bash
cd c:\Users\spand\Downloads\SHREESTAAASK\financial-rag
```

---

### Step 3 — Create & Activate a Virtual Environment

```bash
# Create the virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt.

---

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ This will download the embedding model (~90 MB) and cross-encoder (~70 MB) on first run. This is a one-time download.

---

### Step 5 — Configure Environment Variables

Copy the example file and edit if needed:

```bash
copy .env.example .env
```

Open `.env` and at minimum set a proper `SECRET_KEY`:
```env
SECRET_KEY=any-long-random-string-here-at-least-32-chars
```

Everything else works out-of-the-box with the defaults (SQLite + local Qdrant + Ollama).

---

### Step 6 — (Optional) Set Up Ollama for AI-Generated Answers

This is only needed for the `POST /rag/query` endpoint (full RAG with LLM).  
Skip this step if you only want semantic search (`POST /rag/search`).

1. Download and install Ollama: https://ollama.com/download
2. Open a **new terminal** and run:
```bash
ollama pull llama3
ollama serve
```
3. Leave that terminal open while using the app.

---

### Step 7 — Start the Server

```bash
python -m uvicorn app.main:app --reload
```

You will see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

> On first start, the app automatically:
> - Creates all database tables (SQLite)
> - Seeds 4 roles: Admin, Financial Analyst, Auditor, Client
> - Creates a default admin user: **admin / adminpass**

---

### Step 8 — Open the API Docs (Swagger UI)

Visit in your browser:
```
http://127.0.0.1:8000/docs
```

To authenticate in Swagger:
1. Click the **Authorize 🔓** button (top right)
2. Enter `admin` / `adminpass`
3. Click **Authorize** → **Close**
4. All endpoints are now authenticated

---

## Quick Usage Guide

### 1. Register a new user
```
POST /auth/register
{
  "username": "alice",
  "password": "securepass123",
  "company_name": "Acme Corp"
}
```

### 2. Login and get a token
```
POST /auth/login
{
  "username": "alice",
  "password": "securepass123"
}
```
Returns: `{ "access_token": "eyJ...", "token_type": "bearer" }`

### 3. Upload a financial document
```
POST /documents/upload
  title        = "Q3 Financial Report"
  company_name = "Acme Corp"
  document_type = "report"    ← must be: invoice | report | contract
  file         = [attach .pdf or .txt file]
```
> The document is automatically chunked → embedded → stored in Qdrant.

### 4. Search documents by metadata
```
GET /documents/search?document_type=report&company_name=Acme+Corp
```

### 5. Semantic search (returns raw chunks)
```
POST /rag/search
{ "query": "financial risk related to high debt ratio" }
```

### 6. AI-powered Q&A (requires Ollama)
```
POST /rag/query
{ "query": "What are the key financial risks in the Acme report?" }
```
Returns: `{ "answer": "Based on the documents...", "sources": [...] }`

### 7. Assign a role (Admin only)
```
POST /users/assign-role
{ "user_id": 2, "role_name": "Financial Analyst" }
```

---

## RBAC Permissions Matrix

| Role | Upload Docs | Edit Docs | View All Docs | View Own Company | Semantic Search | Manage Roles |
|---|---|---|---|---|---|---|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Financial Analyst** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Auditor** | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Client** | ❌ | ❌ | ❌ | ✅ | ✅ (own company only) | ❌ |

---

## Full API Endpoint Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login (JSON) → JWT token |
| GET | `/auth/me` | Get current user info |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents/upload` | Upload a PDF or TXT document |
| GET | `/documents` | List documents (with `?skip=0&limit=20`) |
| GET | `/documents/search` | Filter by title, company, type, uploader |
| GET | `/documents/{document_id}` | Get single document details |
| PATCH | `/documents/{document_id}` | Update title / company / type |
| DELETE | `/documents/{document_id}` | Delete document + embeddings |

### RAG (Semantic Search & AI Q&A)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/rag/search` | Semantic search → top-5 chunks (no LLM) |
| POST | `/rag/query` | Full RAG → LLM-generated answer + sources |
| GET | `/rag/context/{document_id}` | All stored chunks for a document |
| POST | `/rag/index-document` | Manually re-index a document |
| DELETE | `/rag/remove-document/{id}` | Remove document embeddings from Qdrant |
| GET | `/rag/audit-log` | Admin: view all RAG query history |

### Roles & Users
| Method | Endpoint | Description |
|---|---|---|
| POST | `/roles/create` | Create a custom role (Admin) |
| GET | `/roles` | List all roles (Admin) |
| GET | `/roles/{role_id}` | Get role details (Admin) |
| POST | `/users/assign-role` | Assign role to user (Admin) |
| GET | `/users/{id}/roles` | Get user's roles |
| GET | `/users/{id}/permissions` | Get user's permissions |

---

## Running Tests

```bash
python -m pytest tests/test_flow.py -v
```

Expected output:
```
tests/test_flow.py::TestFinancialDMS::test_e2e_flow PASSED   [100%]
1 passed in ~40s
```

---

## Default Admin Credentials

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `adminpass` |

> ⚠️ Change these immediately in production!
