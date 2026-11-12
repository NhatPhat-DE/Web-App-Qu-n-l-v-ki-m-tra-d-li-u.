from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Confirm the application is running; no database check is performed."""
    return {"status": "ok"}


@router.get("/health/db", responses={503: {"description": "Database unavailable"}})
def database_health() -> JSONResponse:
    if check_database():
        return JSONResponse({"status": "ok", "database": "ok"})
    return JSONResponse(
        {"status": "error", "database": "unavailable"}, status_code=503
    )
