import logging
from typing import List, Any

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("company_buddy.embedding")


class EmbeddingService:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-embedding-001",  # ou "text-embedding-004" se estiver usando esse
        output_dimensionality: int = 768,
    ) -> None:
        key = api_key or settings.google_api_key
        if not key:
            raise RuntimeError("GOOGLE_API_KEY não configurada para embeddings.")

        genai.configure(api_key=key)
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality

    def _extract_values_from_response(self, resp: Any, idx: int) -> List[float]:
        """
        Extrai o vetor de embedding da resposta do Gemini
        cobrindo os formatos mais comuns.
        """
        if isinstance(resp, dict):
            embedding = resp.get("embedding")
        else:
            embedding = getattr(resp, "embedding", None)

        # Caso 1: embedding já é lista de floats
        if isinstance(embedding, list):
            return [float(v) for v in embedding]

        # Caso 2: embedding é objeto com .values
        if hasattr(embedding, "values"):
            return [float(v) for v in embedding.values]  # type: ignore[union-attr]

        # Caso 3: embedding é dict com "values"
        if isinstance(embedding, dict) and "values" in embedding:
            return [float(v) for v in embedding["values"]]

        logger.error(
            f"[EMBEDDING] Formato inesperado de resposta no índice {idx}: "
            f"resp={repr(resp)} embedding={repr(embedding)}"
        )
        raise RuntimeError("Unexpected response from Gemini (embedding format).")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Versão simples: 1 chamada por texto,
        forçando output_dimensionality para 768 (pra bater com o Qdrant).
        """
        vectors: List[List[float]] = []

        for idx, text in enumerate(texts):
            clean_text = text.strip()
            if not clean_text:
                logger.warning(
                    f"[EMBEDDING] Texto vazio no índice {idx}, retornando vetor vazio."
                )
                vectors.append([])
                continue

            try:
                resp = genai.embed_content(
                    model=self.model_name,
                    content=clean_text,
                    output_dimensionality=self.output_dimensionality,
                )
            except Exception as exc:
                logger.exception(
                    f"[EMBEDDING] Erro ao chamar Gemini embeddings para índice {idx}: {exc}"
                )
                raise

            vector = self._extract_values_from_response(resp, idx)
            vectors.append(vector)

        return vectors
