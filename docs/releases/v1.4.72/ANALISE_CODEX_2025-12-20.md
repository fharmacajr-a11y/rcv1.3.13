# ANÁLISE CODEX - RC Gestor de Clientes

**Versão:** v1.4.72  
**Data:** 20 de dezembro de 2025  
**Tipo:** Análise rápida de bugs + melhorias + próximos módulos de cobertura

---

## 📊 Sumário Executivo

Análise estática realizada via compileall, ruff, bandit e busca manual de padrões. Identificados:
- **9 imports não utilizados** (Ruff F401 - baixo risco, fácil fix)
- **7 try/except pass** (Bandit B110 - médio risco, swallow de erros)
- **3 asserts em código produção** (Bandit B101 - baixo risco, removido em -O)
- **2 subprocess.Popen** (Bandit B603 - já mitigado com nosec + shutil.which)
- **Threading/GUI**: Padrão correto identificado (app.after(0) para UI updates)
- **Cloud-Only**: Guardrails implementados e consistentes

### Smoke Checks - Status

✅ **Compileall (src)**: Sem erros de sintaxe  
⚠️ **Ruff**: 9 imports não utilizados em testes (fixável com --fix)  
⚠️ **Bandit**: 7 try/except pass + 3 asserts (baixa/média severidade)  
✅ **Pyright**: Não executado (pesado no ambiente)

---

## 🐛 Bugs Potenciais e Melhorias

### A) Thread/GUI (✅ Status: OK)

#### Padrão Correto Identificado

**Arquivo:** [src/app_status.py](src/app_status.py#L131)  
**Risco:** ✅ BAIXO (implementado corretamente)

```python
# Thread worker
def worker():
    # ... probe network ...
    app.after(0, lambda s=current_status: _apply_status(app, s))

# app.after(0) garante que UI updates rodem no main thread
```

**Análise:** O código usa corretamente `app.after(0)` para agendar updates de UI da thread worker. Padrão recomendado pela documentação do Tkinter.

**Locais verificados:**
- [src/modules/main_window/views/main_window.py](src/modules/main_window/views/main_window.py#L553): `threading.Thread + app.after(0)` ✅
- [src/modules/uploads/uploader_supabase.py](src/modules/uploads/uploader_supabase.py#L328): `Thread + _safe_after(0)` ✅
- [src/modules/main_window/app_actions.py](src/modules/main_window/app_actions.py#L358): `Thread + self._app.after(0)` ✅

**Ação:** Nenhuma. Implementação segura.

---

### B) Cloud-Only / RC_NO_LOCAL_FS (✅ Status: Consistente)

#### Guardrails Implementados

**Arquivo:** [src/utils/helpers/cloud_guardrails.py](src/utils/helpers/cloud_guardrails.py)  
**Risco:** ✅ BAIXO (guardrails ativas)

```python
def check_cloud_only_block(operation_name: str = "Esta função") -> bool:
    if CLOUD_ONLY:
        messagebox.showinfo(...) # Bloqueia operação
        return True
    return False
```

**Locais de uso:**
- [src/utils/file_utils/path_utils.py](src/utils/file_utils/path_utils.py#L44): `open_folder()` bloqueado ✅
- [src/utils/file_utils/bytes_utils.py](src/utils/file_utils/bytes_utils.py#L191): `if not CLOUD_ONLY` ✅
- [src/utils/themes.py](src/utils/themes.py#L16): `NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"` ✅

**Ação:** Nenhuma. Guardrails consistentes.

---

### C) Robustez - Try/Except Pass (⚠️ Ação Recomendada)

#### C.1) Swallow de Exceções em Notificações

**Arquivo:** [src/core/notifications_service.py](src/core/notifications_service.py#L137)  
**Risco:** ⚠️ MÉDIO (swallow silencioso, dificulta debug)

```python
try:
    return (display_name, initial)
except Exception:
    pass  # ❌ Swallow sem log
```

**Impacto:** Falhas no parse de nome de usuário são silenciadas. Não é crítico (funcionalidade secundária), mas dificulta troubleshooting.

**Sugestão:**
```python
except Exception as exc:
    log.debug("Falha ao extrair iniciais de %s: %s", display_name, exc)
    return (display_name, "??")
```

**Prioridade:** MÉDIA (quick win, melhora observabilidade)  
**Teste:** `tests/unit/core/test_notifications_service.py` (criar/estender)

---

#### C.2) Swallow em Navegação de Tree (Anvisa)

**Arquivo:** [src/modules/anvisa/views/_anvisa_handlers_mixin.py](src/modules/anvisa/views/_anvisa_handlers_mixin.py#L331)  
**Risco:** ⚠️ BAIXO (comportamento esperado documentado)

```python
try:
    self.tree_requests.see(client_id)
except Exception:
    pass  # Ignorar se cliente não existir mais (todas demandas excluídas)
```

**Análise:** Comentário explica comportamento esperado (race condition: cliente deletado entre listagem e foco). Swallow é aceitável aqui.

**Ação:** Opcional - adicionar log.debug se quiser observabilidade extra.

---

#### C.3) Swallow em PDF Preview

**Arquivo:** [src/modules/pdf_preview/views/main_window.py](src/modules/pdf_preview/views/main_window.py#L245)  
**Risco:** ⚠️ BAIXO (operação de cleanup de modal)

```python
try:
    self.grab_release()
except Exception:
    pass  # ❌ Swallow sem log
```

**Impacto:** Falha ao liberar grab modal é ignorada. Pode causar lock de UI em casos raros.

**Sugestão:**
```python
except Exception as exc:
    log.debug("Falha ao liberar grab modal: %s", exc)
```

**Prioridade:** BAIXA (edge case)

---

#### C.4) Swallow em Main Window Controller

**Arquivo:** [src/modules/main_window/controller.py](src/modules/main_window/controller.py#L317)  
**Risco:** ⚠️ MÉDIO (mascara erro de estado da topbar)

```python
try:
    app._topbar.set_is_hub(False)
except Exception:
    pass  # ❌ Swallow sem log
```

**Impacto:** Se topbar falha em atualizar estado, erro é silenciado. Pode causar inconsistência visual.

**Sugestão:**
```python
except Exception as exc:
    log.warning("Falha ao atualizar estado da topbar: %s", exc, exc_info=True)
```

**Prioridade:** MÉDIA (quick win)  
**Teste:** `tests/unit/modules/main_window/test_controller.py` (criar/estender)

---

### D) Segurança - Subprocess (✅ Status: Mitigado)

#### Subprocess com Paths Controlados

**Arquivo:** [src/modules/uploads/service.py](src/modules/uploads/service.py#L413)  
**Risco:** ✅ BAIXO (mitigado com nosec + shutil.which)

```python
if sys.platform.startswith("win"):
    os.startfile(local_path)  # nosec B606
elif sys.platform == "darwin":
    open_cmd = shutil.which("open")  # ✅ Resolve full path
    subprocess.Popen([open_cmd, local_path])  # nosec B603
else:
    xdg_cmd = shutil.which("xdg-open")  # ✅ Resolve full path
    subprocess.Popen([xdg_cmd, local_path])  # nosec B603
```

**Análise:**
- ✅ Usa `shutil.which()` para resolver caminho completo (evita PATH injection)
- ✅ `local_path` é arquivo temporário criado pelo app (não input externo direto)
- ✅ Marcado com `# nosec` após revisão de segurança

**Ação:** Nenhuma. Implementação segura.

---

### E) Asserts em Produção (⚠️ Ação Recomendada)

**Arquivo:** [src/modules/uploads/views/action_bar.py](src/modules/uploads/views/action_bar.py#L55)  
**Risco:** ⚠️ BAIXO (removido em -O, mas não é best practice)

```python
self.btn_download = ttk.Button(...)
assert self.btn_download is not None  # type narrowing para Pyright
```

**Impacto:** Em Python com `-O` (optimize), asserts são removidos. Se código depende deles em runtime, pode quebrar.

**Análise:** Aqui são usados apenas para type narrowing (Pyright). Não há lógica de negócio.

**Sugestão:** Substituir por type annotation (mais idiomático):
```python
self.btn_download: ttk.Button = ttk.Button(...)
# ou usar cast
from typing import cast
self.btn_download = cast(ttk.Button, ttk.Button(...))
```

**Prioridade:** BAIXA (quick win, melhora idiomaticidade)  
**Locais:** 3 instâncias em [action_bar.py](src/modules/uploads/views/action_bar.py) (linhas 55, 63, 69)

---

### F) Imports Não Utilizados (✅ Quick Fix)

**Ruff F401** - 9 ocorrências em testes:
- `tests/unit/core/test_notifications_minimal.py:13` - `datetime.timezone`
- `tests/unit/core/test_notifications_repository_coverage.py:12` - `typing.Any`
- `tests/unit/infra/repositories/test_anvisa_repository_coverage.py:13` - `unittest.mock.Mock`
- `tests/unit/infra/test_db_client_cobertura_qa.py:10` - `os`
- `tests/unit/infra/test_db_client_cobertura_qa.py:14` - `unittest.mock.patch`
- `tests/unit/infra/test_db_client_cobertura_qa.py:263` - `infra.http.retry`
- `tests/unit/modules/anvisa/test_anvisa_errors.py:4` - `unittest.mock.MagicMock`
- `tests/unit/modules/anvisa/test_anvisa_errors.py:6` - `pytest`
- `tests/unit/modules/anvisa/test_anvisa_logging.py:5` - `pytest`

**Fix:** `python -m ruff check tests --fix`  
**Prioridade:** BAIXA (não afeta funcionalidade, apenas limpeza de código)

---

## 📋 Próximos Módulos para Cobertura (TEST-001 + QA-003)

### Critérios de Priorização

1. **Criticidade:** Lógica de negócio core (auth, CRUD, validações)
2. **Testabilidade:** Funções puras/headless (evitar GUI pesada)
3. **Custo/Benefício:** Testes rápidos, alto ROI
4. **Gaps Atuais:** Módulos com baixa cobertura ou sem testes

---

### 1. 🔐 **Core Auth (core/auth/auth.py)** - ALTA PRIORIDADE

**Por que:**
- Lógica de segurança crítica (hash de senha, autenticação)
- Funções puras/testáveis (pbkdf2_hash, authenticate_user)
- Risco alto se quebrar (lock out de usuários)

**Cenários de Teste:**
- `pbkdf2_hash()`: verificar formato, consistência, salt diferente
- `create_user()`: criação, update de senha, username duplicado
- `authenticate_user()`: login válido/inválido, usuário inexistente
- `ensure_users_db()`: criação de tabela, idempotência

**Arquivo de Teste:** `tests/unit/core/auth/test_auth.py`

**Comando:**
```bash
pytest -q tests/unit/core/auth/test_auth.py
```

**Dependências:** Mock de `infra.supabase_client`, sqlite em memória

---

### 2. 📝 **Validadores (utils/validators.py)** - ALTA PRIORIDADE

**Por que:**
- Funções puras (entrada/saída determinística)
- Usadas em todos os formulários (CNPJ, WhatsApp, duplicatas)
- Já tem testes parciais, expandir cobertura

**Cenários de Teste:**
- `is_valid_cnpj()`: CNPJ válido/inválido, edge cases (000000, 111111)
- `is_valid_whatsapp_br()`: formatos variados (+55, 55, 11 dígitos)
- `check_duplicates()`: CNPJ/Razão duplicados, skip_id
- `validate_cliente_payload()`: combinações de campos vazios/válidos

**Arquivo de Teste:** `tests/unit/utils/test_validators.py` (expandir)

**Comando:**
```bash
pytest -q tests/unit/utils/test_validators.py
```

**Dependências:** Nenhuma (funções puras)

---

### 3. 🗄️ **Clientes Service (core/services/clientes_service.py)** - MÉDIA PRIORIDADE

**Por que:**
- CRUD core (create/update/delete clientes)
- Lógica de duplicatas (CNPJ/Razão)
- Orquestra db_manager + validadores + auditoria

**Cenários de Teste:**
- `_exists_duplicate()`: detectar CNPJ/Razão duplicados, skip_id
- `salvar_cliente()`: criação, update, bloqueio de duplicatas
- `_pasta_do_cliente()`: paths corretos, modo CLOUD_ONLY
- `_normalize_payload()`: sanitização de campos

**Arquivo de Teste:** `tests/unit/core/services/test_clientes_service.py`

**Comando:**
```bash
pytest -q tests/unit/core/services/test_clientes_service.py
```

**Dependências:** Mock de `core.db_manager`, `config.paths.CLOUD_ONLY`

---

### 4. 🔍 **Search (core/search/search.py)** - MÉDIA PRIORIDADE

**Por que:**
- Função headless (busca por CNPJ/nome/razão)
- Usada em autocomplete e buscas rápidas
- Testável com lista fixa de clientes

**Cenários de Teste:**
- `search_clientes()`: busca por CNPJ (parcial/completo)
- Busca por nome fantasia (case insensitive)
- Busca por razão social (normalização)
- Busca vazia, nenhum resultado

**Arquivo de Teste:** `tests/unit/core/search/test_search.py`

**Comando:**
```bash
pytest -q tests/unit/core/search/test_search.py
```

**Dependências:** Mock de `core.db_manager.list_clientes()`

---

### 5. 📦 **DB Manager (core/db_manager/db_manager.py)** - BAIXA PRIORIDADE

**Por que:**
- Já testado indiretamente via serviços
- Integração com Supabase (difícil mockar tudo)
- Priorizar testes E2E em ambiente de staging

**Cenários de Teste:**
- `_to_cliente()`: conversão de dict para Cliente
- `_resolve_order()`: mapeamento de order_by
- Funções CRUD: insert/update/delete (mock Supabase)

**Arquivo de Teste:** `tests/unit/core/db_manager/test_db_manager.py`

**Comando:**
```bash
pytest -q tests/unit/core/db_manager/test_db_manager.py
```

**Dependências:** Mock de `infra.supabase_client.supabase`

**Nota:** Considerar testes E2E em staging ao invés de unit tests pesados.

---

### 6. 🌐 **Network Utils (src/utils/network.py)** - BAIXA PRIORIDADE

**Por que:**
- Funções de probe de rede (check_internet_access)
- Testável com mock de requests
- Já usado em app_status.py (coberto indiretamente)

**Cenários de Teste:**
- `check_internet_access()`: modo CLOUD_ONLY, timeout, URL inválida
- Retornos True/False conforme disponibilidade

**Arquivo de Teste:** `tests/unit/utils/test_network.py`

**Comando:**
```bash
pytest -q tests/unit/utils/test_network.py
```

**Dependências:** Mock de `requests.get`, `config.paths.CLOUD_ONLY`

---

## 🛠️ Patches Mínimos Recomendados

### Patch 1: Adicionar Logging em Try/Except Pass (Notifications Service)

**Arquivo:** [src/core/notifications_service.py](src/core/notifications_service.py#L137)

**Antes:**
```python
try:
    return (display_name, initial)
except Exception:
    pass
```

**Depois:**
```python
try:
    return (display_name, initial)
except Exception as exc:
    log.debug("Falha ao extrair iniciais de %s: %s", display_name, exc)
    return (display_name, "??")
```

**Teste:** Verificar que fallback "??" é retornado em caso de erro  
**Comando:** `pytest -q tests/unit/core/test_notifications_service.py` (criar teste)

---

### Patch 2: Adicionar Logging em Try/Except Pass (Main Window Controller)

**Arquivo:** [src/modules/main_window/controller.py](src/modules/main_window/controller.py#L317)

**Antes:**
```python
try:
    app._topbar.set_is_hub(False)
except Exception:
    pass
```

**Depois:**
```python
try:
    app._topbar.set_is_hub(False)
except Exception as exc:
    log.warning("Falha ao atualizar estado da topbar: %s", exc, exc_info=True)
```

**Teste:** Mock de `app._topbar.set_is_hub()` levantando exceção  
**Comando:** `pytest -q tests/unit/modules/main_window/test_controller.py` (criar teste)

---

### Patch 3: Substituir Asserts por Type Annotations (Action Bar)

**Arquivo:** [src/modules/uploads/views/action_bar.py](src/modules/uploads/views/action_bar.py)

**Antes (linha 55):**
```python
self.btn_download = ttk.Button(left, text="Baixar", command=on_download, bootstyle="info")
assert self.btn_download is not None  # type narrowing para Pyright
```

**Depois:**
```python
from typing import cast
self.btn_download = cast(ttk.Button, ttk.Button(left, text="Baixar", command=on_download, bootstyle="info"))
```

**OU (mais simples):**
```python
self.btn_download: ttk.Button = ttk.Button(left, text="Baixar", command=on_download, bootstyle="info")
```

**Aplicar em:** Linhas 55, 63, 69  
**Teste:** Verificar que Pyright não reporta erros de tipo  
**Comando:** `pyright src/modules/uploads/views/action_bar.py`

---

## 📝 Resumo de Ações

### Quick Wins (Custo Baixo, ROI Alto)

1. ✅ **Fix Imports Não Utilizados**: `ruff check tests --fix` (1 comando, 0 risco)
2. ⚠️ **Adicionar Logging em Try/Except**: 2 patches mínimos (notifications_service, controller)
3. ⚠️ **Substituir Asserts**: 3 linhas em action_bar.py (melhora idiomaticidade)

### Testes Prioritários (Próximas Sprints)

1. 🔐 **core/auth/auth.py** - Segurança crítica
2. 📝 **utils/validators.py** - Funções puras, alta reutilização
3. 🗄️ **core/services/clientes_service.py** - CRUD core

### Análises Futuras (QA-003)

- Executar Pyright após patches de type hints
- Revisar cobertura de testes integrados (E2E) para DB Manager
- Considerar testes de carga para app_status.py (worker thread)

---

## 📚 Referências

- [Tkinter Thread Safety](https://docs.python.org/3/library/tkinter.html#thread-safety) - Documentação oficial
- [Bandit B110](https://bandit.readthedocs.io/en/1.8.6/plugins/b110_try_except_pass.html) - Try/Except Pass
- [Ruff F401](https://docs.astral.sh/ruff/rules/unused-import/) - Unused Imports
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

## ✅ TEST-008: Uploads Components Helpers

**Data:** 20 de dezembro de 2025  
**Alvo:** `src/modules/uploads/components/helpers.py`

### Testes Adicionados

**Arquivo:** `tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py`

**Total:** 34 testes (100% aprovados)

**Cobertura:**
- `_cnpj_only_digits`: 5 testes (None, vazio, apenas dígitos, formatado, especiais)
- `format_cnpj_for_display`: 5 testes (14 dígitos, menos/mais dígitos, vazio, não numérico)
- `strip_cnpj_from_razao`: 13 testes (vazio, None, sem CNPJ, separadores diversos, meio, trim)
- `get_clients_bucket`: 1 teste (retorno constante)
- `client_prefix_for_id`: 3 testes (normal, client_id=0, org_id vazio)
- `get_current_org_id`: 7 testes (mock Supabase, success/fail, exceções)

### Comando Executado

```bash
pytest -q tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py
# Output: 34 passed in 0.15s
```

### Verificação de Sanidade

```bash
python -m compileall src/modules/uploads/components/helpers.py tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py
python -m ruff check src/modules/uploads/components/helpers.py tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py
# All checks passed!
```

### Commit

```
a482e8d test: TEST-008 uploads components helpers
```

---

**Fim do Relatório CODEX - v1.4.72**  
*Análise realizada em: 20 de dezembro de 2025*
