"""
Query Rewriter Service for Phase 4

Rewrites follow-up questions into standalone queries using conversation context.
This enables the system to understand references like "E para estagiários?" after
a question about vacation policy.
"""

import logging
from typing import List, Dict, Optional
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class QueryRewriterService:
    """
    Rewrites queries to be standalone using conversation history.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize query rewriter.
        
        Args:
            llm_service: LLM service for rewriting (uses Gemini)
        """
        self.llm = llm_service or LLMService()
    
    def rewrite_with_context(
        self,
        current_query: str,
        conversation_history: List[Dict[str, str]],
        max_history_turns: int = 3,
    ) -> str:
        """
        Rewrite query to be standalone using conversation history.
        
        Args:
            current_query: Current user question
            conversation_history: List of {"role": "user"|"assistant", "content": "..."}
            max_history_turns: Maximum number of previous turns to consider
        
        Returns:
            Standalone query that can be understood without context
        """
        # If no history, return query as-is
        if not conversation_history:
            logger.info("[QUERY_REWRITER] No history, using original query")
            return current_query
        
        # Check if query looks like a follow-up (short, has pronouns, etc.)
        if not self._is_followup_question(current_query):
            logger.info("[QUERY_REWRITER] Not a follow-up, using original query")
            return current_query
        
        # Get recent history (last N turns)
        recent_history = conversation_history[-max_history_turns * 2:]  # *2 for user+assistant pairs
        
        # Build history text
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in recent_history
        ])
        
        # Rewrite using LLM
        prompt = f"""Dado o histórico de conversa abaixo, reescreva a última pergunta do usuário para que ela seja autocontida e possa ser entendida sem o contexto anterior.

HISTÓRICO:
{history_text}

PERGUNTA ATUAL: {current_query}

INSTRUÇÕES:
- Reescreva a pergunta para ser autocontida
- Mantenha em português brasileiro
- Seja conciso
- Não adicione informações que não estão no contexto
- Se a pergunta já é autocontida, retorne ela como está

PERGUNTA REESCRITA:"""
        
        try:
            # Updated to use generate_raw from LLMService which handles the new SDK client
            rewritten = self.llm.generate_raw(prompt)
            rewritten = rewritten.strip()
            
            if rewritten and len(rewritten) > 5:
                logger.info(
                    f"[QUERY_REWRITER] Original: '{current_query}' -> "
                    f"Rewritten: '{rewritten}'"
                )
                return rewritten
            else:
                logger.warning("[QUERY_REWRITER] Empty rewrite, using original")
                return current_query
                
        except Exception as e:
            logger.error(f"[QUERY_REWRITER] Error rewriting query: {e}")
            return current_query
    
    def _is_followup_question(self, query: str) -> bool:
        """
        Detect if query is likely a follow-up question.
        
        Heuristics:
        - Short queries (< 10 words)
        - Contains pronouns (ele, ela, isso, este, etc.)
        - Starts with "E" (and)
        - Contains "também" (also)
        """
        query_lower = query.lower().strip()
        word_count = len(query_lower.split())
        
        # Very short queries are likely follow-ups
        if word_count <= 5:
            return True
        
        # Check for pronouns and connectors
        followup_indicators = [
            r'\b(ele|ela|isso|este|esta|esse|essa|aquele|aquela)\b',
            r'^e\s',  # Starts with "E "
            r'\btambém\b',
            r'\bmesmo\b',
            r'\baqui\b',
            r'\blá\b',
        ]
        
        import re
        for pattern in followup_indicators:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def _extract_text(self, response) -> str:
        """Extract text from Gemini response."""
        try:
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except ValueError:
            pass
        
        # Fallback: extract from candidates
        try:
            for candidate in getattr(response, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    for part in parts:
                        part_text = getattr(part, "text", None)
                        if part_text:
                            return part_text.strip()
        except Exception:
            pass
        
        return ""


# Singleton instance
_rewriter_instance = None


def get_query_rewriter(llm_service: Optional[LLMService] = None) -> QueryRewriterService:
    """Get or create query rewriter instance."""
    global _rewriter_instance
    if _rewriter_instance is None:
        _rewriter_instance = QueryRewriterService(llm_service)
    return _rewriter_instance
