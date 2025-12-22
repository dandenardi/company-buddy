import logging
from typing import List, Any

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("company_buddy.embedding")


class EmbeddingService:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "text-embedding-004", # Atualizado para modelo mais recente sugerido
        output_dimensionality: int = 768,
    ) -> None:
        key = api_key or settings.google_api_key
        if not key:
            raise RuntimeError("GOOGLE_API_KEY não configurada para embeddings.")

        self.client = genai.Client(api_key=key)
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para uma lista de textos.
        Uses new SDK: client.models.embed_content
        """
        vectors: List[List[float]] = []

        # O novo SDK suporta batching? Vamos manter 1 por 1 por segurança ou tentar batch.
        # client.models.embed_content aceita 'contents' que pode ser string ou list of parts.
        # Mas para multiple inputs geralmente se usa batch calls.
        # Vamos manter o loop safe por enquanto.
        
        for idx, text in enumerate(texts):
            clean_text = text.strip()
            if not clean_text:
                logger.warning(
                    f"[EMBEDDING] Texto vazio no índice {idx}, retornando vetor vazio."
                )
                vectors.append([])
                continue

            try:
                # New SDK call
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=clean_text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.output_dimensionality,
                    )
                )
                
                # Verify response structure
                # response.embeddings -> list of EmbedContentResponse? Or single?
                # For single content, it usually has .embedding object.
                # Let's check attributes safely.
                
                embedding_values = None
                if hasattr(response, "embedding") and response.embedding:
                     embedding_values = response.embedding.values
                
                if embedding_values:
                    vectors.append([float(v) for v in embedding_values])
                else:
                    logger.error(f"[EMBEDDING] Embed vazio para doc {idx}")
                    vectors.append([])

            except Exception as exc:
                logger.exception(
                    f"[EMBEDDING] Erro ao chamar Gemini embeddings para índice {idx}: {exc}"
                )
                raise

        return vectors
