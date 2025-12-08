# app/services/llm_service.py

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence

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

    def answer_with_context_and_citations(
        self,
        question: str,
        context_chunks: Sequence[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Gera resposta com citações obrigatórias.
        
        Args:
            question: Pergunta do usuário
            context_chunks: Lista de dicts com 'text' e metadados (document_name, etc)
            system_prompt: Prompt customizado do tenant (opcional)
        
        Returns:
            {
                "answer": str,           # Resposta com citações [N]
                "citations": List[int],  # Números citados [1, 2, 3]
                "has_answer": bool,      # False se resposta for "não sei"
            }
        """
        # Numerar chunks para citação
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
        
        prompt = (
            f"{base_prompt}\n\n"
            f"TRECHOS:\n{numbered_context}\n\n"
            f"PERGUNTA:\n{question}\n\n"
            f"RESPOSTA (com citações [N]):"
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
        
        # Extrair citações
        citations = self._extract_citations(answer_text)
        
        # Detectar "não sei"
        has_answer = not self._is_no_answer_response(answer_text)
        
        return {
            "answer": answer_text,
            "citations": citations,
            "has_answer": has_answer,
        }

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

    @staticmethod
    def _extract_citations(text: str) -> List[int]:
        """Extrai números de citações [N] do texto."""
        matches = re.findall(r'\[(\d+)\]', text)
        return sorted(set(int(m) for m in matches))

    @staticmethod
    def _is_no_answer_response(text: str) -> bool:
        """Detecta se a resposta é 'não sei'."""
        no_answer_phrases = [
            "não encontrei",
            "não há informação",
            "não está disponível",
            "não consta",
            "sugiro adicionar documentos",
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in no_answer_phrases)


# Dependency para usar com Depends(get_llm_service)
_llm_service_singleton: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service_singleton  # noqa: PLW0603
    if _llm_service_singleton is None:
        _llm_service_singleton = LLMService()
    return _llm_service_singleton
