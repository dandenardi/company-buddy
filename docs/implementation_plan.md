# 🚀 Plano de Implementação: De Naive RAG para Production-Ready RAG

Transformar o Company Buddy em um sistema RAG robusto e observável, eliminando as características "naive" identificadas na análise.

## User Review Required

> [!IMPORTANT] > **Abordagem Incremental**: Este plano está dividido em 5 fases que podem ser implementadas de forma independente. Você pode escolher começar por qualquer fase baseado nas suas prioridades de negócio.

> [!WARNING] > **Breaking Changes**:
>
> - Fase 2 (Chunking) pode requerer re-ingestão de todos os documentos existentes
> - Fase 3 (Busca Híbrida) pode alterar a ordem dos resultados retornados
> - Fase 4 (Contexto) muda a API do `/ask` para incluir session_id

**Qual fase você gostaria de priorizar?**

1. **Fase 1** (Observabilidade) - Recomendado para começar, sem breaking changes
2. **Fase 2** (Chunking) - Maior impacto na qualidade, mas requer re-ingestão
3. **Fase 3** (Recuperação) - Melhora relevância dos resultados
4. **Fase 4** (Contexto) - Habilita conversas naturais
5. **Fase 5** (Geração) - Melhora formato e confiabilidade das respostas

---

## Fase 1: Fundação - Observabilidade e Metadados Ricos

**Objetivo**: Sair do "voando no escuro" para ter visibilidade sobre qualidade e performance.

**Impacto**: 🟢 Sem breaking changes | ⏱️ 2-3 dias

### Backend

#### [MODIFY] [document_model.py](file:///c:/programming/company-buddy/backend/app/infrastructure/db/models/document_model.py)

Adicionar campos de metadata:

```python
# Novos campos
category = Column(String, nullable=True)  # "juridico", "rh", "tecnico"
language = Column(String, default="pt-BR")
page_count = Column(Integer, nullable=True)
content_hash = Column(String, unique=True, nullable=True)  # SHA256 do conteúdo
version = Column(Integer, default=1)
```

#### [NEW] [feedback_model.py](file:///c:/programming/company-buddy/backend/app/infrastructure/db/models/feedback_model.py)

Modelo para feedback do usuário:

```python
class FeedbackModel(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(Integer)  # 1 (👎) ou 5 (👍)
    comment = Column(Text, nullable=True)
    chunks_used = Column(JSON)  # IDs dos chunks retornados
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### [NEW] [query_log_model.py](file:///c:/programming/company-buddy/backend/app/infrastructure/db/models/query_log_model.py)

Logging de queries para analytics:

```python
class QueryLogModel(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    question = Column(Text, nullable=False)
    chunks_retrieved = Column(Integer)
    chunks_used = Column(JSON)
    avg_score = Column(Float)  # Score médio dos chunks
    response_time_ms = Column(Integer)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### [MODIFY] [qdrant_service.py](file:///c:/programming/company-buddy/backend/app/services/qdrant_service.py)

Enriquecer payload dos chunks:

```python
def upsert_chunks(
    self,
    tenant_id: int,
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]],
    document_metadata: Dict[str, Any] = None,  # NOVO
) -> None:
    metadata = document_metadata or {}

    for idx, (text, vector) in enumerate(zip(chunks, embeddings)):
        payload: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "document_id": document_id,
            "chunk_index": idx,
            "text": text,
            # Metadados ricos
            "document_name": metadata.get("filename"),
            "category": metadata.get("category"),
            "content_type": metadata.get("content_type"),
            "upload_date": metadata.get("upload_date"),
            "language": metadata.get("language", "pt-BR"),
            "page_number": metadata.get("page_number"),  # Se aplicável
        }
```

Retornar scores na busca:

```python
def search(self, tenant_id: int, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    # ... código existente ...

    hits: List[Dict[str, Any]] = []
    for scored_point in result.points:
        if scored_point.payload:
            hit = scored_point.payload.copy()
            hit["score"] = scored_point.score  # NOVO: incluir score
            hits.append(hit)

    return hits
```

#### [MODIFY] [ask.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py)

Adicionar logging e retornar scores:

```python
import time
from app.infrastructure.db.models.query_log_model import QueryLogModel

@router.post("", response_model=AskResponse)
def ask(...) -> AskResponse:
    start_time = time.time()

    # ... busca existente ...

    # Calcular métricas
    avg_score = sum(hit.get("score", 0) for hit in results) / len(results) if results else 0

    # Log da query
    query_log = QueryLogModel(
        tenant_id=tenant_id,
        user_id=current_user.id,
        question=question,
        chunks_retrieved=len(results),
        chunks_used=[h.get("document_id") for h in results],
        avg_score=avg_score,
        response_time_ms=int((time.time() - start_time) * 1000),
    )
    db.add(query_log)
    db.commit()

    # Incluir scores nas sources
    sources.append(
        SourceChunk(
            text=text,
            document_id=str(hit.get("document_id")),
            document_name=hit.get("document_name"),  # NOVO
            score=hit.get("score"),  # NOVO
        )
    )
```

#### [NEW] [feedback.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/feedback.py)

Endpoint para feedback:

```python
@router.post("/feedback")
def submit_feedback(
    question: str,
    answer: str,
    rating: int,  # 1 ou 5
    comment: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feedback = FeedbackModel(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        question=question,
        answer=answer,
        rating=rating,
        comment=comment,
    )
    db.add(feedback)
    db.commit()
    return {"status": "ok"}
```

---

### Frontend

#### [MODIFY] [AskResponse component](file:///c:/programming/company-buddy/frontend/src/components/chat/AskResponse.tsx)

Adicionar botões de feedback:

```tsx
function AskResponse({ answer, sources }: Props) {
  const [feedback, setFeedback] = useState<1 | 5 | null>(null);

  const handleFeedback = async (rating: 1 | 5) => {
    await fetch("/api/v1/feedback", {
      method: "POST",
      body: JSON.stringify({ question, answer, rating }),
    });
    setFeedback(rating);
  };

  return (
    <div>
      <p>{answer}</p>

      {/* Feedback buttons */}
      <div className="flex gap-2 mt-4">
        <button onClick={() => handleFeedback(5)}>
          👍 {feedback === 5 && "Obrigado!"}
        </button>
        <button onClick={() => handleFeedback(1)}>
          👎 {feedback === 1 && "Vamos melhorar!"}
        </button>
      </div>

      {/* Sources com scores */}
      <div className="mt-4">
        <h4>Fontes:</h4>
        {sources.map((src, i) => (
          <div key={i} className="border p-2">
            <p className="text-sm text-gray-600">
              {src.document_name} (relevância: {(src.score * 100).toFixed(0)}%)
            </p>
            <p className="text-xs">{src.text.substring(0, 100)}...</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### [NEW] [Analytics Dashboard](<file:///c:/programming/company-buddy/frontend/src/app/(protected)/analytics/page.tsx>)

Dashboard básico de métricas:

```tsx
export default function AnalyticsPage() {
  const { data } = useSWR("/api/v1/analytics/queries");

  return (
    <div>
      <h1>Analytics</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <h3>Total de Queries</h3>
          <p className="text-3xl">{data?.total_queries}</p>
        </Card>

        <Card>
          <h3>Satisfação Média</h3>
          <p className="text-3xl">{data?.avg_rating}%</p>
        </Card>

        <Card>
          <h3>Tempo Médio de Resposta</h3>
          <p className="text-3xl">{data?.avg_response_time}ms</p>
        </Card>
      </div>

      <div className="mt-8">
        <h2>Queries Mais Comuns</h2>
        <ul>
          {data?.top_queries.map((q) => (
            <li key={q.question}>
              {q.question} ({q.count}x)
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

## Fase 2: Chunking Inteligente

**Objetivo**: Melhorar qualidade dos chunks respeitando estrutura semântica.

**Impacto**: 🟡 Requer re-ingestão | ⏱️ 3-4 dias

### Backend

#### [MODIFY] [document_ingestion.py](file:///c:/programming/company-buddy/backend/app/services/document_ingestion.py)

Substituir `chunk_text` por chunking semântico:

```python
from typing import List, Tuple
import hashlib

def chunk_text_semantic(
    text: str,
    max_chars: int = 1000,
    overlap_chars: int = 200,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunking semântico com overlap e metadados.
    Retorna: List[(chunk_text, metadata)]
    """
    # 1. Detectar estrutura (títulos, parágrafos)
    sections = detect_sections(text)

    chunks_with_metadata = []

    for section in sections:
        # 2. Quebrar seção em chunks com overlap
        section_chunks = split_with_overlap(
            section["text"],
            max_chars=max_chars,
            overlap=overlap_chars,
        )

        for i, chunk_text in enumerate(section_chunks):
            metadata = {
                "section_title": section.get("title"),
                "chunk_hash": hashlib.sha256(chunk_text.encode()).hexdigest(),
                "has_overlap": i > 0,  # Indica se tem overlap com anterior
            }
            chunks_with_metadata.append((chunk_text, metadata))

    return chunks_with_metadata

def detect_sections(text: str) -> List[Dict[str, Any]]:
    """Detecta títulos e seções no texto."""
    lines = text.split("\n")
    sections = []
    current_section = {"title": None, "text": ""}

    for line in lines:
        # Heurística: linha curta + maiúsculas = título
        if len(line) < 100 and line.isupper():
            if current_section["text"]:
                sections.append(current_section)
            current_section = {"title": line.strip(), "text": ""}
        else:
            current_section["text"] += line + "\n"

    if current_section["text"]:
        sections.append(current_section)

    return sections

def split_with_overlap(text: str, max_chars: int, overlap: int) -> List[str]:
    """Quebra texto com overlap entre chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]

        # Tenta quebrar em final de sentença
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > max_chars * 0.7:  # Pelo menos 70% do chunk
                end = start + last_period + 1
                chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap  # Overlap

    return chunks
```

Implementar deduplicação:

```python
def deduplicate_chunks(
    chunks_with_metadata: List[Tuple[str, Dict]],
    db: Session,
    tenant_id: int,
) -> List[Tuple[str, Dict]]:
    """Remove chunks duplicados baseado em hash."""
    unique_chunks = []
    seen_hashes = set()

    # Buscar hashes existentes no banco
    existing_hashes = db.query(ChunkHashModel.content_hash).filter(
        ChunkHashModel.tenant_id == tenant_id
    ).all()
    seen_hashes.update(h[0] for h in existing_hashes)

    for chunk_text, metadata in chunks_with_metadata:
        chunk_hash = metadata["chunk_hash"]
        if chunk_hash not in seen_hashes:
            unique_chunks.append((chunk_text, metadata))
            seen_hashes.add(chunk_hash)

    return unique_chunks
```

#### [NEW] [chunk_hash_model.py](file:///c:/programming/company-buddy/backend/app/infrastructure/db/models/chunk_hash_model.py)

Tabela para tracking de hashes:

```python
class ChunkHashModel(Base):
    __tablename__ = "chunk_hashes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    content_hash = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Fase 3: Recuperação Avançada (Reranking + Híbrido)

**Objetivo**: Melhorar relevância dos resultados com reranking e busca híbrida.

**Impacto**: 🟢 Sem breaking changes | ⏱️ 4-5 dias

### Backend

#### [NEW] [reranker_service.py](file:///c:/programming/company-buddy/backend/app/services/reranker_service.py)

Serviço de reranking usando modelo cross-encoder:

```python
from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self):
        # Modelo multilíngue para português
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Reordena chunks por relevância usando cross-encoder."""
        if not chunks:
            return []

        # Pares (query, chunk_text)
        pairs = [(query, chunk["text"]) for chunk in chunks]

        # Scores do cross-encoder
        scores = self.model.predict(pairs)

        # Adicionar scores e reordenar
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        # Ordenar por rerank_score
        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        return reranked[:top_k]
```

#### [MODIFY] [qdrant_service.py](file:///c:/programming/company-buddy/backend/app/services/qdrant_service.py)

Adicionar busca híbrida (BM25 + Vetorial):

```python
def hybrid_search(
    self,
    tenant_id: int,
    query_text: str,
    limit: int = 10,  # Buscar mais para reranking
    alpha: float = 0.5,  # 0.5 = 50% vetorial, 50% BM25
) -> List[Dict[str, Any]]:
    """
    Busca híbrida combinando vetorial e BM25.
    alpha=1.0: apenas vetorial
    alpha=0.0: apenas BM25
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

    # Busca híbrida usando Qdrant Fusion
    result = self.client.query_points(
        collection_name=self.collection_name,
        prefetch=[
            # Prefetch vetorial
            qmodels.Prefetch(
                query=query_vector,
                limit=limit,
            ),
            # Prefetch BM25
            qmodels.Prefetch(
                query=qmodels.Query(text=query_text),
                using="text",  # Requer índice BM25
                limit=limit,
            ),
        ],
        query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),  # Reciprocal Rank Fusion
        query_filter=flt,
        limit=limit,
        with_payload=True,
    )

    hits = []
    for scored_point in result.points:
        if scored_point.payload:
            hit = scored_point.payload.copy()
            hit["score"] = scored_point.score
            hits.append(hit)

    return hits
```

Criar índice BM25:

```python
def _ensure_collection(self) -> None:
    # ... código existente ...

    # Criar índice BM25 para busca textual
    self.client.create_payload_index(
        collection_name=self.collection_name,
        field_name="text",
        field_schema=qmodels.TextIndexParams(
            type="text",
            tokenizer=qmodels.TokenizerType.MULTILINGUAL,  # Suporte a PT
        ),
    )
```

#### [MODIFY] [ask.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py)

Integrar reranking:

```python
from app.services.reranker_service import RerankerService

@router.post("", response_model=AskResponse)
def ask(...) -> AskResponse:
    # 1) Busca híbrida (retorna mais resultados)
    qdrant = QdrantService()
    results = qdrant.hybrid_search(
        tenant_id=tenant_id,
        query_text=question,
        limit=payload.top_k * 2,  # Buscar 2x para reranking
    )

    # 2) Reranking
    reranker = RerankerService()
    reranked_results = reranker.rerank(
        query=question,
        chunks=results,
        top_k=payload.top_k,
    )

    # 3) Score threshold (descartar chunks irrelevantes)
    MIN_SCORE = 0.3
    filtered_results = [
        r for r in reranked_results
        if r.get("rerank_score", 0) >= MIN_SCORE
    ]

    # ... resto do código ...
```

Implementar K adaptativo:

```python
def adaptive_top_k(query: str, default_k: int = 5) -> int:
    """Ajusta K baseado no tipo de pergunta."""
    query_lower = query.lower()

    # Perguntas simples = menos chunks
    if any(word in query_lower for word in ["o que é", "quem é", "quando"]):
        return 3

    # Perguntas complexas = mais chunks
    if any(word in query_lower for word in ["compare", "diferença", "todos", "liste"]):
        return 10

    # Perguntas de procedimento = médio
    if any(word in query_lower for word in ["como", "passo a passo", "processo"]):
        return 7

    return default_k

# No endpoint:
top_k = adaptive_top_k(question, default_k=payload.top_k)
```

---

## Fase 4: Contexto Conversacional

**Objetivo**: Habilitar conversas naturais com memória de contexto.

**Impacto**: 🟡 Muda API (adiciona session_id) | ⏱️ 3-4 dias

### Backend

#### [NEW] [conversation_model.py](file:///c:/programming/company-buddy/backend/app/infrastructure/db/models/conversation_model.py)

Modelos para sessões e mensagens:

```python
class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=True)  # Auto-gerado do primeiro turno
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    messages = relationship("MessageModel", back_populates="conversation")

class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # "user" ou "assistant"
    content = Column(Text)
    chunks_used = Column(JSON, nullable=True)  # Para mensagens do assistant
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ConversationModel", back_populates="messages")
```

#### [NEW] [query_rewriter.py](file:///c:/programming/company-buddy/backend/app/services/query_rewriter.py)

Serviço para reescrever queries com contexto:

```python
class QueryRewriter:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def rewrite_with_context(
        self,
        current_query: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Reescreve query standalone usando histórico."""
        if not conversation_history:
            return current_query

        # Últimos 3 turnos
        recent_history = conversation_history[-6:]  # 3 pares user/assistant

        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in recent_history
        ])

        prompt = f"""Dado o histórico de conversa abaixo, reescreva a última pergunta do usuário para que ela seja autocontida e possa ser entendida sem o contexto anterior.

Histórico:
{history_text}

Pergunta atual: {current_query}

Pergunta reescrita (mantenha em português, seja conciso):"""

        rewritten = self.llm.model.generate_content(prompt).text.strip()
        return rewritten
```

#### [MODIFY] [ask.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py)

Adicionar suporte a conversação:

```python
class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    conversation_id: Optional[int] = None  # NOVO

@router.post("", response_model=AskResponse)
def ask(...) -> AskResponse:
    # 1) Buscar ou criar conversação
    if payload.conversation_id:
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == payload.conversation_id,
            ConversationModel.tenant_id == tenant_id,
        ).first()
        if not conversation:
            raise HTTPException(404, "Conversation not found")
    else:
        conversation = ConversationModel(
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        db.add(conversation)
        db.commit()

    # 2) Buscar histórico
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation.messages[-6:]  # Últimos 3 turnos
    ]

    # 3) Reescrever query com contexto
    query_rewriter = QueryRewriter(llm)
    standalone_query = query_rewriter.rewrite_with_context(
        current_query=question,
        conversation_history=history,
    )

    logger.info(f"Query original: {question}")
    logger.info(f"Query reescrita: {standalone_query}")

    # 4) Buscar com query reescrita
    results = qdrant.hybrid_search(
        tenant_id=tenant_id,
        query_text=standalone_query,  # Usar query reescrita
        limit=payload.top_k * 2,
    )

    # ... reranking e geração ...

    # 5) Salvar mensagens
    user_msg = MessageModel(
        conversation_id=conversation.id,
        role="user",
        content=question,
    )
    assistant_msg = MessageModel(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        chunks_used=[s.document_id for s in sources],
    )
    db.add_all([user_msg, assistant_msg])
    db.commit()

    return AskResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation.id,  # NOVO
    )
```

---

### Frontend

#### [MODIFY] [Chat component](file:///c:/programming/company-buddy/frontend/src/components/chat/Chat.tsx)

Gerenciar sessão de conversa:

```tsx
function Chat() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const handleAsk = async (question: string) => {
    const response = await fetch("/api/v1/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        conversation_id: conversationId, // Manter sessão
      }),
    });

    const data = await response.json();

    // Atualizar conversationId se for novo
    if (!conversationId) {
      setConversationId(data.conversation_id);
    }

    setMessages([
      ...messages,
      { role: "user", content: question },
      { role: "assistant", content: data.answer, sources: data.sources },
    ]);
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages([]);
  };

  return (
    <div>
      <button onClick={startNewConversation}>Nova Conversa</button>

      <MessageList messages={messages} />
      <ChatInput onSend={handleAsk} />
    </div>
  );
}
```

---

## Fase 5: Geração Melhorada

**Objetivo**: Respostas mais confiáveis com citações e validação.

**Impacto**: 🟢 Sem breaking changes | ⏱️ 2-3 dias

### Backend

#### [MODIFY] [llm_service.py](file:///c:/programming/company-buddy/backend/app/services/llm_service.py)

Prompt com citação obrigatória:

```python
def answer_with_context_and_citations(
    self,
    question: str,
    context_chunks: Sequence[Dict[str, Any]],  # Agora recebe dicts com metadata
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Retorna resposta + citações."""

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

    response = self.model.generate_content(prompt)
    answer_text = self._extract_text_from_response(response)

    # Extrair citações
    citations = extract_citations(answer_text)

    return {
        "answer": answer_text,
        "citations": citations,  # [1, 2, 3]
        "has_answer": not is_no_answer_response(answer_text),
    }

def extract_citations(text: str) -> List[int]:
    """Extrai números de citações [N] do texto."""
    import re
    matches = re.findall(r'\[(\d+)\]', text)
    return sorted(set(int(m) for m in matches))

def is_no_answer_response(text: str) -> bool:
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
```

#### [MODIFY] [ask.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py)

Usar novo método com citações:

```python
# Passar chunks completos (com metadata) para o LLM
result = llm.answer_with_context_and_citations(
    question=question,
    context_chunks=filtered_results,  # Lista de dicts
    system_prompt=tenant_prompt,
)

answer = result["answer"]
citations = result["citations"]
has_answer = result["has_answer"]

# Marcar chunks citados
for i, source in enumerate(sources):
    source.cited = (i + 1) in citations  # NOVO campo

return AskResponse(
    answer=answer,
    sources=sources,
    has_answer=has_answer,  # NOVO
    citations=citations,  # NOVO
)
```

---

## Verification Plan

### Automated Tests

**Fase 1 - Observabilidade**:

```bash
# Testar logging de queries
pytest tests/test_query_logging.py

# Testar feedback
pytest tests/test_feedback.py

# Verificar metadados no Qdrant
python scripts/verify_metadata.py
```

**Fase 2 - Chunking**:

```bash
# Testar chunking semântico
pytest tests/test_semantic_chunking.py

# Testar deduplicação
pytest tests/test_deduplication.py

# Re-ingerir documentos de teste
python scripts/reingest_documents.py --test
```

**Fase 3 - Recuperação**:

```bash
# Testar reranking
pytest tests/test_reranker.py

# Testar busca híbrida
pytest tests/test_hybrid_search.py

# Comparar relevância antes/depois
python scripts/compare_retrieval_quality.py
```

**Fase 4 - Contexto**:

```bash
# Testar reescrita de query
pytest tests/test_query_rewriter.py

# Testar sessões
pytest tests/test_conversations.py
```

**Fase 5 - Geração**:

```bash
# Testar extração de citações
pytest tests/test_citations.py

# Testar detecção de "não sei"
pytest tests/test_no_answer_detection.py
```

### Manual Verification

**Fase 1**: Verificar dashboard de analytics mostrando métricas corretas

**Fase 2**: Comparar qualidade dos chunks antes/depois da re-ingestão

**Fase 3**: Testar queries e verificar se resultados são mais relevantes

**Fase 4**: Testar conversas multi-turno (follow-up questions)

**Fase 5**: Verificar se respostas incluem citações [N] corretas

---

## 📊 Métricas de Sucesso

Após implementação completa, você deve observar:

| Métrica                   | Antes (Naive)    | Depois (Production) |
| ------------------------- | ---------------- | ------------------- |
| **Satisfação do usuário** | ? (sem dados)    | > 80% 👍            |
| **Chunks relevantes**     | ~40%             | > 70%               |
| **Tempo de resposta**     | ~2-3s            | < 2s                |
| **Alucinações**           | ? (sem tracking) | < 5%                |
| **Follow-up questions**   | ❌ Não funciona  | ✅ Funciona         |
| **Citações de fonte**     | ❌ Nunca         | ✅ Sempre           |

---

## 🎯 Próximos Passos

1. **Revisar este plano** e decidir qual fase priorizar
2. **Criar branch** para desenvolvimento (`feature/production-rag`)
3. **Implementar Fase 1** (recomendado começar aqui)
4. **Validar com usuários reais** antes de prosseguir
5. **Iterar** baseado em feedback e métricas

---

## 📚 Dependências Adicionais

Adicionar ao `requirements.txt`:

```txt
# Fase 2 - Chunking
langchain-text-splitters>=0.0.1

# Fase 3 - Reranking
sentence-transformers>=2.2.0
```

Adicionar ao `package.json` (frontend):

```json
{
  "dependencies": {
    "recharts": "^2.10.0" // Para gráficos no analytics
  }
}
```
