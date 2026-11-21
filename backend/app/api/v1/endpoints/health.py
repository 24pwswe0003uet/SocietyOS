"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import DB

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: DB) -> dict:
    """Verify the API and database are running."""
    await db.execute(text("SELECT 1"))
    return {"status": "healthy", "service": "societyos-api"}
