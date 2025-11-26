from typing import List, Dict, Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels  # pode manter assim
# alternativa equivalente seria: from qdrant_client import models as qmodels

from app.core.config import settings


class QdrantService:
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
    ):
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.client = QdrantClient(
            url=url or str(settings.qdrant_url),
            api_key=api_key or settings.qdrant_api_key,
        )

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """
        Garante que a coleção existe.
        Schema multi-tenant: um único collection com payloads (tenant_id, document_id, chunk_index).
        """
        collections = self.client.get_collections()
        existing_names = {c.name for c in collections.collections}

        if self.collection_name not in existing_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=768,  # depende do modelo de embedding
                    distance=qmodels.Distance.COSINE,
                ),
            )

        # índices de payload (idempotentes)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="tenant_id",
            field_schema=qmodels.PayloadSchemaType.INTEGER,
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.INTEGER,
        )

    def upsert_chunks(
        self,
        tenant_id: int,
        document_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> None:
        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError("Quantity of chunks and embeddings do not match.")

        points: List[qmodels.PointStruct] = []
        for idx, (text, vector) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid4())
            payload: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "document_id": document_id,
                "chunk_index": idx,
                "text": text,
            }
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def search(self, tenant_id: int, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Faz busca vetorial filtrada por tenant_id.
        Usa a Query API moderna: client.query_points(...)
        Retorna lista de payloads (cada payload = chunk relevante).
        """
        from app.services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        query_vector = embedding_service.embed_texts([query_text])[0]

        flt = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="tenant_id",
                    match=qmodels.MatchValue(value=tenant_id),
                )
            ]
        )

        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=flt,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        hits: List[Dict[str, Any]] = []
        for scored_point in result.points:
            if scored_point.payload:
                hits.append(scored_point.payload)

        return hits

    def delete_document(self, tenant_id: int, document_id: int) -> None:
        """
        Remove todos os pontos de um documento específico de um tenant.
        """
        flt = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="tenant_id",
                    match=qmodels.MatchValue(value=tenant_id),
                ),
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchValue(value=document_id),
                ),
            ]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(filter=flt),
        )
