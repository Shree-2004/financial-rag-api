# 💼 Financial Document Management System with RAG

> A production-ready **FastAPI** application for managing financial documents with AI-powered semantic search, LLM-generated answers (RAG), and enterprise-grade role-based access control.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-1C3C3C?style=flat&logo=chainlink&logoColor=white)](https://langchain.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC143C?style=flat)](https://qdrant.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 What This Project Does

Organizations deal with hundreds of financial documents — reports, invoices, contracts, audits. Finding specific information across all of them is slow and manual.

This system solves that by:
1. **Storing** financial documents with metadata and access control
2. **Indexing** them into a vector database using AI embeddings
3. **Searching** semantically — find relevant content even if the exact keywords don't match
4. **Answering** natural language questions using an LLM (Ollama/OpenAI/Gemini)

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔐 **JWT Authentication** | Secure login & registration with Bearer tokens |
| 👥 **Role-Based Access Control** | Admin, Financial Analyst, Auditor, Client roles |
| 🏢 **Multi-Tenant Isolation** | Clients only see their own company's documents |
| 📄 **Document Management** | Upload, list, update, delete PDF & TXT documents |
| 🔍 **Semantic Search** | Vector similarity search using `all-MiniLM-L6-v2` embeddings |
| 🏆 **Cross-Encoder Reranking** | Reranks Top-20 results to surface the best Top-5 |
| 🤖 **RAG Q&A** | LLM-generated answers with source citations |
| 📊 **Audit Logging** | All RAG queries are logged for compliance |
| 🖥️ **Web UI** | Built-in glassmorphism dashboard — no Swagger needed |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI + Uvicorn |
| **Relational Database** | SQLAlchemy + SQLite (PostgreSQL-ready) |
| **Vector Database** | Qdrant (local folder, no Docker needed) |
| **Embeddings** | SentenceTransformers `all-MiniLM-L6-v2` |
| **Reranking** | Cross-Encoder `ms-marco-MiniLM-L-6-v2` |
| **LLM / Generation** | LangChain + Ollama (`llama3`) — local & free |
| **Document Parsing** | LangChain `RecursiveCharacterTextSplitter` |
| **Auth** | JWT Bearer Tokens (`python-jose`) |
| **Password Hashing** | `bcrypt` |
| **Testing** | `pytest` + `TestClient` |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10 or higher** → https://python.org/downloads
- **Git** → https://git-scm.com

Check your Python version:
```bash
python --version
```

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Shree-2004/financial-rag-api.git
cd financial-rag-api
```

---

### Step 2 — Create & Activate a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ First run downloads the embedding model (~90 MB) and reranker model (~70 MB). This is a **one-time download**.

---

### Step 4 — Configure Environment Variables

```bash
# Copy the example environment file
copy .env.example .env        # Windows
cp .env.example .env          # Mac/Linux
```

Open `.env` and set a secure `SECRET_KEY`:

```env
SECRET_KEY=replace-this-with-a-long-random-string-minimum-32-characters

# All other settings work out-of-the-box with defaults:
DATABASE_URL=sqlite:///./financial_dms.db
QDRANT_PATH=./qdrant_storage
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

---

### Step 5 — (Optional) Set Up Ollama for AI-Generated Answers

This enables the `POST /rag/query` endpoint (full LLM answers).
Skip this step if you only need semantic search.

1. Download Ollama: https://ollama.com/download
2. In a **new terminal**, run:
```bash
ollama pull llama3
ollama serve
```
3. Keep that terminal open while using the app.

---

### Step 6 — Start the Server

```bash
python -m uvicorn app.main:app --reload
```

You will see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

> **On first startup, the app automatically:**
> - Creates all database tables
> - Seeds 4 roles with permissions (Admin, Financial Analyst, Auditor, Client)
> - Creates a default admin user: **`admin` / `adminpass`**

---

### Step 7 — Open the App

| Interface | URL |
|---|---|
| **Web UI Dashboard** | http://127.0.0.1:8000 |
| **API Docs (Swagger)** | http://127.0.0.1:8000/docs |
| **API Docs (Redoc)** | http://127.0.0.1:8000/redoc |

**Login with:** Username: `admin` | Password: `adminpass`

---

## 🖥️ Using the Web UI

### Upload a Document
1. Go to http://127.0.0.1:8000 → Log in as admin
2. Fill in **Document Title**, **Company Name**, **Document Type**
3. Click **Choose File** → select a `.pdf` or `.txt` file
4. Click **Upload & Index** — the document is automatically embedded into Qdrant

### Semantic Search
- Type any financial question in the search box
- e.g. *"What is Apple's debt to equity ratio?"*
- Returns the top-5 most relevant chunks from all your documents

### Sample Documents
Ready-to-use test documents are in the `sample_docs/` folder:

| File | Company | Type |
|---|---|---|
| `apple_annual_report_2023.txt` | Apple Inc. | report |
| `tesla_q3_2023_earnings.txt` | Tesla Inc. | report |
| `global_tech_invoice_2023.txt` | Global Ltd | invoice |
| `nexgen_advisory_contract_2023.txt` | Nextgen Ltd | contract |

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login → returns JWT token |
| `GET` | `/auth/me` | Get current logged-in user info |

**Login Request:**
```json
POST /auth/login
{
  "username": "admin",
  "password": "adminpass"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

---

### Documents

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/documents/upload` | Upload a PDF or TXT file | Analyst, Admin |
| `GET` | `/documents` | List all documents (paginated) | All roles |
| `GET` | `/documents/search` | Filter by title, company, type | All roles |
| `GET` | `/documents/{document_id}` | Get single document | All roles |
| `PATCH` | `/documents/{document_id}` | Update title/company/type | Analyst, Admin |
| `DELETE` | `/documents/{document_id}` | Delete document + embeddings | Admin |

**Upload Example:**
```bash
curl -X POST http://127.0.0.1:8000/documents/upload \
  -H "Authorization: Bearer <your_token>" \
  -F "title=Q3 Report" \
  -F "company_name=Acme Corp" \
  -F "document_type=report" \
  -F "file=@report.pdf"
```

---

### RAG (Semantic Search & AI Q&A)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/rag/search` | Semantic search → Top-5 chunks (no LLM) |
| `POST` | `/rag/query` | Full RAG → LLM answer + source citations |
| `GET` | `/rag/context/{document_id}` | All stored chunks for a document |
| `POST` | `/rag/index-document` | Manually re-index a document |
| `DELETE` | `/rag/remove-document/{id}` | Remove document from Qdrant |
| `GET` | `/rag/audit-log` | Query history log (Admin only) |

**Semantic Search:**
```json
POST /rag/search
{ "query": "What is the debt to equity ratio?" }
```

**RAG Query (requires Ollama):**
```json
POST /rag/query
{ "query": "Summarize the key financial risks in the Tesla report." }
```

---

### Roles & Users (Admin Only)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/roles` | List all roles |
| `GET` | `/roles/{role_id}` | Get role details |
| `POST` | `/roles/create` | Create a custom role |
| `POST` | `/users/assign-role` | Assign a role to a user |
| `GET` | `/users/{id}/roles` | Get a user's roles |
| `GET` | `/users/{id}/permissions` | Get a user's permissions |

---

## 👥 Role-Based Access Control (RBAC)

| Permission | Admin | Financial Analyst | Auditor | Client |
|---|---|---|---|---|
| Upload Documents | ✅ | ✅ | ❌ | ❌ |
| Edit Documents | ✅ | ✅ | ❌ | ❌ |
| View ALL Documents | ✅ | ✅ | ✅ | ❌ |
| View Own Company Docs | ✅ | ✅ | ✅ | ✅ |
| Semantic Search | ✅ | ✅ | ✅ | ✅ (own company) |
| Delete Documents | ✅ | ❌ | ❌ | ❌ |
| Manage Roles & Users | ✅ | ❌ | ❌ | ❌ |
| View Audit Log | ✅ | ❌ | ❌ | ❌ |

### Multi-Tenant Isolation
A **Client** user from "Apple Inc." can only see and search documents where `company_name == "Apple Inc."`. Documents from other companies are completely hidden — even in search results.

---

## 🧪 Running Tests

```bash
python -m pytest tests/test_flow.py -v
```

Expected output:
```
tests/test_flow.py::TestFinancialDMS::test_e2e_flow PASSED   [100%]
1 passed in ~40s
```

The test covers the full end-to-end flow: register → login → upload → search → delete.

---

## 📁 Project Structure

```
financial-rag-api/
│
├── app/
│   ├── main.py              # FastAPI app entry point, DB seeding
│   ├── config.py            # Settings from .env
│   ├── database.py          # SQLAlchemy engine & session
│   │
│   ├── auth/                # Authentication (JWT, login, register)
│   ├── users/               # User & Role management, RBAC
│   ├── documents/           # Document upload, listing, CRUD
│   ├── rag/                 # Vector pipeline, LLM, audit log
│   │   ├── pipeline.py      # Qdrant embed/search/rerank logic
│   │   ├── llm.py           # LLM manager (Ollama/OpenAI/Gemini)
│   │   ├── router.py        # RAG API endpoints
│   │   └── models.py        # Audit log DB model
│   │
│   └── static/
│       └── index.html       # Full web UI (single file)
│
├── tests/
│   └── test_flow.py         # End-to-end integration test
│
├── sample_docs/             # Sample financial documents for testing
├── storage/                 # Uploaded files (gitignored)
├── qdrant_storage/          # Local vector DB (gitignored)
│
├── .env.example             # Environment variable template
├── .gitignore               # Excludes secrets, DB, venv
├── requirements.txt         # Python dependencies
└── README.md
```

---

## ⚙️ Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | JWT signing secret — change this! |
| `DATABASE_URL` | `sqlite:///./financial_dms.db` | Database connection string |
| `QDRANT_PATH` | `./qdrant_storage` | Local Qdrant storage folder |
| `LLM_PROVIDER` | `ollama` | LLM backend: `ollama`, `openai`, `gemini` |
| `LLM_MODEL` | `llama3` | Model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |

---

## 🔒 Security Notes

- Change the default admin password immediately in production
- Set a strong, unique `SECRET_KEY` in your `.env`
- Never commit your `.env` file — it is already in `.gitignore`
- For production, switch from SQLite to PostgreSQL
- Enable HTTPS in production using a reverse proxy (e.g., Nginx)

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 🙋 Author

**Shree Londhe**
GitHub: [Shree-2004](https://github.com/Shree-2004)
