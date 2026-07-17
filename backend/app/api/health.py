"""Liveness endpoint for the ChoreTracker API."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the FastAPI process is running."""

    return {
        "status": "ok",
        "service": "choretracker",
    }
