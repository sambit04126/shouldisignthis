from google.adk.sessions import DatabaseSessionService

# SETUP SESSION SERVICE & DB
DB_URL = "sqlite:///contract_auditor.db"
session_service = DatabaseSessionService(db_url=DB_URL)
