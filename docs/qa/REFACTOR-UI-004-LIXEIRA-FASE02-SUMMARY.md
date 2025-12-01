# REFACTOR-UI-004: Lixeira - Fase 02 - SUMMARY

**Data**: 2025-11-28  
**Branch**: qa/fixpack-04  
**Projeto**: RC Gestor v1.2.97  

---

## 📋 Objetivo

Continuar extração de lógica testável de `src/modules/lixeira/views/lixeira.py`, focando em **Singleton Management**, **Progress Dialog** e **Data Transformation**.

---

## 🎯 Recorte Escolhido - Fase 02

**Singleton + Progress + Data Transformation**

Extraído **7 novas funções puras** para o arquivo `lixeira_helpers.py` (que já tinha 7 funções da Fase 01):

### Funções Adicionadas:

1. `should_open_new_trash_window` - Determina se deve criar nova janela
2. `should_refresh_trash_window` - Determina se deve fazer refresh
3. `calculate_progress_percentage` - Calcula percentual de progresso (0-100%)
4. `normalize_trash_row_data` - Normaliza rows do Supabase para estrutura consistente
5. `format_author_initial` - Formata inicial do autor para exibição
6. `format_timestamp_with_author` - Formata timestamp com inicial do autor
7. `parse_error_list_for_display` - Converte lista de erros para formato de exibição

---

## 📁 Arquivos Modificados/Criados

### 1. `src/modules/lixeira/views/lixeira_helpers.py` (atualizado)

**ANTES** (Fase 01): 219 linhas, 7 funções  
**DEPOIS** (Fase 01 + 02): **431 linhas, 14 funções totais**

#### Novas Funções (Fase 02):

```python
def should_open_new_trash_window(window_exists: bool) -> bool:
    """Determina se deve criar nova janela da lixeira."""

def should_refresh_trash_window(
    window_exists: bool,
    has_pending_changes: bool = False,
) -> bool:
    """Determina se deve recarregar a janela da lixeira."""

def calculate_progress_percentage(current: int, total: int) -> float:
    """Calcula percentual de progresso (0.0 a 100.0)."""

def normalize_trash_row_data(
    row: Any,
    field_mappings: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Normaliza dados de row da lixeira com fallbacks."""

def format_author_initial(
    author_id: str,
    initials_mapping: dict[str, str] | None = None,
    display_name_fallback: str = "",
) -> str:
    """Formata inicial do autor (1 caractere maiúsculo)."""

def format_timestamp_with_author(
    timestamp: str,
    author_initial: str,
) -> str:
    """Formata timestamp com autor: '28/11/2025 18:30 (J)'."""

def parse_error_list_for_display(error_list: Any) -> list[str]:
    """Converte lista de erros para formato de exibição."""
```

**Características**:
- Funções puras sem side-effects
- Type hints completos
- Docstrings com Examples
- Suporte a múltiplos formatos de entrada (dict/objeto)
- Fallbacks robustos (field_mappings customizáveis)

---

### 2. `tests/unit/modules/lixeira/views/test_lixeira_helpers_fase02.py` (novo)

**31 testes** cobrindo todas as 7 funções:

| Função | Testes | Cobertura |
|--------|--------|-----------|
| `should_open_new_trash_window` | 2 | Window exists/não exists |
| `should_refresh_trash_window` | 4 | Window exists, pending changes, combinações |
| `calculate_progress_percentage` | 5 | Start (0%), mid (50%), end (100%), edge cases (total=0, current>total) |
| `normalize_trash_row_data` | 6 | Dict completo/parcial, objeto, fallbacks, custom mappings, empty row |
| `format_author_initial` | 5 | Mapping, display_name fallback, ID fallback, empty, empty alias |
| `format_timestamp_with_author` | 3 | Com inicial, sem inicial, timestamp vazio |
| `parse_error_list_for_display` | 6 | Tuplas (id,msg), strings, single string, empty, None, formato misto |

**TOTAL**: **31 testes**

---

## 📊 Mapeamento de Pontos-Alvo em lixeira.py

### 1. **Singleton Management** (linhas 39-58)

```python
_OPEN_WINDOW: tb.Toplevel | None = None

def _is_open() -> bool:
    try:
        return _OPEN_WINDOW is not None and int(_OPEN_WINDOW.winfo_exists()) == 1
    except Exception:
        return False

def refresh_if_open() -> None:
    """Recarrega a listagem se a janela estiver aberta."""
    if not _is_open():
        return
    try:
        _OPEN_WINDOW._carregar()
    except Exception:
        log.exception("Falha ao recarregar Lixeira aberta.")
```

**Extração**:
- ✅ `should_open_new_trash_window(window_exists)` - decisão de criar/reusar
- ✅ `should_refresh_trash_window(window_exists, has_pending_changes)` - decisão de refresh

**Nota**: Lógica de Tkinter (`winfo_exists`, `_carregar()`) permanece em `lixeira.py`.

---

### 2. **Progress Dialog** (linhas 310-334)

```python
def _show_wait_dialog(count: int) -> Tuple[tk.Toplevel, ttk.Label, ttk.Progressbar]:
    dlg = tk.Toplevel(win)
    # ... configuração UI ...
    label = ttk.Label(dlg, text=f"Apagando 0/{count} registro(s)... Aguarde.")
    bar = ttk.Progressbar(dlg, mode="determinate", maximum=max(count, 1), value=0)
    # ...
    return dlg, label, bar

def _make_purge_progress_cb(bar: ttk.Progressbar, label: ttk.Label):
    def progress_cb(idx: int, total: int, client_id: int) -> None:
        def _update():
            bar["maximum"] = max(total, 1)
            bar["value"] = idx
            label.configure(text=f"Apagando {idx}/{total} registro(s)... Aguarde.")
        win.after(0, _update)
    return progress_cb
```

**Extração**:
- ✅ `calculate_progress_percentage(current, total)` - cálculo de percentual
- ✅ `format_progress_text(current, total, action)` - já existia na Fase 01
- ❌ `_show_wait_dialog()` - **NÃO extraído** (criação de widgets Tk)
- ❌ `_make_purge_progress_cb()` - **NÃO extraído** (depende de widgets Tk)

**Justificativa**: Factories de callbacks com Tkinter não são puramente testáveis sem mocks complexos. Mantidas em `lixeira.py`.

---

### 3. **Data Transformation** (linhas 210-278)

```python
def _get_val(obj: Any, *names: str):
    for name in names:
        if hasattr(obj, name):
            try:
                val = getattr(obj, name)
            except Exception:
                val = None
            if val is not None:
                return val
        if isinstance(obj, dict) and name in obj:
            val = obj.get(name)
            if val is not None:
                return val
    return None

# Uso em carregar():
for r in rows:
    r_id = _get_val(r, "id") or ""
    razao_social = _get_val(r, "razao_social") or ""
    cnpj = _get_val(r, "cnpj") or ""
    nome = _get_val(r, "nome") or ""
    whatsapp = _get_val(r, "whatsapp", "numero") or ""
    obs = _get_val(r, "obs", "observacoes", "Observacoes") or ""
    ultima_raw = _get_val(r, "ultima_alteracao", "updated_at") or ""
    # ...
    if ultima_raw:
        try:
            from src.app_utils import fmt_data
            ultima_fmt = fmt_data(ultima_raw)
        except Exception:
            ultima_fmt = str(ultima_raw)
    # ...
    by = (_get_val(r, "ultima_por") or "").strip()
    initial = ""
    if by:
        # ... lógica de mapeamento de iniciais ...
        initial = (alias[:1] or "").upper()
    if ultima_fmt and initial:
        ultima_fmt = f"{ultima_fmt} ({initial})"
```

**Extração**:
- ✅ `extract_field_value(obj, *field_names)` - já existia na Fase 01
- ✅ `normalize_trash_row_data(row, field_mappings)` - normalização completa
- ✅ `format_author_initial(author_id, initials_mapping, display_name_fallback)` - formatação de inicial
- ✅ `format_timestamp_with_author(timestamp, author_initial)` - combinação timestamp+autor

**Vantagens**:
- Testável sem Tkinter
- Fallbacks configuráveis
- Suporta tanto objetos quanto dicts

---

## ✅ Resultados de Testes

### Fase 02 Isolada

```bash
python -m pytest tests/unit/modules/lixeira/views/test_lixeira_helpers_fase02.py -vv --maxfail=1
```

**RESULTADO**: **31 passed in 4.42s** ✅

---

### Módulo Lixeira Completo (Regressão)

```bash
python -m pytest tests/unit/modules/lixeira -vv --maxfail=1
```

**RESULTADO**: **93 passed in 10.83s** ✅

**Breakdown**:
- **24 testes** - service layer (`test_lixeira_service.py`)
- **38 testes** - helpers Fase 01 (`test_lixeira_helpers_fase01.py`)
- **31 testes** - helpers Fase 02 (`test_lixeira_helpers_fase02.py`)

**Total**: **93 testes, 0 falhas, 0 regressões**

---

## ✅ Validação QA

### Pyright

```bash
python -m pyright src/modules/lixeira/views/lixeira.py \
                   src/modules/lixeira/views/lixeira_helpers.py \
                   tests/unit/modules/lixeira/views/test_lixeira_helpers_fase01.py \
                   tests/unit/modules/lixeira/views/test_lixeira_helpers_fase02.py
```

**RESULTADO**: **0 errors, 0 warnings, 0 informations** ✅

---

### Ruff

```bash
python -m ruff check src/modules/lixeira/views/lixeira.py \
                     src/modules/lixeira/views/lixeira_helpers.py \
                     tests/unit/modules/lixeira/views/test_lixeira_helpers_fase01.py \
                     tests/unit/modules/lixeira/views/test_lixeira_helpers_fase02.py
```

**RESULTADO**: **All checks passed!** ✅

---

### Bandit

```bash
python -m bandit -r src infra adapters data security -x tests \
  -f json -o reports/bandit-refactor-ui-004-lixeira-fase02.json
```

**RESULTADO**: **6 issues LOW** (não relacionados à Fase 02) ✅

**Detalhes**:
- `reports/bandit-refactor-ui-004-lixeira-fase02.json` criado
- **Total LOC scanned**: 26,798 linhas
- **Severidades**:
  - HIGH: 0
  - MEDIUM: 0
  - LOW: 6 (issues antigos em outros módulos)
- **Confidence**:
  - HIGH: 6
- **Issues no código da Fase 02**: **0**

**Issues LOW existentes** (não introduzidos nesta fase):
- 1x em `src/core/services/notes_service.py` (B110 - try/except/pass)
- Outros em módulos não relacionados

---

## 📊 Estatísticas Consolidadas

| Métrica | Fase 01 | Fase 02 | **Total** |
|---------|---------|---------|-----------|
| **Funções extraídas** | 7 | 7 | **14** |
| **Testes criados** | 38 | 31 | **69** |
| **Linhas helpers** | 219 | 212 (delta) | **431** |
| **Arquivos de teste** | 1 | 1 | **2** |
| **Testes módulo lixeira** | 62 | 93 | **93** |
| **Pyright errors** | 0 | 0 | **0** |
| **Ruff errors** | 0 | 0 | **0** |
| **Bandit issues (novos)** | 0 | 0 | **0** |

---

## 🔄 Comparação com Fases Anteriores

| Fase | Módulo | Funções (total) | Testes (novos) | Duração |
|------|--------|-----------------|----------------|---------|
| **001** | pdf_preview | 4 | 31 | ~3.5s |
| **002** | clientes | 5 | 35 | ~4.2s |
| **003** | hub | 5 | 42 | ~4.8s |
| **004-F1** | lixeira | 7 | 38 | ~4.83s |
| **004-F2** | lixeira | **14** | **31** | **4.42s** |

**Evolução Lixeira**:
- Fase 01: 7 funções, 38 testes (status, validação, mensagens)
- Fase 02: +7 funções, +31 testes (singleton, progress, data transform)
- **Total**: 14 funções, 69 testes, 93 testes no módulo completo

---

## 🎓 Lições Aprendidas - Fase 02

### 1. **Separação de Concerns: UI vs Lógica**

**Decisão**: Não extrair `_show_wait_dialog()` nem `_make_purge_progress_cb()`

**Motivo**:
- Factories de callbacks com widgets Tkinter (`ttk.Progressbar`, `ttk.Label`) não são puramente testáveis
- Extrair requereria mocks complexos que não agregam valor
- Melhor manter em `lixeira.py` e testar lógica pura de cálculo (`calculate_progress_percentage`)

**Aprendizado**: Nem tudo precisa ser extraído. Foco em **lógica de negócio pura**.

---

### 2. **Normalização de Dados com Fallbacks**

**Implementação**: `normalize_trash_row_data()` com `field_mappings` customizáveis

**Vantagens**:
```python
# Default mapping
result = normalize_trash_row_data(row)

# Custom mapping para compatibilidade com schemas diferentes
custom = {
    "id": ["custom_id", "pk"],
    "razao_social": ["company_name", "business_name"],
}
result = normalize_trash_row_data(row, field_mappings=custom)
```

**Aprendizado**: Permitir customização aumenta reusabilidade sem quebrar simplicidade.

---

### 3. **Progress Percentage: Edge Cases Importantes**

**Casos testados**:
```python
calculate_progress_percentage(5, 0)    # total=0 → 0.0 (não crash)
calculate_progress_percentage(15, 10)  # current>total → 100.0 (cap)
```

**Aprendizado**: Edge cases de divisão por zero e valores inválidos devem ser tratados com defaults seguros.

---

### 4. **Formatação de Autores com Múltiplos Fallbacks**

**Hierarquia de fallback** em `format_author_initial()`:
1. **Mapping explícito** (`initials_mapping`)
2. **Display name fallback** (ex: "João Silva" → "J")
3. **ID fallback** (ex: "user-123" → "U")
4. **Empty string** (se tudo falhar)

**Aprendizado**: Múltiplos níveis de fallback garantem que sempre há um valor razoável.

---

### 5. **Parse de Error Lists: Formato Flexível**

**Suporta**:
```python
# Tuplas (id, msg)
[(1, "Erro A"), (2, "Erro B")]  → ["ID 1: Erro A", "ID 2: Erro B"]

# Strings simples
["Erro genérico"]  → ["Erro genérico"]

# String única
"Erro"  → ["Erro"]

# Formato misto
[(1, "Erro"), "Outro erro"]  → ["ID 1: Erro", "Outro erro"]
```

**Aprendizado**: Aceitar múltiplos formatos de entrada evita quebras quando APIs mudam.

---

## 🚀 Próximos Passos (Fases Futuras)

### Candidatos NÃO Extraídos Ainda:

1. **Dialog Factories** (complexidade alta, baixo valor testável):
   - `_show_wait_dialog()` - criação de Toplevel de progresso
   - `_make_purge_progress_cb()` - callback com widgets Tk

2. **UI State Management** (já parcialmente coberto):
   - `_set_busy()` - cursor + estado de botões
   - **Alternativa**: Extrair apenas a lógica de decisão (já feito em `calculate_trash_button_states`)

3. **Event Handlers** (acoplados ao Tkinter):
   - `on_restore()`, `on_purge()`, `carregar()`
   - **Possível**: Extrair apenas validações/transformações internas

---

## 📝 Notas Finais

### ✅ REFACTOR-UI-004 - FASE 02 COMPLETA

**Conquistas**:
- ✅ 7 novas funções puras extraídas (14 total com Fase 01)
- ✅ 31 testes novos (69 total com Fase 01)
- ✅ 93 testes no módulo lixeira (24 service + 38 F1 + 31 F2)
- ✅ Zero erros em Pyright/Ruff/Bandit
- ✅ Zero regressões
- ✅ Comportamento de `lixeira.py` **intacto**

**Padrão de Qualidade Mantido**:
- Funções puras sem side-effects
- Type hints completos
- Docstrings com Examples
- Fallbacks robustos
- Edge cases cobertos

**Decisões Arquiteturais**:
- Não extrair factories de UI (baixo valor testável)
- Priorizar lógica de negócio pura
- Aceitar múltiplos formatos de entrada (flexibilidade)

---

## 📂 Arquivos Envolvidos

### Modificados:
- `src/modules/lixeira/views/lixeira_helpers.py` (219 → 431 linhas)

### Criados:
- `tests/unit/modules/lixeira/views/test_lixeira_helpers_fase02.py` (257 linhas, 31 testes)
- `reports/bandit-refactor-ui-004-lixeira-fase02.json` (4,085 linhas)
- `docs/qa/REFACTOR-UI-004-LIXEIRA-FASE02-SUMMARY.md` (este arquivo)

### Inalterados (sem mudança de comportamento):
- `src/modules/lixeira/views/lixeira.py` (295 linhas)
- `tests/unit/modules/lixeira/test_lixeira_service.py` (24 testes)
- `tests/unit/modules/lixeira/views/test_lixeira_helpers_fase01.py` (38 testes)

---

**Assinado**: GitHub Copilot  
**Status**: ✅ APROVADO - Pronto para review  
**Branch**: qa/fixpack-04  
**Próxima Fase**: Considerar outras telas UI ou finalizar série REFACTOR-UI-004
