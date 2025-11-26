from fastapi import APIRouter
from app.services.qdrant_service import QdrantService

router = APIRouter()

@router.get("/health")
def qdrant_health():
    client = QdrantService()
    collections = client.client.get_collections()
    return {
        "collections": [c.name for c in collections.collections]
    }