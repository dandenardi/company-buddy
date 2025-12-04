# 🔍 Análise: Company Buddy é um "Naive RAG"?

## 📊 Resumo Executivo

**Veredito**: **Sim, o Company Buddy atual está na categoria "Naive RAG"** com alguns pontos positivos de multi-tenancy.

**Score Geral**: ⚠️ **6/7 categorias são "Naive"**

---

## 1️⃣ Ingestão / Chunking

### 🔹 Quebra de texto em chunks de tamanho fixo?

**Status**: ✅ **SIM - NAIVE**

**Evidência**: [document_ingestion.py:41-73](file:///c:/programming/company-buddy/backend/app/services/document_ingestion.py#L41-L73)

```python
def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """
    Chunk simples baseado em palavras, sem overlap, focado em segurança.
    """
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in words:
        word_len = len(word) + 1
        if current_length + word_len <= max_chars:
            current.append(word)
            current_length += word_len
        else:
            if current:
                chunks.append(" ".join(current))
            current = [word]
            current_length = word_len
```

**Problemas**:

- ❌ Tamanho fixo de 800 caracteres
- ❌ Não respeita títulos, seções ou estrutura semântica
- ❌ Não respeita parágrafos lógicos
- ❌ Não respeita listas ou tabelas
- ❌ Sem overlap entre chunks (pode perder contexto nas bordas)
- ❌ Quebra apenas por palavras (pode cortar no meio de uma ideia)

**O que falta**:

- Chunking semântico (por parágrafos, seções)
- Overlap configurável (ex: 10-20%)
- Detecção de estrutura (títulos, listas, tabelas)
- Chunking adaptativo baseado no tipo de documento

---

### 🔹 Sem deduplicação, versionamento ou metadados ricos?

**Status**: ✅ **SIM - NAIVE**

**Evidência**: [qdrant_service.py:55-89](file:///c:/programming/company-buddy/backend/app/services/qdrant_service.py#L55-L89)

```python
def upsert_chunks(
    self,
    tenant_id: int,
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]],
) -> None:
    points: List[qmodels.PointStruct] = []
    for idx, (text, vector) in enumerate(zip(chunks, embeddings)):
        point_id = str(uuid4())  # ⚠️ ID aleatório - sem deduplicação
        payload: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "document_id": document_id,
            "chunk_index": idx,
            "text": text,  # ⚠️ Metadados mínimos
        }
```

**Problemas**:

- ❌ Sem deduplicação por hash de conteúdo
- ❌ Sem controle de versões (se re-upload, cria duplicatas?)
- ❌ Metadados básicos: apenas `tenant_id`, `document_id`, `chunk_index`, `text`

**Metadados que faltam**:

- `document_name` / `filename`
- `content_type` / `mime_type`
- `upload_date` / `created_at`
- `section` / `page_number`
- `document_category` / `tags`
- `language`
- `author` / `department`
- `content_hash` (para deduplicação)
- `version`

**Ponto positivo**: ✅ Tem `tenant_id` (multi-tenancy)

---

## 2️⃣ Recuperação

### 🔹 Apenas top_k por similaridade vetorial, sem filtros, BM25 ou rerank?

**Status**: ✅ **SIM - BEM NAIVE**

**Evidência**: [qdrant_service.py:91-125](file:///c:/programming/company-buddy/backend/app/services/qdrant_service.py#L91-L125)

```python
def search(self, tenant_id: int, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Faz busca vetorial filtrada por tenant_id.
    """
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
        query_filter=flt,  # ⚠️ Apenas filtro de tenant
        limit=limit,       # ⚠️ K fixo
        with_payload=True,
        with_vectors=False,
    )
```

**Problemas**:

- ❌ Apenas busca vetorial pura (sem BM25 híbrido)
- ❌ Sem reranking
- ❌ Sem filtros adicionais por metadata (tipo de documento, data, categoria)
- ❌ Sem score threshold (retorna até chunks irrelevantes)
- ❌ Sem diversidade (pode retornar 5 chunks do mesmo parágrafo)

**Ponto positivo**: ✅ Filtra por `tenant_id` (isolamento multi-tenant)

---

### 🔹 K fixo para tudo?

**Status**: ✅ **SIM - NAIVE**

**Evidência**: [ask.py:22-24](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py#L22-L24)

```python
class AskRequest(BaseModel):
  question: str
  top_k: int = 5  # ⚠️ Default fixo
```

**Problemas**:

- ⚠️ K padrão de 5 para todas as perguntas
- ❌ Não adapta baseado no tipo de pergunta
- ❌ Não adapta baseado na complexidade da query

**O que falta**:

- K adaptativo (perguntas simples = menos chunks, complexas = mais)
- Score threshold dinâmico
- Lógica de "suficiência" (parar quando tiver contexto suficiente)

---

## 3️⃣ Geração / Resposta

### 🔹 Prompt genérico sem obrigatoriedade de citar fonte ou formato?

**Status**: ⚠️ **PARCIALMENTE NAIVE**

**Evidência**: [llm_service.py:41-61](file:///c:/programming/company-buddy/backend/app/services/llm_service.py#L41-L61)

```python
def answer_with_context(self, question: str, context_chunks: Sequence[str], system_prompt: Optional[str] = None,) -> str:
    context_text = "\n\n".join(context_chunks) if context_chunks else "Nenhum contexto foi encontrado."

    base_prompt = system_prompt or (
        "Você é um assistente interno de uma empresa. "
        "Responda sempre em português brasileiro, de forma clara e objetiva, "
        "usando apenas as informações fornecidas no contexto. "
        "Se não encontrar a resposta no contexto, diga que não sabe e sugira "
        "que o usuário adicione documentos relacionados."
    )
```

**Pontos positivos**:

- ✅ Instrui a usar apenas o contexto
- ✅ Instrui a dizer "não sei" quando não encontrar
- ✅ Suporte a `custom_prompt` por tenant ([ask.py:55-62](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py#L55-L62))

**Problemas**:

- ❌ Não obriga citação de fontes
- ❌ Não especifica formato de resposta
- ❌ Não instrui a identificar qual chunk usou
- ⚠️ Prompt genérico (mas tem customização por tenant)

---

### 🔹 Sem lógica clara de "não sei / não encontrado"?

**Status**: ✅ **NÃO - TEM LÓGICA** (ponto positivo!)

**Evidência**: [llm_service.py:48-54](file:///c:/programming/company-buddy/backend/app/services/llm_service.py#L48-L54)

```python
base_prompt = system_prompt or (
    "Você é um assistente interno de uma empresa. "
    "Responda sempre em português brasileiro, de forma clara e objetiva, "
    "usando apenas as informações fornecidas no contexto. "
    "Se não encontrar a resposta no contexto, diga que não sabe e sugira "
    "que o usuário adicione documentos relacionados."
)
```

**Ponto positivo**: ✅ Instrui explicitamente a dizer "não sei"

**Problema**: ⚠️ Depende do LLM seguir a instrução (não é validação programática)

---

## 4️⃣ Conversa e Contexto

### 🔹 Cada pergunta tratada isoladamente, sem memória ou reescrita de query?

**Status**: ✅ **SIM - NAIVE**

**Evidência**: [ask.py:39-71](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py#L39-L71)

```python
@router.post("", response_model=AskResponse)
def ask(
  payload: AskRequest,
  db: Session = Depends(get_db),
  current_user: UserModel = Depends(get_current_user),
  llm: LLMService = Depends(get_llm_service),
) -> AskResponse:
  # ...
  results = qdrant.search(
    tenant_id=tenant_id,
    query_text=question,  # ⚠️ Query direta, sem reescrita
    limit=payload.top_k,
  )
```

**Problemas**:

- ❌ Sem memória de conversação
- ❌ Sem histórico de turnos anteriores
- ❌ Sem reescrita de query com base no contexto
- ❌ Perguntas de follow-up não funcionam bem

**Exemplo de problema**:

```
User: "Qual a política de férias?"
Bot: "30 dias por ano..."
User: "E para estagiários?"  ⚠️ Não sabe que é sobre férias
```

---

## 5️⃣ Observabilidade / Qualidade

### 🔹 Sem métricas de relevância, satisfação, alucinação ou custo?

**Status**: ✅ **SIM - NAIVE DE PRODUÇÃO**

**Evidência**: Não há código de métricas, logging de qualidade ou feedback

**Problemas**:

- ❌ Sem métricas de relevância dos chunks retornados
- ❌ Sem feedback do usuário (👍/👎)
- ❌ Sem detecção de alucinação
- ❌ Sem tracking de custo por consulta
- ❌ Sem A/B testing de prompts
- ❌ Sem analytics de queries mais comuns

**Logging básico**: ✅ Tem logs de ingestão e erros, mas não de qualidade

---

## 6️⃣ Domínio / Especialização

### 🔹 Mesmo prompt e comportamento para todos os domínios?

**Status**: ⚠️ **PARCIALMENTE NAIVE**

**Evidência**: [ask.py:55-62](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py#L55-L62)

```python
# 0) Busca o tenant para pegar o custom_prompt (se existir)
tenant: TenantModel | None = (
  db.query(TenantModel)
  .filter(TenantModel.id == tenant_id)
  .first()
)

tenant_prompt = tenant.custom_prompt if tenant and tenant.custom_prompt else None
```

**Ponto positivo**: ✅ Suporte a `custom_prompt` por tenant

**Problemas**:

- ⚠️ Customização manual (não há templates por domínio)
- ❌ Sem especialização automática por tipo de documento
- ❌ Sem comportamento diferente para jurídico vs. técnico vs. atendimento

---

## 📈 Scorecard Final

| Categoria           | Status                                | Naive?     |
| ------------------- | ------------------------------------- | ---------- |
| **Chunking**        | Tamanho fixo, sem estrutura semântica | ✅ Sim     |
| **Metadados**       | Básicos, sem dedup/versão             | ✅ Sim     |
| **Recuperação**     | Apenas vetorial, sem BM25/rerank      | ✅ Sim     |
| **K adaptativo**    | K fixo (default 5)                    | ✅ Sim     |
| **Prompt**          | Genérico, mas customizável            | ⚠️ Parcial |
| **"Não sei"**       | Tem instrução                         | ❌ Não     |
| **Memória**         | Sem contexto de conversa              | ✅ Sim     |
| **Observabilidade** | Sem métricas de qualidade             | ✅ Sim     |
| **Especialização**  | Custom prompt por tenant              | ⚠️ Parcial |

**Total Naive**: 6/9 categorias

---

## 🎯 Pontos Fortes (não-naive)

1. ✅ **Multi-tenancy robusto** com isolamento por `tenant_id`
2. ✅ **Custom prompt por tenant** (permite especialização)
3. ✅ **Instrução de "não sei"** no prompt
4. ✅ **Tratamento de erros** do LLM
5. ✅ **Logging básico** de ingestão

---

## 🚨 Principais Gaps para Evoluir

### Prioridade Alta 🔴

1. **Chunking semântico**

   - Respeitar parágrafos, seções, listas
   - Adicionar overlap (10-20%)
   - Detectar estrutura do documento

2. **Metadados ricos**

   - Adicionar: `filename`, `category`, `upload_date`, `section`, `page`
   - Implementar deduplicação por hash
   - Versionamento de documentos

3. **Reranking**

   - Adicionar modelo de rerank após busca vetorial
   - Implementar score threshold
   - Diversidade de resultados

4. **Memória de conversa**
   - Armazenar histórico de turnos
   - Reescrever query com contexto anterior
   - Session management

### Prioridade Média 🟡

5. **Busca híbrida (BM25 + Vetorial)**

   - Combinar busca lexical e semântica
   - Melhor para nomes próprios, códigos, datas

6. **Observabilidade**

   - Feedback do usuário (👍/👎)
   - Métricas de relevância
   - Tracking de custo

7. **K adaptativo**
   - Ajustar baseado no tipo de pergunta
   - Score threshold dinâmico

### Prioridade Baixa 🟢

8. **Templates por domínio**

   - Prompts especializados (jurídico, técnico, etc.)
   - Comportamento diferente por categoria

9. **Citação de fontes**
   - Obrigar modelo a citar qual chunk usou
   - Link para documento original

---

## 💡 Recomendação

**Você está voando no escuro?** ✅ **Sim**

O sistema funciona, mas sem métricas de qualidade, você não sabe:

- Se os chunks retornados são relevantes
- Se o usuário está satisfeito
- Se há alucinações
- Quanto custa cada consulta

**Próximo passo sugerido**: Implementar observabilidade básica (logs de relevância + feedback do usuário) antes de otimizar chunking/retrieval.

---

## 📚 Referências

- [document_ingestion.py](file:///c:/programming/company-buddy/backend/app/services/document_ingestion.py)
- [qdrant_service.py](file:///c:/programming/company-buddy/backend/app/services/qdrant_service.py)
- [llm_service.py](file:///c:/programming/company-buddy/backend/app/services/llm_service.py)
- [ask.py](file:///c:/programming/company-buddy/backend/app/api/v1/routes/ask.py)
