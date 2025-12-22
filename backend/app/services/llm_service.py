from __future__ import annotations

import json
import logging
import re
from typing import List, Dict, Any, Optional, Sequence

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    pass


class LLMService:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.3,
    ) -> None:
        key = api_key or settings.google_api_key
        if not key:
            raise RuntimeError("GOOGLE_API_KEY não configurada.")

        # Initialize the new Client
        self.client = genai.Client(api_key=key)
        self.model_name = model_name
        self.temperature = temperature

    def answer_with_context_and_citations(
        self,
        question: str,
        context_chunks: Sequence[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Gera resposta com citações obrigatórias e histórico de conversa.
        """
        # Numerar chunks
        numbered_context = "\n\n".join([
            f"[{i+1}] {chunk['text']}\n(Fonte: {chunk.get('document_name', 'Desconhecido')})"
            for i, chunk in enumerate(context_chunks)
        ])
        
        base_prompt = system_prompt or (
            "Você é um assistente interno de uma empresa. "
            "Responda SEMPRE em português brasileiro, de forma clara e objetiva.\n\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "1. Use APENAS as informações dos trechos numerados abaixo\n"
            "2. Cite os números dos trechos que você usou (ex: [1], [2])\n"
            "3. Se a resposta não estiver nos trechos, responda EXATAMENTE:\n"
            "   'Não encontrei essa informação nos documentos disponíveis. "
            "   Sugiro adicionar documentos relacionados ou reformular a pergunta.'\n"
            "4. NÃO invente informações\n"
            "5. NÃO use conhecimento externo\n"
        )
        
        history_text = ""
        if chat_history:
            history_text = "HISTÓRICO DA CONVERSA:\n"
            for msg in chat_history:
                role = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                history_text += f"{role}: {msg['content']}\n"
            history_text += "\n"
        
        prompt = (
            f"{base_prompt}\n\n"
            f"TRECHOS:\n{numbered_context}\n\n"
            f"{history_text}"
            f"PERGUNTA ATUAL:\n{question}\n\n"
            f"RESPOSTA (com citações [N]):"
        )

        try:
            # New SDK call structure
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "answer": {"type": "STRING"},
                            "citations": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"}
                            },
                            "has_answer": {"type": "BOOLEAN"}
                        },
                        "required": ["answer", "citations", "has_answer"]
                    }
                )
            )
            
            # For JSON response with schema, parsing is often automatic if we use parsed=True?
            # Or we get text and parse it.
            # Using response.text for now as it's reliable.
            text_resp = response.text
            if not text_resp:
                raise LLMServiceError("Resposta vazia do LLM.")

            # New SDK usually returns pure JSON if mime_type is json.
            data = json.loads(text_resp)
            return data

        except Exception as error:
            logger.exception("Erro ao chamar Gemini: %s", error)
            # Fallback handling or re-raise
            raise LLMServiceError(f"Falha ao chamar o modelo de linguagem: {error}")

    def generate_raw(self, prompt: str) -> str:
        """Helper for simple generation (used by QueryRewriter)."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                )
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Generate raw error: {e}")
            return ""


# Dependency para usar com Depends(get_llm_service)
_llm_service_singleton: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service_singleton
    if _llm_service_singleton is None:
        _llm_service_singleton = LLMService()
    return _llm_service_singleton
