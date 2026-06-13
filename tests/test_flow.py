import os
import sys

# Override environment variables for isolated testing BEFORE importing the app
os.environ["DATABASE_URL"] = "sqlite:///./test_financial_dms.db"
os.environ["QDRANT_PATH"] = ":memory:"
os.environ["SECRET_KEY"] = "testsecretkeytestsecretkeytestsecretkey123"

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, seed_db
from app.database import Base, get_db
from app.auth.models import User
from app.users.models import Role, Permission
from app.documents.models import Document

class TestFinancialDMS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.database import engine
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
                
        # Initialize Test Client
        cls.client = TestClient(app)
        
        # Seed DB
        seed_db()
        
    @classmethod
    def tearDownClass(cls):
        from app.database import engine
        Base.metadata.drop_all(bind=engine)

    def test_e2e_flow(self):
        # 1. Register users with different roles
        print("\n--- 1. Registering Users ---")
        
        # Client 1: Acme Corp
        res = self.client.post("/auth/register", json={
            "username": "acme_client",
            "password": "acmepassword1",
            "company_name": "Acme Corp"
        })
        self.assertEqual(res.status_code, 201)
        acme_client_id = res.json()["id"]
        
        # Client 2: Beta Inc
        res = self.client.post("/auth/register", json={
            "username": "beta_client",
            "password": "betapassword1",
            "company_name": "Beta Inc"
        })
        self.assertEqual(res.status_code, 201)
        beta_client_id = res.json()["id"]
        
        # Analyst
        res = self.client.post("/auth/register", json={
            "username": "analyst_user",
            "password": "analystpassword1",
            "company_name": "Internal"
        })
        self.assertEqual(res.status_code, 201)
        analyst_id = res.json()["id"]
        
        # Auditor
        res = self.client.post("/auth/register", json={
            "username": "auditor_user",
            "password": "auditorpassword1",
            "company_name": "Internal"
        })
        self.assertEqual(res.status_code, 201)
        auditor_id = res.json()["id"]

        # 2. Login to get tokens
        print("--- 2. Logging In ---")
        # Admin
        res = self.client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
        self.assertEqual(res.status_code, 200)
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Acme Client
        res = self.client.post("/auth/login", json={"username": "acme_client", "password": "acmepassword1"})
        self.assertEqual(res.status_code, 200)
        acme_token = res.json()["access_token"]
        acme_headers = {"Authorization": f"Bearer {acme_token}"}
        
        # Beta Client
        res = self.client.post("/auth/login", json={"username": "beta_client", "password": "betapassword1"})
        self.assertEqual(res.status_code, 200)
        beta_token = res.json()["access_token"]
        beta_headers = {"Authorization": f"Bearer {beta_token}"}
        
        # Analyst
        res = self.client.post("/auth/login", json={"username": "analyst_user", "password": "analystpassword1"})
        self.assertEqual(res.status_code, 200)
        analyst_token = res.json()["access_token"]
        analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
        
        # Auditor
        res = self.client.post("/auth/login", json={"username": "auditor_user", "password": "auditorpassword1"})
        self.assertEqual(res.status_code, 200)
        auditor_token = res.json()["access_token"]
        auditor_headers = {"Authorization": f"Bearer {auditor_token}"}

        # 3. Assign correct roles using Admin account
        print("--- 3. Assigning Roles via RBAC Endpoints ---")
        # Assign Analyst
        res = self.client.post("/users/assign-role", json={"user_id": analyst_id, "role_name": "Financial Analyst"}, headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        
        # Assign Auditor
        res = self.client.post("/users/assign-role", json={"user_id": auditor_id, "role_name": "Auditor"}, headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        
        # Verify permissions of analyst
        res = self.client.get(f"/users/{analyst_id}/permissions", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        analyst_perms = res.json()["permissions"]
        self.assertIn("document:create", analyst_perms)
        
        # Verify permissions of auditor
        res = self.client.get(f"/users/{auditor_id}/permissions", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        auditor_perms = res.json()["permissions"]
        self.assertNotIn("document:create", auditor_perms)
        self.assertIn("document:read", auditor_perms)
        self.assertIn("document:read_all", auditor_perms)

        # 4. Upload document via Analyst (Analyst has upload permission)
        print("--- 4. Uploading Documents ---")
        
        # Prepare dummy txt content
        acme_doc_content = "Acme Corp Financial Report.\nAcme Corp has a high debt-to-equity ratio of 2.5, creating substantial financial risk. However, cash flows remain strong."
        beta_doc_content = "Beta Inc invoice details.\nBeta Inc has total invoice amount of $150,000 for technology services. The cash ratio is 1.8 which is extremely safe."
        
        # Upload Acme document
        acme_upload_files = {"file": ("acme_report.txt", acme_doc_content, "text/plain")}
        res = self.client.post("/documents/upload", data={
            "title": "Acme Q3 Report",
            "company_name": "Acme Corp",
            "document_type": "report"
        }, files=acme_upload_files, headers=analyst_headers)
        self.assertEqual(res.status_code, 201)
        acme_doc_id = res.json()["document_id"]
        
        # Upload Beta document
        beta_upload_files = {"file": ("beta_invoice.txt", beta_doc_content, "text/plain")}
        res = self.client.post("/documents/upload", data={
            "title": "Beta Q3 Invoice",
            "company_name": "Beta Inc",
            "document_type": "invoice"
        }, files=beta_upload_files, headers=analyst_headers)
        self.assertEqual(res.status_code, 201)
        beta_doc_id = res.json()["document_id"]

        # 5. Verify Client is blocked from uploading documents
        res = self.client.post("/documents/upload", data={
            "title": "Client Attempt",
            "company_name": "Acme Corp",
            "document_type": "report"
        }, files={"file": ("test.txt", "client content", "text/plain")}, headers=acme_headers)
        self.assertEqual(res.status_code, 403)  # Forbidden

        # 6. Test listing documents and isolation constraints
        print("--- 5. Verifying Multi-Tenant Document Listing ---")
        
        # Analyst should see all documents
        res = self.client.get("/documents", headers=analyst_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)
        
        # Auditor should see all documents
        res = self.client.get("/documents", headers=auditor_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)
        
        # Acme Client should ONLY see Acme Corp documents
        res = self.client.get("/documents", headers=acme_headers)
        self.assertEqual(res.status_code, 200)
        acme_docs = res.json()
        self.assertEqual(len(acme_docs), 1)
        self.assertEqual(acme_docs[0]["company_name"], "Acme Corp")
        
        # Beta Client should ONLY see Beta Inc documents
        res = self.client.get("/documents", headers=beta_headers)
        self.assertEqual(res.status_code, 200)
        beta_docs = res.json()
        self.assertEqual(len(beta_docs), 1)
        self.assertEqual(beta_docs[0]["company_name"], "Beta Inc")

        # 7. Test single document fetch and authorization
        print("--- 6. Verifying Document Access Control ---")
        
        # Acme Client can fetch Acme document
        res = self.client.get(f"/documents/{acme_doc_id}", headers=acme_headers)
        self.assertEqual(res.status_code, 200)
        
        # Acme Client CANNOT fetch Beta document
        res = self.client.get(f"/documents/{beta_doc_id}", headers=acme_headers)
        self.assertEqual(res.status_code, 403)

        # 8. Test metadata search and isolation
        print("--- 7. Verifying Metadata Search Filtering ---")
        # Admin searches for everything
        res = self.client.get("/documents/search?document_type=invoice", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["document_id"], beta_doc_id)
        
        # Acme Client searches for invoices - should get 0 because Beta's invoice is filtered out
        res = self.client.get("/documents/search?document_type=invoice", headers=acme_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 0)

        # 9. Test RAG Context and Semantic Search with Reranking
        print("--- 8. Verifying RAG Search & Reranking (Top 20 -> Cross-Encoder -> Top 5) ---")
        
        # Fetch related chunks (Context)
        res = self.client.get(f"/rag/context/{acme_doc_id}", headers=analyst_headers)
        self.assertEqual(res.status_code, 200)
        chunks = res.json()
        self.assertGreater(len(chunks), 0)
        self.assertIn("debt-to-equity ratio", chunks[0]["text"])
        
        # Acme client fetches Acme context
        res = self.client.get(f"/rag/context/{acme_doc_id}", headers=acme_headers)
        self.assertEqual(res.status_code, 200)
        
        # Acme client attempts to fetch Beta context - blocked
        res = self.client.get(f"/rag/context/{beta_doc_id}", headers=acme_headers)
        self.assertEqual(res.status_code, 403)
        
        # Semantic search for Analyst
        res = self.client.post("/rag/search", json={"query": "financial risk and debt ratio"}, headers=analyst_headers)
        self.assertEqual(res.status_code, 200)
        search_results = res.json()
        self.assertGreater(len(search_results), 0)
        # Check that top result is Acme because it has "debt-to-equity ratio" and "financial risk"
        self.assertEqual(search_results[0]["company_name"], "Acme Corp")
        
        # Semantic search for Acme Client - should return Acme result
        res = self.client.post("/rag/search", json={"query": "debt ratio financial risk"}, headers=acme_headers)
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.json()), 0)
        self.assertEqual(res.json()[0]["company_name"], "Acme Corp")
        
        # Semantic search for Beta Client - should NOT return Acme result
        res = self.client.post("/rag/search", json={"query": "debt ratio financial risk"}, headers=beta_headers)
        self.assertEqual(res.status_code, 200)
        # Beta Client doesn't have debt ratio info, should return nothing or only Beta chunks
        for item in res.json():
            self.assertEqual(item["company_name"], "Beta Inc")

        # 10. Delete document and verify cleanup
        print("--- 9. Verifying Document Deletion & Vector DB Clean-up ---")
        res = self.client.delete(f"/documents/{acme_doc_id}", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        
        # Verify metadata is deleted from SQL DB
        res = self.client.get(f"/documents/{acme_doc_id}", headers=admin_headers)
        self.assertEqual(res.status_code, 404)
        
        # Verify vector search no longer returns Acme
        res = self.client.post("/rag/search", json={"query": "debt ratio financial risk"}, headers=analyst_headers)
        self.assertEqual(res.status_code, 200)
        for item in res.json():
            self.assertNotEqual(item["company_name"], "Acme Corp")
            
        print("\nAll integration tests passed successfully!")

if __name__ == "__main__":
    unittest.main()
