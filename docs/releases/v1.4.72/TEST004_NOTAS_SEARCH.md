# TEST004_NOTAS_SEARCH.md

**RC Gestor v1.4.72 — Mapeamento de src/core/search/search.py**  
**Data:** 2025-12-20  
**Objetivo:** Documentar API pública do módulo search antes de criar TEST-004

---

## 1. Funções Públicas

### 1.1 `search_clientes(term, order_by, org_id)`

**Assinatura:**
```python
def search_clientes(
    term: str | None,
    order_by: str | None = None,
    org_id: str | None = None
) -> list[Cliente]
```

**Comportamento:**
- **Online (Supabase disponível):**
  - Exige `org_id` (levanta `ValueError` se None)
  - Consulta `clients` table com filtro `deleted_at IS NULL` e `org_id = ?`
  - Se `term` fornecido: usa `ilike` em `nome`, `razao_social`, `cnpj`, `numero`
  - Aplica filtro local adicional com normalização
  - Se não encontrar resultados, reconsuita sem filtro e reaplica filtro local
  - Suporta ordenação via `order_by`

- **Offline (Supabase indisponível ou falha):**
  - Fallback para `list_clientes_by_org()` (repositório local)
  - Exige `org_id` (levanta `ValueError` se None)
  - Aplica filtro local com `_filter_clientes()`

- **Auto-resolve org_id:**
  - Se `org_id=None`, tenta obter de `get_current_user().org_id`

**Retorno:** Lista de objetos `Cliente`

---

## 2. Funções Internas (helpers)

### 2.1 `_normalize_order(order_by)`
- Converte apelidos de ordenação para colunas canônicas
- Retorna `(column: str | None, descending: bool)`
- Mapeamento:
  - `"nome"` → `("nome", False)`
  - `"razao social"` / `"razao_social"` → `("razao_social", False)`
  - `"cnpj"` → `("cnpj", False)`
  - `"id"` → `("id", False)`
  - `"ultima alteracao"` / `"ultima_alteracao"` → `("ultima_alteracao", True)`
- Case-insensitive
- Retorna `(None, False)` se não encontrar match

### 2.2 `_row_to_cliente(row)`
- Converte `Mapping[str, Any]` (row do Supabase) em `Cliente` object
- Extrai campos: `id`, `numero`, `nome`, `razao_social`, `cnpj`, `cnpj_norm`, `ultima_alteracao`, `obs`, `ultima_por`, `created_at`

### 2.3 `_cliente_search_blob(cliente)`
- Concatena campos relevantes em string normalizada para busca textual
- Usa `join_and_normalize()` com: `id`, `nome`, `razao_social`, `cnpj`, `numero`, `obs`

### 2.4 `_filter_rows_with_norm(rows, term)`
- Filtra rows já carregadas usando normalização
- Cacheia `_search_norm` em cada row para evitar recálculo
- Termo vazio retorna todas as rows
- Usa `normalize_search(term)` para gerar query normalizada
- Retorna `list[dict[str, Any]]`

### 2.5 `_filter_clientes(clientes, term)`
- Filtra lista de `Cliente` usando busca textual normalizada
- Termo vazio retorna todos os clientes
- Usa `_cliente_search_blob()` para gerar string de busca

---

## 3. Dependências Externas

### 3.1 Supabase
- `infra.supabase_client.supabase` → table("clients")
- `infra.supabase_client.exec_postgrest()` → executa query
- `infra.supabase_client.is_supabase_online()` → verifica conectividade

### 3.2 Repositório Local
- `src.core.db_manager.db_manager.list_clientes_by_org()` → fallback offline
- `src.core.db_manager.db_manager.CLIENT_COLUMNS` → constante com colunas

### 3.3 Sessão
- `src.core.session.session.get_current_user()` → obtém org_id do usuário logado

### 3.4 Normalização
- `src.core.textnorm.normalize_search()` → normaliza termo de busca
- `src.core.textnorm.join_and_normalize()` → concatena e normaliza múltiplos campos

### 3.5 Modelos
- `src.core.models.Cliente` → dataclass/NamedTuple com campos do cliente

---

## 4. Contratos/Retornos

### 4.1 Retorno Normal
- `list[Cliente]` → lista de clientes encontrados (pode ser vazia)

### 4.2 Exceções
- `ValueError("org_id obrigatorio")` → quando online mas org_id é None
- `ValueError("org_id obrigatorio")` → quando offline/falha e org_id é None

### 4.3 Fallback
- Sempre tenta Supabase primeiro se online
- Em exceção do Supabase, faz fallback para repositório local
- Log de warning em caso de fallback: `"search_clientes: falha no Supabase, usando fallback local"`

---

## 5. Cenários de Teste (TEST-004)

### A) Busca Básica
1. **Query normal com resultados** → retorna lista de clientes
2. **Query vazia/whitespace** → retorna todos os clientes da org
3. **Query sem resultados** → retorna lista vazia
4. **Query com caracteres especiais** → normalização correta

### B) Ordenação
1. **order_by="nome"** → chama Supabase com `order("nome", desc=False)`
2. **order_by="ultima alteracao"** → chama com `order("ultima_alteracao", desc=True)`
3. **order_by inválido** → ignora ordenação (None)

### C) Multi-org
1. **org_id fornecido** → filtra por org_id
2. **org_id=None mas current_user tem org_id** → usa org_id do usuário
3. **org_id=None e current_user=None** → levanta ValueError

### D) Fallback Offline
1. **Supabase offline** → chama list_clientes_by_org()
2. **Supabase com exceção** → fallback + log warning
3. **Fallback sem org_id** → levanta ValueError

### E) Filtro Duplo (online)
1. **Term fornecido** → primeiro ilike, depois filtro local
2. **Sem resultados no ilike** → reconsuita sem filtro, reaplica local
3. **Cacheamento de _search_norm** → não recalcula em rows repetidas

---

## 6. Pontos de Mock para Testes

### 6.1 Mock de Supabase
- `infra.supabase_client.is_supabase_online()` → retorna True/False
- `infra.supabase_client.exec_postgrest()` → retorna mock com .data
- `infra.supabase_client.supabase.table()` → retorna mock QueryBuilder

### 6.2 Mock de Repositório Local
- `src.core.db_manager.db_manager.list_clientes_by_org()` → retorna lista de Cliente

### 6.3 Mock de Sessão
- `src.core.session.session.get_current_user()` → retorna mock com .org_id

### 6.4 Mock de Normalização (opcional)
- `src.core.textnorm.normalize_search()` → pode usar implementação real ou mock
- `src.core.textnorm.join_and_normalize()` → pode usar implementação real ou mock

---

## 7. Observações Importantes

1. **Duplo filtro online:** Quando online + term fornecido, faz:
   - 1ª query: com `ilike` no SQL
   - Filtro local adicional
   - Se vazio: 2ª query sem filtro + filtro local

2. **ValueError exigente:** Tanto online quanto offline exigem org_id

3. **Cacheamento inteligente:** `_filter_rows_with_norm()` cacheia `_search_norm` em cada row

4. **Log de fallback:** Exception do Supabase gera log.warning, não propaga erro

5. **Order_by case-insensitive:** `_normalize_order()` aceita "Razao Social" e "razao_social"

---

**Status:** Mapeamento completo. Pronto para criar test_search_fase61.py.
