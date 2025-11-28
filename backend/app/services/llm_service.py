# app/services/llm_service.py

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from app.core.config import settings  # ajuste se seu settings tiver outro nome

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Erro de alto nível ao chamar o LLM."""


class LLMService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """
        Service simples para isolar chamadas ao Gemini.

        api_key: se None, usa settings.GOOGLE_API_KEY
        model_name: se None, usa "gemini-2.5-flash" ou o que você definir no settings
        """
        api_key = api_key or settings.google_api_key
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY não configurado.")

        model_name = model_name or getattr(settings, "GEMINI_MODEL_NAME", "gemini-2.5-flash")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def answer_with_context(self, question: str, context_chunks: Sequence[str], system_prompt: Optional[str] = None,) -> str:
        """
        Monta o prompt com contexto e retorna a resposta em texto.
        Levanta LLMServiceError se não conseguir produzir uma resposta útil.
        """
        context_text = "\n\n".join(context_chunks) if context_chunks else "Nenhum contexto foi encontrado."

        base_prompt = system_prompt or (
            "Você é um assistente interno de uma empresa. "
            "Responda sempre em português brasileiro, de forma clara e objetiva, "
            "usando apenas as informações fornecidas no contexto. "
            "Se não encontrar a resposta no contexto, diga que não sabe e sugira "
            "que o usuário adicione documentos relacionados."
        )   

        prompt = (
            f"{base_prompt}\n\n"
            f"Contexto:\n{context_text}\n\n"
            f"Pergunta do usuário:\n{question}\n\n"
            "Resposta:"
        )

        try:
            response: GenerateContentResponse = self.model.generate_content(prompt)
        except Exception as error:  # noqa: BLE001
            logger.exception("Erro ao chamar Gemini: %s", error)
            raise LLMServiceError("Falha ao chamar o modelo de linguagem.") from error

        answer_text = self._extract_text_from_response(response)
        if not answer_text:
            finish_reason = None
            try:
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
            except Exception:  # noqa: BLE001
                pass

            logger.error(
                "LLM não retornou texto. finish_reason=%s response=%r",
                finish_reason,
                response,
            )
            raise LLMServiceError(
                "O modelo não conseguiu gerar uma resposta para essa pergunta no momento."
            )

        return answer_text

    @staticmethod
    def _extract_text_from_response(response: GenerateContentResponse) -> Optional[str]:
        """
        Extrai texto de forma segura da resposta do Gemini.
        Tenta usar response.text, mas trata o ValueError e cai para leitura manual.
        """
        # 1. Tenta o atalho oficial (pode levantar ValueError no seu caso)
        try:
            if hasattr(response, "text") and response.text:
                return response.text
        except ValueError:
            # É exatamente o cenário do seu stacktrace (finish_reason = 2 etc.)
            pass

        # 2. Tenta extrair manualmente dos candidates/parts
        texts: List[str] = []
        try:
            for candidate in getattr(response, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if not parts:
                    continue

                for part in parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        texts.append(part_text)
        except Exception:  # noqa: BLE001
            return None

        if texts:
            return "\n".join(texts)

        return None


# Dependency para usar com Depends(get_llm_service)
_llm_service_singleton: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service_singleton  # noqa: PLW0603
    if _llm_service_singleton is None:
        _llm_service_singleton = LLMService()
    return _llm_service_singleton
