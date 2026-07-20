"""Root entry point for Render deployment.

Render's Python runtime runs `uvicorn main:app` from the project root,
so this file re-exports the FastAPI app defined in backend/api/main.py.
"""

from backend.api.main import app