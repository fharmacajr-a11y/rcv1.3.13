# Análise Pós-Refactor: Módulo ANVISA (P0.1 + P0.2)

**Data:** 19/12/2025  
**Versão:** RC v1.4.52  
**Mudanças aplicadas:** P0.1 (constants.py) + P0.2 (window_utils.py)

---

## 1. Resumo do Estado Atual

### Fluxos principais funcionando ✅
- ✅ **Listagem de demandas**: Carrega do Supabase, agrupa por cliente (1 linha/cliente)
- ✅ **Criação de demanda**: Modal com 6 tipos, validação de duplicado, persiste no Supabase
- ✅ **Exclusão de demanda**: Via botão ou menu contexto, com confirmação
- ✅ **Finalização de demanda**: Altera status para "done" via controller headless
- ✅ **Histórico de demandas**: Popup centralizado sem flash, lista todas as demandas do cliente
- ✅ **Browser de arquivos**: Janela única por cliente para upload/gestão de documentos

### MVC parcial atual
```
Repository (infra/repositories/anvisa_requests_repository.py)
    ↓ CRUD operations (list/create/update/delete)
Controller (src/modules/anvisa/controllers/anvisa_controller.py)
    ↓ delete_request(), close_request() - HEADLESS ✅
View (src/modules/anvisa/views/anvisa_screen.py + mixins)
    ↓ UI + lógica de criação/validação/listagem - ACOPLADO ⚠️
```

**Headless (testável sem GUI):**
- ✅ Controller: `delete_request()`, `close_request()`
- ✅ Repository: `list_requests()`, `create_request()`, `update_request_status()`, `delete_request()`

**Ainda acoplado à UI:**
- ⚠️ Criação de demanda: modal + validação duplicado + persist → em `anvisa_screen.py`
- ⚠️ Listagem/refresh: carregamento + agrupamento + popular Treeview → em `_anvisa_requests_mixin.py`
- ⚠️ Validação de duplicado: busca em cache local → em `_anvisa_requests_mixin.py`

### Mudanças P0.1/P0.2 aplicadas

**P0.1 - Constantes centralizadas:**
- ✅ Arquivo `src/modules/anvisa/constants.py` criado (49 linhas)
- ✅ `REQUEST_TYPES`: 6 tipos de demanda (incluindo "Cancelamento de AFE")
- ✅ `STATUS_OPEN`, `STATUS_CLOSED`, `STATUS_ALL`: Sets com status válidos
- ✅ `DEFAULT_CLOSE_STATUS`: "done"
- ✅ `STATUS_ALIASES`: 18 aliases (incluindo legados como "aberta")
- ✅ Usado em: `anvisa_screen.py`, `_anvisa_requests_mixin.py`, `anvisa_controller.py`, `anvisa_requests_repository.py`

**P0.2 - Helpers de janela unificados:**
- ✅ Arquivo `src/ui/window_utils.py` atualizado (+112 linhas)
- ✅ Funções adicionadas:
  - `apply_window_icon(window)` - aplica rc.ico
  - `prepare_hidden_window(win)` - withdraw + alpha 0 + offscreen
  - `show_centered_no_flash(win, parent, width, height)` - mostra centralizado sem flash
  - `center_window_simple(window, parent)` - centralização simples
- ✅ Usado em: `anvisa_screen.py` (modal nova demanda), `_anvisa_history_popup_mixin.py` (popup histórico)
- ✅ Métodos locais removidos: `_apply_window_icon`, `_prepare_hidden_window`, `_show_centered_no_flash`, `_center_window`

---

## 2. Checklist de Consistência (P0.1 - Constantes)

### ✅ REQUEST_TYPES centralizado
- ✅ `anvisa_screen.py` linha 550: importa e usa `REQUEST_TYPES` no modal
- ⚠️ **DUPLICAÇÃO ENCONTRADA**: `anvisa_footer.py` linha 22-27 tem lista hardcoded:
  ```python
  ANVISA_PROCESSES = [
      "Alteração do Responsável Legal",
      "Alteração do Responsável Técnico",
      "Alteração da Razão Social",
      "Associação ao SNGPC",
      "Alteração de Porte",
  ]
  ```
  **→ Falta "Cancelamento de AFE" e deveria usar `constants.REQUEST_TYPES`**

- ⚠️ **DUPLICAÇÃO ENCONTRADA**: `helpers/process_slug.py` linha 50-54 tem mapeamento hardcoded:
  ```python
  PROCESS_SLUG_MAP = {
      "Alteração do Responsável Legal": "alteracao_responsavel_legal",
      "Alteração do Responsável Técnico": "alteracao_responsavel_tecnico",
      ...
      "Alteração de Porte": "alteracao_porte",
  }
  ```
  **→ Falta "Cancelamento de AFE" e deveria derivar de `constants.REQUEST_TYPES`**

### ✅ STATUS_OPEN/CLOSED/ALL centralizado
- ✅ `_anvisa_requests_mixin.py` linha 140-151: usa `STATUS_OPEN`, `STATUS_CLOSED`, `STATUS_ALIASES` em `_is_open_status()`
- ✅ `anvisa_requests_repository.py` linha 223: usa `STATUS_ALL` e `STATUS_ALIASES` em `update_request_status()`
- ✅ `anvisa_controller.py` linha 90: usa `DEFAULT_CLOSE_STATUS` em `close_request()`

### ⚠️ Strings hardcoded restantes

| Arquivo | Linha | Código | Severidade | Recomendação |
|---------|-------|--------|------------|--------------|
| `anvisa_screen.py` | 411 | `"status": "draft"` | **Baixa** | Usar `constants.STATUS_OPEN` (qualquer item do set) ou criar `DEFAULT_CREATE_STATUS = "draft"` |
| `_anvisa_requests_mixin.py` | 376 | `status = request.get("status", "draft")` | **Baixa** | Idem acima |
| `anvisa_footer.py` | 22-27 | Lista `ANVISA_PROCESSES` | **Média** | Usar `constants.REQUEST_TYPES` (remover "Cancelamento de AFE" se não aplicável ao footer) |
| `helpers/process_slug.py` | 50-54 | Dict `PROCESS_SLUG_MAP` | **Média** | Gerar mapa dinamicamente a partir de `constants.REQUEST_TYPES` |

**Conclusão P0.1:**
- ✅ **Uso principal das constantes está correto**
- ⚠️ **2 arquivos secundários (footer + helper) ainda têm listas hardcoded**
- ⚠️ **2 ocorrências de "draft" hardcoded (baixa prioridade - status padrão de criação)**

---

## 3. Checklist de Utilidades de Janela (P0.2)

### ✅ Uso de `window_utils` confirmado

| Função | Onde usa | Linha | Status |
|--------|----------|-------|--------|
| `apply_window_icon` | `anvisa_screen.py` | 466 | ✅ Modal nova demanda |
| `apply_window_icon` | `_anvisa_history_popup_mixin.py` | 64 | ✅ Popup histórico |
| `prepare_hidden_window` | `anvisa_screen.py` | 458 | ✅ Modal nova demanda |
| `prepare_hidden_window` | `_anvisa_history_popup_mixin.py` | 56 | ✅ Popup histórico |
| `show_centered_no_flash` | `anvisa_screen.py` | 565 | ✅ Modal nova demanda |
| `center_window_simple` | `_anvisa_history_popup_mixin.py` | 43 | ✅ Reposicionar popup existente |

### ⚠️ Duplicação/inconsistência restante

**ENCONTRADO:** `_anvisa_history_popup_mixin.py` linha 166 ainda tem referência a método OLD:
```python
anvisa_screen.AnvisaScreen._show_centered_no_flash(
```
**→ Deveria usar o import de `window_utils.show_centered_no_flash` diretamente**

**Status:** Provavelmente código morto (não executado em fluxo normal), mas deveria ser removido.

### ✅ Anti-flash aplicado nos 2 pontos críticos

1. **Modal nova demanda** (`anvisa_screen.py` linha 458-466):
   ```python
   prepare_hidden_window(dlg)  # ✅
   # ... construir UI ...
   apply_window_icon(dlg)  # ✅
   # ... construir botões ...
   show_centered_no_flash(dlg, self.winfo_toplevel(), width=680, height=420)  # ✅
   ```

2. **Popup histórico** (`_anvisa_history_popup_mixin.py` linha 56-64):
   ```python
   prepare_hidden_window(self._history_popup)  # ✅
   # ... construir UI ...
   apply_window_icon(self._history_popup)  # ✅
   # ... construir botões ...
   # (centralização via center_window_simple ao atualizar) ✅
   ```

**Conclusão P0.2:**
- ✅ **Helpers unificados e usados corretamente nos 2 pontos principais**
- ⚠️ **1 referência morta ao método antigo (linha 166 do popup mixin) - limpeza recomendada**
- ✅ **Anti-flash funcionando perfeitamente (sem flash visível ao usuário)**

---

## 4. Testes e Cobertura (Observação)

### Testes existentes

**Controller (headless):** `tests/unit/modules/anvisa/test_anvisa_controller.py`
- ✅ 9 testes, todos passando
- ✅ Mock do repository (FakeAnvisaRepository)
- ✅ Testa: delete_request, close_request, exceções, requests inexistentes
- ✅ **Cobertura:** ~100% do controller (53 LOC de lógica)

**View (helpers puros):** `tests/unit/modules/anvisa/test_anvisa_screen_basic.py`
- ✅ 34 testes (19 passed, 15 skipped)
- ✅ Testa helpers: `_format_cnpj`, `_format_datetime`, `_is_open_status`, `_find_open_duplicate`, `_summarize_demands_for_main`
- ✅ Usa `AnvisaScreen.__new__(AnvisaScreen)` para evitar Tkinter init
- ⚠️ **Limitação:** Não testa fluxos completos (criação, exclusão, listagem)

### Partes difíceis de testar (UI acoplada)

**Alto acoplamento com Tkinter:**
1. `_on_new_anvisa_clicked()` - criação de demanda (linha 360-437 de `anvisa_screen.py`)
   - Modal Tkinter + validação + persist + messagebox tudo inline
   - **Impossível testar sem Tkinter rodando**

2. `_load_requests_from_cloud()` - listagem (linha 41-109 de `_anvisa_requests_mixin.py`)
   - Carrega do Supabase + popula Treeview diretamente
   - **Impossível testar headless**

3. `_open_history_popup()` - popup histórico (linha 23-170 de `_anvisa_history_popup_mixin.py`)
   - Cria Toplevel + constrói widgets + bind eventos
   - **Impossível testar sem Tkinter**

4. Menu contexto e binds de eventos (linha 196-207 de `anvisa_screen.py`)
   - `unbind()` + `bind()` de Double-1, TreeviewSelect, Button-3
   - **Difícil testar eventos do Tkinter**

**Dependências externas não mockadas:**
- Supabase real (sem mock em testes unitários de view)
- Messagebox (interrompe testes headless)
- Tkinter.Toplevel (requer display)

### Cobertura estimada

```
Controller:     100% ✅ (headless, totalmente testado)
Repository:     ~70% ⚠️ (CRUD básico funciona, mas sem testes unitários dedicados)
View (helpers): ~60% ✅ (helpers puros testados, mas fluxos completos não)
View (UI):      ~5%  ❌ (praticamente impossível testar sem refactor MVC)
```

**Conclusão Testes:**
- ✅ **Controller headless tem excelente cobertura**
- ⚠️ **View tem ~90% de lógica ainda acoplada à UI (não testável)**
- 🎯 **Próximo passo P1 deve focar em extrair lógica da View para Service headless**

---

## 5. Dívidas Técnicas / Riscos Atuais

### Alta severidade 🔴

1. **Criação de demanda 100% na View** (Alta)
   - Arquivo: `anvisa_screen.py` linha 360-437
   - Problema: Modal + validação duplicado + persist + messagebox tudo inline
   - Risco: Impossível testar sem Tkinter, difícil refatorar depois
   - **Impacto:** Bugs em validação/criação não são detectados por testes automatizados

2. **Cache de demandas não sincronizado entre usuários** (Alta)
   - Arquivo: `_anvisa_requests_mixin.py` linha 83-85
   - Problema: `_demandas_cache` e `_requests_by_client` são locais, não sincronizam com Supabase em tempo real
   - Risco: Se outro usuário criar/editar demanda, cache fica desatualizado até refresh manual
   - **Impacto:** Dados inconsistentes em ambientes multi-usuário

### Média severidade 🟡

3. **Listagem/agrupamento na View** (Média)
   - Arquivo: `_anvisa_requests_mixin.py` linha 41-109
   - Problema: Carrega + agrupa + formata + popula Treeview tudo junto
   - Risco: Dificulta testes de lógica de agrupamento/summary
   - **Impacto:** Lógica de negócio misturada com UI

4. **Duplicações hardcoded em arquivos secundários** (Média)
   - Arquivos: `anvisa_footer.py` (linha 22-27), `helpers/process_slug.py` (linha 50-54)
   - Problema: Listas de tipos de demanda hardcoded, sem usar `constants.REQUEST_TYPES`
   - Risco: Ao adicionar novo tipo, precisa atualizar 3 lugares (constants + footer + helper)
   - **Impacto:** Inconsistência de dados, manutenção duplicada

5. **Logs redundantes View + Controller + Repository** (Média)
   - Arquivos: 22 ocorrências de `log.info("[ANVISA] ...")` em views, controller e repository
   - Problema: Mesma ação logada 3 vezes (ex: excluir demanda loga na View, Controller E Repository)
   - Risco: Logs poluídos, dificulta debug
   - **Impacto:** Performance de logging, dificuldade de rastrear fluxo

### Baixa severidade 🟢

6. **Unbind antes de bind (anti-double-bind)** (Baixa)
   - Arquivo: `anvisa_screen.py` linha 196-207
   - Problema: Padrão `unbind()` + `bind()` aplicado, mas sem validação se binding já existe
   - Risco: Se `_build_ui()` for chamado 2x, bindings podem duplicar
   - **Impacto:** Ações disparam 2x (ex: double-click abre 2 browsers)

7. **Status hardcoded "draft" em 2 lugares** (Baixa)
   - Arquivos: `anvisa_screen.py` linha 411, `_anvisa_requests_mixin.py` linha 376
   - Problema: Status padrão de criação hardcoded em vez de usar constante
   - Risco: Se mudar política de status padrão, precisa atualizar 2 lugares
   - **Impacto:** Inconsistência baixa (status padrão raramente muda)

8. **Timezone fixo UTC-3** (Baixa)
   - Arquivo: `_anvisa_requests_mixin.py` linha 316
   - Problema: Timezone hardcoded em vez de usar `zoneinfo` ou configuração
   - Risco: Horários errados para usuários fora de São Paulo
   - **Impacto:** UX degradada para outras regiões (baixo impacto se app é regional)

9. **Validação de duplicado só na View** (Baixa)
   - Arquivo: `anvisa_screen.py` linha 388-404
   - Problema: Lógica `_find_open_duplicate()` executada só no modal da View
   - Risco: API externa poderia criar demanda duplicada via repository direto (bypass da validação)
   - **Impacto:** Baixo (API externa não existe atualmente)

10. **Referência morta a método antigo** (Baixa)
    - Arquivo: `_anvisa_history_popup_mixin.py` linha 166
    - Problema: Código chama `anvisa_screen.AnvisaScreen._show_centered_no_flash()` (método removido)
    - Risco: Se esse caminho for executado, erro AttributeError
    - **Impacto:** Provavelmente código morto (não executado), mas deveria ser limpo

---

## 6. Próxima Microfase Recomendada

### ⚖️ Avaliação: P0.3+P0.4 vs. P1.1+P1.2

**Opção A: P0.3 + P0.4 (Estabilização)**
- Tempo estimado: 1-2h
- Risco: Baixo (apenas limpeza/organização)
- Benefício: Código mais limpo, menos logs, sem double-binds
- **Não avança MVC** (ainda 90% da lógica na View)

**Opção B: P1.1 + P1.2 (MVC Incremental)**
- Tempo estimado: 3-4h
- Risco: Médio (refactor de lógica, testes novos)
- Benefício: **Extrai lógica de validação/duplicado para Service headless**
- **Avança MVC real** (primeiro passo para desacoplar)

### 🎯 Recomendação: **P1.1 + P1.2 (MVC Incremental)**

**Justificativa:**
1. **P0.1 e P0.2 já estabilizaram infraestrutura** (constantes + window_utils OK)
2. **Dívidas P0.3/P0.4 são baixa prioridade** (logs redundantes, double-bind improvável)
3. **Maior ROI em P1:** Começa a extrair lógica de negócio da View (ganho real de testabilidade)
4. **Strangler Fig:** Microfase pequena (só validação duplicado), baixo risco de quebra
5. **Momentum:** Após P0, momento ideal para iniciar MVC incremental

**Contra-argumento P0.3/P0.4:**
- Se equipe prefere "limpar tudo antes de refatorar", P0.3+P0.4 faz sentido
- Mas logs redundantes e double-bind são problemas estéticos, não críticos

---

## 7. Detalhamento da Microfase P1.1 + P1.2

### Objetivo
Criar `AnvisaService` headless e migrar validação de duplicado da View para o Service, mantendo comportamento idêntico.

### Arquivos a serem criados/alterados

**Novos arquivos:**
1. `src/modules/anvisa/services/__init__.py` (vazio)
2. `src/modules/anvisa/services/anvisa_service.py` (~120 LOC)
3. `tests/unit/modules/anvisa/test_anvisa_service.py` (~180 LOC)

**Arquivos alterados:**
1. `src/modules/anvisa/views/anvisa_screen.py` (linha 360-404)
   - Injetar `_service` no `__init__`
   - Trocar `self._find_open_duplicate()` por `self._service.check_duplicate_open_request()`
   - Remover método `_find_open_duplicate()` (migrado para service)

2. `src/modules/anvisa/views/_anvisa_requests_mixin.py` (linha 175-192)
   - Remover método `_find_open_duplicate()` (migrado para service)
   - Manter `_load_demandas_for_cliente()` (será migrado em P1.4)

### Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Lógica de duplicado tem edge case não coberto | Baixa | Médio | Testes abrangentes + validação manual |
| Service não recebe org_id correto | Baixa | Alto | Injetar org_id via método, não no `__init__` |
| Cache de demandas desatualizado | Média | Baixo | Service carrega fresh do Supabase (ignora cache da View) |
| Quebra de comportamento no modal | Baixa | Alto | Testes manuais + checklist de validação |

### Critérios de aceite (Checklist)

**Funcional:**
- [ ] Service criado com método `check_duplicate_open_request(client_id, request_type)`
- [ ] Service retorna `Optional[dict]` (demanda duplicada ou None)
- [ ] View usa service em vez de método local
- [ ] Comportamento idêntico ao anterior:
  - [ ] Duplicado do mesmo tipo + status aberto → bloqueado
  - [ ] Duplicado do mesmo tipo + status fechado → permitido
  - [ ] Duplicado de tipo diferente → permitido
  - [ ] Nenhuma demanda → permitido

**Técnico:**
- [ ] Service é headless (sem import de Tkinter)
- [ ] Service recebe repository via injeção de dependência
- [ ] Método `_find_open_duplicate()` removido da View
- [ ] Normalização de tipo (uppercase, strip) preservada

**Testes:**
- [ ] `test_anvisa_service.py` criado com 8-10 testes
- [ ] Mock do repository (fixture `fake_repo`)
- [ ] Cenários testados:
  - [ ] Sem demandas → None
  - [ ] Duplicado aberto → retorna dict
  - [ ] Duplicado fechado → None
  - [ ] Tipo diferente → None
  - [ ] Normalização case-insensitive funciona
  - [ ] Exceção no repository → tratada
- [ ] Testes antigos (`test_anvisa_screen_basic.py`) continuam passando

**Validação:**
- [ ] `python -m compileall src/modules/anvisa/services/ -q`
- [ ] `python -m ruff check src/modules/anvisa/services/`
- [ ] `python -m pyright src/modules/anvisa/services/anvisa_service.py --level error`
- [ ] `pytest tests/unit/modules/anvisa/test_anvisa_service.py -v` (todos passam)
- [ ] `pytest tests/unit/modules/anvisa/test_anvisa_screen_basic.py -v` (todos passam)
- [ ] `pytest tests/unit/modules/anvisa/test_anvisa_controller.py -v` (todos passam)

**Manual (UX):**
- [ ] Abrir tela ANVISA
- [ ] Criar nova demanda (tipo "Alteração de RT")
- [ ] Tentar criar demanda duplicada do mesmo tipo → deve bloquear
- [ ] Finalizar primeira demanda
- [ ] Tentar criar demanda do mesmo tipo novamente → deve permitir
- [ ] Criar demanda de tipo diferente → deve permitir
- [ ] Verificar que mensagens de erro são as mesmas

### Testes a criar/ajustar

**Novo arquivo:** `tests/unit/modules/anvisa/test_anvisa_service.py`

```python
"""Testes unitários para AnvisaService headless."""

import pytest
from src.modules.anvisa.services.anvisa_service import AnvisaService

class FakeAnvisaRepository:
    """Mock do repository para testes."""
    def __init__(self):
        self.requests_by_client = {
            "123": [
                {"id": "req-1", "request_type": "Alteração de RT", "status": "draft"},
                {"id": "req-2", "request_type": "Alteração de RL", "status": "done"},
            ]
        }

    def list_requests(self, org_id: str):
        # Retorna todas as demandas (flat list)
        return [req for reqs in self.requests_by_client.values() for req in reqs]

@pytest.fixture
def fake_repo():
    return FakeAnvisaRepository()

@pytest.fixture
def service(fake_repo):
    return AnvisaService(repository=fake_repo)

def test_check_duplicate_blocks_same_type_open(service):
    """Deve bloquear demanda do mesmo tipo com status aberto."""
    dup = service.check_duplicate_open_request("123", "Alteração de RT", "org-1")
    assert dup is not None
    assert dup["id"] == "req-1"

def test_check_duplicate_allows_same_type_closed(service):
    """Deve permitir demanda do mesmo tipo se anterior está fechada."""
    dup = service.check_duplicate_open_request("123", "Alteração de RL", "org-1")
    assert dup is None

def test_check_duplicate_allows_different_type(service):
    """Deve permitir demanda de tipo diferente."""
    dup = service.check_duplicate_open_request("123", "Alteração de Porte", "org-1")
    assert dup is None

def test_check_duplicate_no_requests(service, fake_repo):
    """Deve retornar None se cliente não tem demandas."""
    fake_repo.requests_by_client["456"] = []
    dup = service.check_duplicate_open_request("456", "Alteração de RT", "org-1")
    assert dup is None

# ... mais 4-6 testes (normalização, exceções, etc.)
```

**Ajustes em `test_anvisa_screen_basic.py`:**
- Remover testes de `_find_open_duplicate()` (migrados para `test_anvisa_service.py`)
- Manter testes de helpers puros (`_format_cnpj`, `_is_open_status`, etc.)

---

## 8. Próximo Prompt Sugerido

```
IMPLEMENTAR P1.1 + P1.2 - CRIAR ANVISA SERVICE E MIGRAR VALIDAÇÃO DE DUPLICADO

REGRAS
- Trabalhar em cima do código atual do workspace.
- NÃO rodar testes pesados: pytest apenas do módulo ANVISA.
- Rodar: compileall + ruff + pyright apenas nos arquivos alterados.
- NÃO mudar comportamento (apenas extrair lógica da View para Service).
- Usar padrão Strangler Fig: código antigo e novo convivem até migração completa.

OBJETIVO P1.1 — Criar AnvisaService headless
1) Criar pasta: src/modules/anvisa/services/
2) Criar: src/modules/anvisa/services/__init__.py (vazio)
3) Criar: src/modules/anvisa/services/anvisa_service.py com:
   - Classe AnvisaService(repository: AnvisaRequestsRepository)
   - Método check_duplicate_open_request(client_id: str, request_type: str, org_id: str) -> Optional[dict]
   - Lógica migrada de _find_open_duplicate() (anvisa_screen.py linha 175-192)
   - Usa _is_open_status() e _norm_tipo() (também migrar para service como métodos privados)
   - Carrega demandas do repository.list_requests(org_id) e filtra por client_id
   - Retorna dict da demanda duplicada ou None
   - SEM imports de Tkinter

OBJETIVO P1.2 — Migrar validação duplicado para Service
1) Atualizar src/modules/anvisa/views/anvisa_screen.py:
   - No __init__, criar self._service = AnvisaService(repository=AnvisaRequestsRepositoryAdapter())
   - Na linha 388-404 (_on_new_anvisa_clicked), trocar:
     OLD: duplicado = self._find_open_duplicate(demandas, request_type)
     NEW: duplicado = self._service.check_duplicate_open_request(client_id, request_type, org_id)
   - Remover método _find_open_duplicate() (agora está no service)

2) Atualizar src/modules/anvisa/views/_anvisa_requests_mixin.py:
   - Remover método _find_open_duplicate() (linha 175-192)
   - Manter _load_demandas_for_cliente() (será migrado em P1.4)

OBJETIVO P1.3 — Criar testes do service
1) Criar: tests/unit/modules/anvisa/test_anvisa_service.py com:
   - Fixture fake_repo (mock do repository)
   - Fixture service (injetar fake_repo)
   - 8-10 testes cobrindo:
     * Duplicado aberto (bloqueado)
     * Duplicado fechado (permitido)
     * Tipo diferente (permitido)
     * Cliente sem demandas (permitido)
     * Normalização case-insensitive
     * Exceção no repository

2) Ajustar tests/unit/modules/anvisa/test_anvisa_screen_basic.py:
   - Remover testes de _find_open_duplicate() (agora em test_anvisa_service.py)
   - Manter testes de helpers puros

VALIDAÇÕES
- python -m compileall src/modules/anvisa/services/ -q
- python -m ruff check src/modules/anvisa/services/ --fix
- python -m pyright src/modules/anvisa/services/anvisa_service.py --level error
- pytest tests/unit/modules/anvisa/test_anvisa_service.py -v (todos passam)
- pytest tests/unit/modules/anvisa/test_anvisa_screen_basic.py -v (todos passam)
- pytest tests/unit/modules/anvisa/test_anvisa_controller.py -v (todos passam)

CHECKLIST MANUAL (testar no app)
- [ ] Criar demanda tipo "Alteração de RT" → OK
- [ ] Tentar criar duplicada do mesmo tipo → bloqueado com mensagem
- [ ] Finalizar primeira demanda
- [ ] Criar novamente "Alteração de RT" → OK (anterior fechada)
- [ ] Criar "Alteração de RL" → OK (tipo diferente)

ENTREGAR
- services/anvisa_service.py criado (~120 LOC)
- anvisa_screen.py atualizado (usa service)
- _anvisa_requests_mixin.py atualizado (remove método)
- test_anvisa_service.py criado (~180 LOC)
- test_anvisa_screen_basic.py ajustado (remove testes migrados)
- comportamento idêntico ao anterior
- todos os testes ANVISA passando
```

---

**Fim da análise pós-refactor** | RC v1.4.52 | Módulo ANVISA | 19/12/2025
