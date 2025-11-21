from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health", summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "message": "API is running",
    }
