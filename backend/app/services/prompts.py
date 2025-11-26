from typing import List


def build_rag_answer_prompt(question: str, chunks: List[str]) -> str:
    context_block = "\n\n---\n\n".join(chunks) if chunks else "Não há documentos relevantes."

    return f"""
Você é o assistente da empresa do usuário. Responda com clareza e objetividade usando SOMENTE os trechos abaixo:

CONTEXTOS:
{context_block}

PERGUNTA:
{question}

REGRAS:
- Não invente informação.
- Se a resposta não estiver nos documentos, diga explicitamente que não foi encontrada.
- Seja direto, em português, e útil.
""".strip()
