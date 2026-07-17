"""Dependency readiness endpoint for the ChoreTracker API."""

from fastapi import APIRouter, Response, status

from app.db.session import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/readiness")
def readiness_check(response: Response) -> dict[str, str]:
    """Confirm that required application dependencies are available."""

    if not check_database_connection():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "unavailable",
            "database": "unavailable",
        }

    return {
        "status": "ready",
        "database": "available",
    }
