# app/services/llm_service.py

import google.generativeai as genai
from app.core.config import settings
from app.services.prompts import build_rag_answer_prompt  # se já criou esse helper


class LLMService:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ):
        key = api_key or settings.google_api_key
        if not key:
            raise RuntimeError("Google API key não configurada para LLM.")

        genai.configure(api_key=key)

        # 👉 Modelo padrão: bom, rápido e com free tier
        self.model_name = (
            model_name
            or getattr(settings, "gemini_model_name", None)
            or "gemini-2.5-flash"
        )

        # Pode deixar só o nome e passar config no generate_content,
        # ou já criar o objeto com config padrão.
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config={
                "temperature": 0.2,        # mais determinístico (bom pra RAG)
                "top_p": 0.9,
                "max_output_tokens": 512,  # limita custo + latência
            },
        )

    def answer_with_context(self, question: str, chunks: list[str]) -> str:
        prompt = build_rag_answer_prompt(question, chunks)

        resp = self.model.generate_content(prompt)

        text = getattr(resp, "text", None)

        # Fallback defensivo, caso a lib mude o shape da resposta
        if not text and hasattr(resp, "candidates"):
            candidates = resp.candidates or []
            if candidates and candidates[0].content and candidates[0].content.parts:
                maybe_text = getattr(candidates[0].content.parts[0], "text", None)
                if maybe_text:
                    text = maybe_text

        return text or "Não consegui gerar uma resposta com o modelo configurado."
