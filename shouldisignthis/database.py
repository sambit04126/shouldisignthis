from google.adk.sessions import InMemorySessionService

# NOTE: Switched to InMemorySessionService for stability in demo/Cloud Run.
# SQLite in /tmp caused async/greenlet conflicts with the ADK library.
# Since /tmp is ephemeral anyway, in-memory storage is functionally equivalent for this demo.

_session_service = None

def get_session_service():
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
    return _session_service
