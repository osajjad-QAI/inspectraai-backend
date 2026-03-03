from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "InspectraAI Backend API is running",
        "version": "1.0.0",
    }