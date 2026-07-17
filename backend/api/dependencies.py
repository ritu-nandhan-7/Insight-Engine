"""FastAPI dependencies for the API layer."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from backend.engine import InsightEngine

logger = logging.getLogger(__name__)

# Session-based engine storage for multi-user support
_sessions: dict[str, tuple[InsightEngine, float]] = {}
_SESSION_MAX_AGE_SECONDS = 3600
_CLEANUP_INTERVAL_SECONDS = 300
_last_cleanup = 0.0


def _cleanup_old_sessions() -> None:
    """Remove expired sessions."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL_SECONDS:
        return
    _last_cleanup = now
    expired = [sid for sid, (_, last_access) in _sessions.items()
               if now - last_access > _SESSION_MAX_AGE_SECONDS]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.info("Cleaned up %d expired sessions", len(expired))


def get_or_create_session(request: Request) -> InsightEngine:
    """Get or create an InsightEngine instance for the current session."""
    _cleanup_old_sessions()
    
    session_id = request.cookies.get("insight_engine_session")
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info("Created new session: %s", session_id)
    
    if session_id not in _sessions:
        engine = InsightEngine()
        _sessions[session_id] = (engine, time.time())
        logger.info("Created new InsightEngine for session: %s", session_id)
    else:
        engine, _ = _sessions[session_id]
        _sessions[session_id] = (engine, time.time())
    
    return engine


def get_engine() -> InsightEngine:
    """Legacy function for backward compatibility."""
    logger.warning("get_engine() called - using shared instance.")
    engine, _ = _sessions.get("_legacy_shared", (None, 0))
    if engine is None:
        engine = InsightEngine()
        _sessions["_legacy_shared"] = (engine, time.time())
    return engine
