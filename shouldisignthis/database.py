from google.adk.sessions import DatabaseSessionService

# SETUP SESSION SERVICE & DB
# NOTE: Using /tmp for SQLite on Cloud Run (Ephemeral storage).
# For production persistence, use Cloud SQL (PostgreSQL).
DB_URL = "sqlite+aiosqlite:////tmp/contract_auditor.db"
session_service = DatabaseSessionService(db_url=DB_URL)
