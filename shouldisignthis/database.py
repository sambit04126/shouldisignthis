from google.adk.sessions import DatabaseSessionService

# SETUP SESSION SERVICE & DB
# NOTE: Using /tmp for SQLite on Cloud Run (Ephemeral storage).
# For production persistence, use Cloud SQL (PostgreSQL).
DB_URL = "sqlite+aiosqlite:////tmp/contract_auditor.db"

_session_service = None

def get_session_service():
    global _session_service
    if _session_service is None:
        _session_service = DatabaseSessionService(db_url=DB_URL)
    return _session_service
