# 🔍 Análise de Melhorias do Projeto - RC Gestor de Clientes

**Versão do Documento:** 1.0  
**Data de Geração:** 22 de dezembro de 2025  
**Versão do Projeto:** 1.4.72

---

## 📋 Índice

1. [Resumo Executivo](#resumo-executivo)
2. [Bugs Potenciais](#1-bugs-potenciais)
3. [Pontos de Melhoria em Performance](#2-pontos-de-melhoria-em-performance)
4. [Sugestões de Refatoração](#3-sugestões-de-refatoração)
5. [Issues de Segurança](#4-issues-de-segurança)
6. [Melhorias em Testes e Qualidade](#5-melhorias-em-testes-e-qualidade)
7. [Otimização de Dependências](#6-otimização-de-dependências-e-configurações)
8. [Melhorias na UI/UX](#7-melhorias-na-uiux)
9. [Outras Sugestões Gerais](#8-outras-sugestões-gerais)

---

## Resumo Executivo

### Estatísticas de Issues Identificadas

| Categoria | Alta | Média | Baixa | Total |
|-----------|------|-------|-------|-------|
| Bugs Potenciais | 3 | 5 | 4 | 12 |
| Performance | 2 | 4 | 3 | 9 |
| Refatoração | 1 | 6 | 5 | 12 |
| Segurança | 4 | 3 | 2 | 9 |
| Testes/Qualidade | 2 | 4 | 3 | 9 |
| Dependências | 2 | 3 | 2 | 7 |
| UI/UX | 1 | 3 | 4 | 8 |
| **Total** | **15** | **28** | **23** | **66** |

### Prioridade de Ação Recomendada

1. 🔴 **Crítico (Imediato):** Issues de segurança e bugs de alta severidade
2. 🟠 **Alto (Sprint atual):** Performance crítica e refatorações bloqueantes  
3. 🟡 **Médio (Próximo sprint):** Melhorias de qualidade e UX
4. 🟢 **Baixo (Backlog):** Otimizações e melhorias incrementais

---

## 1. Bugs Potenciais

### 🔴 Alta Severidade

#### BUG-001: Exceções Silenciadas sem Log em `app_status.py`

**Arquivo:** `src/app_status.py` (linhas 39, 48, 68, 75, 89, 98, 127, 132)  
**Problema:** Múltiplos blocos `except Exception:` sem logging ou re-raise, mascarando erros críticos.

**Antes:**
```python
def get_status():
    try:
        return _fetch_status()
    except Exception:
        pass  # Erro silenciado!
```

**Depois:**
```python
import logging
log = logging.getLogger(__name__)

def get_status():
    try:
        return _fetch_status()
    except Exception as exc:
        log.warning("Falha ao obter status: %s", exc, exc_info=True)
        return None  # Retorno explícito
```

---

#### BUG-002: Condição de Corrida em Cache Global de `_LAST_CLIENTS_COUNT`

**Arquivo:** `src/core/services/clientes_service.py` (linhas 30-85)  
**Problema:** A variável global `_LAST_CLIENTS_COUNT` pode ter leituras inconsistentes em cenários multi-thread, mesmo com lock parcial.

**Antes:**
```python
_LAST_CLIENTS_COUNT = 0
_clients_lock = threading.Lock()

def count_clients(...):
    global _LAST_CLIENTS_COUNT
    # ...
    total: int = _count_clients_raw()  # Fora do lock!
    with _clients_lock:
        _LAST_CLIENTS_COUNT = int(total)
        return _LAST_CLIENTS_COUNT
```

**Depois:**
```python
from dataclasses import dataclass
from threading import Lock

@dataclass
class ClientsCache:
    count: int = 0
    lock: Lock = field(default_factory=Lock)

_clients_cache = ClientsCache()

def count_clients(...):
    with _clients_cache.lock:
        try:
            total = _count_clients_raw()
            _clients_cache.count = total
        except Exception:
            pass  # Usa valor em cache
        return _clients_cache.count
```

---

#### BUG-003: Possível Referência Nula em `resolve_user_context`

**Arquivo:** `src/modules/passwords/service.py` (linhas 140-175)  
**Problema:** Se `supabase.auth.get_user()` retornar estrutura inesperada, `user_id` pode ser `None` e causar erro downstream.

**Antes:**
```python
def resolve_user_context(main_window: Any) -> PasswordsUserContext:
    user = supabase.auth.get_user()
    user_obj = getattr(user, "user", None) or user
    if isinstance(user_obj, dict):
        user_id = user_obj.get("id") or user_obj.get("uid")
    else:
        user_id = getattr(user_obj, "id", None)

    if not user_id:
        raise RuntimeError("Usuário não autenticado...")
```

**Depois:**
```python
def resolve_user_context(main_window: Any) -> PasswordsUserContext:
    try:
        user_response = supabase.auth.get_user()
    except Exception as exc:
        raise RuntimeError(f"Falha ao obter usuário do Supabase: {exc}") from exc

    user_id = _extract_user_id(user_response)
    if not user_id:
        raise RuntimeError("Usuário não autenticado para acessar senhas.")
    # ...

def _extract_user_id(response: Any) -> str | None:
    """Extrai user_id de forma segura de múltiplos formatos de resposta."""
    if response is None:
        return None
    user_obj = getattr(response, "user", response)
    if isinstance(user_obj, dict):
        return user_obj.get("id") or user_obj.get("uid")
    return getattr(user_obj, "id", None)
```

---

### 🟠 Média Severidade

| ID | Descrição | Arquivo | Linha |
|----|-----------|---------|-------|
| BUG-004 | `_continue_after_splash` não trata exceção se `show_hub_screen()` falhar após login | `src/app_gui.py` | 140-150 |
| BUG-005 | Loop de polling pode nunca parar se `screen.state.live_sync_on` for modificado durante execução | `src/modules/hub/controller.py` | 37-55 |
| BUG-006 | `_format_timestamp` pode falhar com strings vazias ou `None` | `src/modules/hub/controller.py` | 180 |
| BUG-007 | Race condition entre `cancel_poll` e `schedule_poll` em `hub/controller.py` | `src/modules/hub/controller.py` | 50-65 |
| BUG-008 | `extrair_dados_cartao_cnpj_em_pasta` não valida se `base_dir` existe antes de processar | `src/modules/clientes/service.py` | 120-170 |

### 🟢 Baixa Severidade

| ID | Descrição | Arquivo | Linha |
|----|-----------|---------|-------|
| BUG-009 | Possível `KeyError` em `valores.get("Raz?o Social")` com encoding incorreto | `src/modules/clientes/service.py` | 178 |
| BUG-010 | `_safe_messagebox` ignora retorno de dialogs de confirmação | `src/app_core.py` | 45-55 |
| BUG-011 | Cleanup de temporários no startup pode falhar silenciosamente | `src/app_gui.py` | 68-72 |
| BUG-012 | `pbkdf2_hash` não valida tamanho mínimo de senha | `src/core/auth/auth.py` | 125-145 |

---

## 2. Pontos de Melhoria em Performance

### 🔴 Alta Severidade

#### PERF-001: Múltiplas Queries ao Supabase em Loop

**Arquivo:** `src/core/services/clientes_service.py` (linhas 135-165)  
**Problema:** `checar_duplicatas_info` itera sobre `list_clientes()` inteiro para cada verificação de duplicata.

**Impacto:** O(n) queries para cada cliente verificado, degradação severa com base de clientes grande.

**Antes:**
```python
def checar_duplicatas_info(...):
    razao_conflicts: list[Any] = []
    if razao_norm:
        for cliente in list_clientes():  # Carrega TODOS os clientes!
            if exclude_id and cliente.id == exclude_id:
                continue
            # ... filtragem em Python
```

**Depois:**
```python
def checar_duplicatas_info(...):
    if razao_norm:
        # Query direta com filtro no banco
        razao_conflicts = exec_postgrest(
            supabase.table("clients")
            .select("id, razao_social, cnpj, cnpj_norm")
            .eq("razao_social_norm", razao_norm)
            .is_("deleted_at", "null")
            .neq("id", exclude_id or 0)
        ).data or []
```

---

#### PERF-002: Health Check Bloqueante no Startup

**Arquivo:** `infra/supabase/db_client.py` (linhas 95-190)  
**Problema:** Thread de health check com `time.sleep()` bloqueante pode atrasar operações iniciais.

**Sugestão:**
```python
import asyncio

async def _async_health_check(client: Client) -> bool:
    """Health check não-bloqueante."""
    try:
        async with asyncio.timeout(5.0):
            res = await asyncio.to_thread(
                lambda: exec_postgrest(client.rpc("ping"))
            )
            return res.data == "ok"
    except asyncio.TimeoutError:
        return False
```

---

### 🟠 Média Severidade

| ID | Descrição | Arquivo | Sugestão |
|----|-----------|---------|----------|
| PERF-003 | `list_passwords` carrega todas as senhas em memória | `infra/repositories/passwords_repository.py` | Implementar paginação com `.range()` |
| PERF-004 | `group_passwords_by_client` reprocessa toda a lista para cada filtro | `src/modules/passwords/service.py` | Usar índice/cache por `client_id` |
| PERF-005 | Splash screen com `time.monotonic()` em loop | `src/ui/splash.py` | Usar `after()` do Tkinter |
| PERF-006 | `normalize_key_for_storage` importa módulo a cada chamada | `adapters/storage/supabase_storage.py` | Mover import para nível de módulo |

### 🟢 Baixa Severidade

| ID | Descrição | Arquivo | Sugestão |
|----|-----------|---------|----------|
| PERF-007 | PBKDF2 com 1M iterações no teste (lento) | `src/core/auth/auth.py` | Já tem env var, documentar melhor |
| PERF-008 | `_http_check` tenta 3 URLs sequencialmente | `src/utils/network.py` | Usar `asyncio.gather` para paralelo |
| PERF-009 | Cache de tema lê arquivo do disco a cada acesso | `src/utils/themes.py` | Já tem cache, mas pode usar TTL |

---

## 3. Sugestões de Refatoração

### 🔴 Alta Severidade

#### REF-001: Classe `App` Muito Grande (God Class)

**Arquivo:** `src/modules/main_window/views/main_window.py` (652 linhas)  
**Problema:** Classe `App` acumula responsabilidades demais: navegação, status, sessão, temas, health check.

**Sugestão:** Aplicar padrão Facade com delegação para classes especializadas.

```python
# Antes: tudo em App
class App(tb.Window):
    def show_hub_screen(self): ...
    def _handle_status_update(self): ...
    def _get_user_cached(self): ...
    def _set_theme(self): ...
    # ... 600+ linhas

# Depois: responsabilidades delegadas
class App(tb.Window):
    def __init__(self):
        self._navigator = NavigationManager(self)
        self._status = StatusManager(self)
        self._session = SessionManager(self)
        self._theme = ThemeManager(self)

    def show_hub_screen(self):
        self._navigator.navigate_to("hub")
```

---

### 🟠 Média Severidade

| ID | Descrição | Arquivo | Padrão Sugerido |
|----|-----------|---------|-----------------|
| REF-002 | Código duplicado em `checar_duplicatas_*` | `src/modules/clientes/service.py` | Extrair validador reutilizável |
| REF-003 | Múltiplos `try/except Exception` sem tipagem | Vários arquivos | Criar exceções de domínio |
| REF-004 | `_normalize_payload` com muitos `_v()` calls | `src/core/services/clientes_service.py` | Usar Pydantic model |
| REF-005 | `hub/controller.py` com funções > 80 linhas | `src/modules/hub/controller.py` | Quebrar em funções menores |
| REF-006 | Imports circulares potenciais entre módulos | `src/modules/*` | Usar lazy imports ou interfaces |
| REF-007 | Variáveis globais mutáveis em `supabase_repo.py` | `data/supabase_repo.py` | Usar Singleton pattern |

### 🟢 Baixa Severidade

| ID | Descrição | Arquivo | Sugestão |
|----|-----------|---------|----------|
| REF-008 | Docstrings com encoding quebrado (caracteres `?`) | `src/core/services/notes_service.py` | Corrigir encoding UTF-8 |
| REF-009 | Magic numbers em timeouts | Vários | Extrair para constantes |
| REF-010 | `# noqa: BLE001` em excesso | `src/modules/hub/controller.py` | Refatorar para exceções específicas |
| REF-011 | Aliases desnecessários (`list_auditorias = fetch_auditorias`) | `src/modules/auditoria/service.py` | Escolher um nome e usar consistentemente |
| REF-012 | Múltiplos `NamedTuple` e `TypedDict` para mesmos dados | Vários | Unificar tipos de domínio |

---

## 4. Issues de Segurança

### 🔴 Alta Severidade

#### SEC-001: Chave de Criptografia em Memória

**Arquivo:** `security/crypto.py` (linhas 20-50)  
**Problema:** Singleton `_fernet_instance` mantém chave Fernet em memória indefinidamente.

**Risco:** Dump de memória pode expor chave de criptografia.

**Mitigação:**
```python
import gc
import ctypes

def _secure_delete(key_bytes: bytes) -> None:
    """Sobrescreve memória antes de liberar."""
    ctypes.memset(id(key_bytes) + 32, 0, len(key_bytes))
    del key_bytes
    gc.collect()

# Considerar rotação periódica da instância Fernet
```

---

#### SEC-002: Rate Limiting Baseado Apenas em Email

**Arquivo:** `src/core/auth/auth.py` (linhas 75-115)  
**Problema:** Rate limiting usa apenas email, permitindo bypass por variação de email ou IP.

**Antes:**
```python
def check_rate_limit(email: str) -> tuple[bool, float]:
    key: str = email.strip().lower()
    # ... apenas baseado em email
```

**Depois:**
```python
def check_rate_limit(email: str, ip_address: str | None = None) -> tuple[bool, float]:
    """Rate limit baseado em email E IP."""
    email_key = f"email:{email.strip().lower()}"
    ip_key = f"ip:{ip_address}" if ip_address else None

    # Verificar ambos os limites
    email_ok, email_remaining = _check_key_limit(email_key)
    if ip_key:
        ip_ok, ip_remaining = _check_key_limit(ip_key)
        if not ip_ok:
            return False, ip_remaining
    return email_ok, email_remaining
```

---

#### SEC-003: SQL Injection Potencial em SQLite Local

**Arquivo:** `src/core/auth/auth.py` (linhas 180-200)  
**Problema:** Embora use placeholders, a concatenação de strings em queries SQLite precisa auditoria.

**Recomendação:** Adicionar validação de input antes das queries:

```python
import re

def _validate_username(username: str) -> str:
    """Valida e sanitiza username."""
    if not username or len(username) > 255:
        raise ValueError("Username inválido")
    if not re.match(r'^[a-zA-Z0-9._@-]+$', username):
        raise ValueError("Username contém caracteres inválidos")
    return username.strip().lower()
```

---

#### SEC-004: Dependências com Vulnerabilidades Conhecidas

**Problema:** Várias dependências estão significativamente desatualizadas.

| Pacote | Versão Atual | Versão Mais Recente | Risco |
|--------|--------------|---------------------|-------|
| `pillow` | 10.4.0 | 12.0.0 | CVEs conhecidos |
| `cryptography` | 46.0.3 | (verificar) | Atualizações de segurança |
| `supabase` | 2.22.0 | 2.27.0 | Correções de bugs |
| `urllib3` | 2.5.0 | 2.6.2 | Patches de segurança |

**Ação:** Executar `pip-audit` e atualizar dependências críticas:
```bash
pip install pip-audit
pip-audit --fix
```

---

### 🟠 Média Severidade

| ID | Descrição | Arquivo | Mitigação |
|----|-----------|---------|-----------|
| SEC-005 | `AUTH_PEPPER` pode ser lido de arquivo YAML sem validação | `src/core/auth/auth.py` | Validar formato antes de usar |
| SEC-006 | Logs podem expor dados sensíveis em modo DEBUG | Vários | Sanitizar logs de senhas/tokens |
| SEC-007 | `RC_CLIENT_SECRET_KEY` exposta em erro de inicialização | `security/crypto.py` | Mascarar valor na mensagem |

### 🟢 Baixa Severidade

| ID | Descrição | Arquivo | Mitigação |
|----|-----------|---------|-----------|
| SEC-008 | Headers HTTP não incluem security headers | `infra/http/*` | Adicionar HSTS, CSP básico |
| SEC-009 | Timeout de sessão não configurado explicitamente | `src/core/session/*` | Definir TTL de sessão |

---

## 5. Melhorias em Testes e Qualidade

### 🔴 Alta Severidade

#### TEST-001: Cobertura Insuficiente em Módulo de Senhas

**Problema:** Módulo `security/crypto.py` é crítico mas pode ter gaps de cobertura.

**Ação:** Adicionar testes para casos de borda:

```python
# tests/unit/security/test_crypto_edge_cases.py
import pytest
from security.crypto import encrypt_text, decrypt_text, _reset_fernet_cache

class TestCryptoEdgeCases:
    def setup_method(self):
        _reset_fernet_cache()

    def test_encrypt_empty_string(self):
        assert encrypt_text("") == ""

    def test_encrypt_none(self):
        assert encrypt_text(None) == ""

    def test_decrypt_invalid_token(self, monkeypatch):
        monkeypatch.setenv("RC_CLIENT_SECRET_KEY", "valid-fernet-key-here==")
        with pytest.raises(RuntimeError, match="Falha na descriptografia"):
            decrypt_text("invalid-token-not-base64!")

    def test_encrypt_unicode(self, monkeypatch):
        monkeypatch.setenv("RC_CLIENT_SECRET_KEY", "valid-fernet-key-here==")
        result = encrypt_text("日本語テスト")
        assert decrypt_text(result) == "日本語テスト"
```

---

#### TEST-002: Testes de Integração com Supabase Ausentes

**Problema:** Maioria dos testes mockam Supabase, não testam integração real.

**Ação:** Criar suite de integração separada:

```python
# tests/integration/test_supabase_passwords.py
import pytest

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("SUPABASE_TEST_URL"), reason="Requer Supabase de teste")
class TestPasswordsIntegration:
    def test_create_and_retrieve_password(self, test_org_id):
        from src.modules.passwords.service import create_password, get_passwords

        pwd = create_password(
            org_id=test_org_id,
            client_name="Test Client",
            service="Test Service",
            username="testuser",
            password_plain="testpass123",
            notes="Integration test",
            created_by="test-user-id"
        )

        passwords = get_passwords(test_org_id)
        assert any(p["id"] == pwd["id"] for p in passwords)
```

---

### 🟠 Média Severidade

| ID | Descrição | Ação |
|----|-----------|------|
| TEST-003 | Fixtures de Tkinter podem vazar entre testes | Adicionar cleanup em `conftest.py` |
| TEST-004 | Testes de UI não cobrem estados de erro | Adicionar testes com mocks de erro |
| TEST-005 | `pytest.ini` não define timeout padrão | Adicionar `timeout = 30` |
| TEST-006 | Dead code em `tests/archived/` | Remover ou documentar propósito |

### 🟢 Baixa Severidade

| ID | Descrição | Ação |
|----|-----------|------|
| TEST-007 | Alguns testes usam `time.sleep()` | Substituir por mocks de tempo |
| TEST-008 | Falta documentação de markers customizados | Documentar em `CONTRIBUTING.md` |
| TEST-009 | Coverage report em HTML não está no `.gitignore` | Adicionar `htmlcov/` ao ignore |

---

## 6. Otimização de Dependências e Configurações

### 🔴 Alta Severidade

#### DEP-001: Dependências Críticas Desatualizadas

Execute a atualização das dependências críticas de segurança:

```bash
pip install --upgrade \
    pillow>=12.0.0 \
    cryptography>=45.0.0 \
    urllib3>=2.6.0 \
    supabase>=2.27.0 \
    httpx>=0.28.0
```

---

#### DEP-002: Dependências Possivelmente Não Utilizadas

**Análise com `deptry`:**

| Pacote | Status | Ação |
|--------|--------|------|
| `fastapi` | Presente em dev, não usado em prod | Verificar se necessário |
| `uvicorn` | Presente em dev, não usado em prod | Verificar se necessário |
| `starlette` | Transitivo de fastapi | Remover se fastapi removido |

**Comando para verificar:**
```bash
deptry . --extend-exclude tests,docs,scripts
```

---

### 🟠 Média Severidade

| ID | Descrição | Ação |
|----|-----------|------|
| DEP-003 | `requirements.txt` mistura produção e comentários | Separar em seções claras |
| DEP-004 | Versões fixadas muito antigas em algumas deps | Atualizar para ranges compatíveis |
| DEP-005 | `pyproject.toml` não define `[project]` completo | Migrar metadata do requirements |

### 🟢 Baixa Severidade

| ID | Descrição | Ação |
|----|-----------|------|
| DEP-006 | `pip-tools` não está sendo usado para lock | Considerar `pip-compile` |
| DEP-007 | Comentários em português/inglês misturados | Padronizar idioma |

---

## 7. Melhorias na UI/UX

### 🔴 Alta Severidade

#### UX-001: Feedback Insuficiente em Operações Longas

**Problema:** Upload/download de arquivos não mostram progresso adequado.

**Sugestão:**
```python
# Adicionar progressbar com callback
class ProgressDialog(tb.Toplevel):
    def __init__(self, parent, title="Processando..."):
        super().__init__(parent)
        self.title(title)
        self.progress = tb.Progressbar(self, mode="determinate", length=300)
        self.progress.pack(padx=20, pady=20)
        self.label = tb.Label(self, text="Aguarde...")
        self.label.pack(pady=10)

    def update_progress(self, value: int, message: str = ""):
        self.progress["value"] = value
        if message:
            self.label.config(text=message)
        self.update_idletasks()
```

---

### 🟠 Média Severidade

| ID | Descrição | Sugestão |
|----|-----------|----------|
| UX-002 | Mensagens de erro técnicas expostas ao usuário | Criar camada de mensagens amigáveis |
| UX-003 | Tema inconsistente entre dialogs e janela principal | Aplicar tema em todos os Toplevel |
| UX-004 | Atalhos de teclado não documentados | Adicionar tooltip/help |

### 🟢 Baixa Severidade

| ID | Descrição | Sugestão |
|----|-----------|----------|
| UX-005 | Splash screen fixo em 5 segundos | Fazer dinâmico baseado em carregamento real |
| UX-006 | Filtros de busca resetam ao trocar de módulo | Persistir estado de filtros |
| UX-007 | Tabelas não têm ordenação por coluna | Adicionar cabeçalhos clicáveis |
| UX-008 | Dark mode pode ter contraste insuficiente | Validar WCAG AA compliance |

---

## 8. Outras Sugestões Gerais

### Features Novas Recomendadas

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| Alta | Export de dados | Permitir exportar clientes/senhas para CSV/Excel |
| Alta | Backup local | Opção de backup criptografado local |
| Média | Histórico de alterações | Audit trail visível para usuário |
| Média | Multi-idioma | Internacionalização (i18n) |
| Baixa | Tema personalizado | Permitir cores customizadas |
| Baixa | Integração com calendar | Lembretes de tarefas/auditorias |

### Melhorias em Logging

```python
# Sugestão: Estruturar logs para análise
import structlog

logger = structlog.get_logger()

def log_operation(operation: str, **context):
    logger.info(
        "operation_executed",
        operation=operation,
        user_id=context.get("user_id"),
        org_id=context.get("org_id"),
        duration_ms=context.get("duration_ms"),
        success=context.get("success", True),
    )
```

### Compatibilidade Cross-Platform

| Área | Status Atual | Melhoria |
|------|--------------|----------|
| Linux | Não suportado | Testar Tkinter no Linux |
| macOS | Não suportado | Verificar paths e ícones |
| Paths | Windows-only (`\\`) | Usar `pathlib.Path` consistentemente |
| Encoding | UTF-8 assumido | Declarar explicitamente em arquivos |

### Escalabilidade

| Aspecto | Limite Atual | Sugestão |
|---------|--------------|----------|
| Clientes | ~1000 (performance) | Paginação server-side |
| Senhas | ~500 por query | Virtual scrolling |
| Arquivos | Sem limite de tamanho | Chunked upload |
| Usuários | Single-user | Multi-tenant ready |

---

## 📊 Métricas de Qualidade Atuais

### Análise Estática (Estimada)

| Ferramenta | Issues |
|------------|--------|
| ruff | ~50 warnings |
| mypy | ~200 type errors (strict mode) |
| bandit | ~10 low/medium |
| vulture | ~30 dead code items |

### Recomendações de CI/CD

```yaml
# .github/workflows/quality.yml
name: Quality Checks
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ruff
        run: ruff check . --output-format=github
      - name: Run mypy
        run: mypy src/ --ignore-missing-imports
      - name: Run bandit
        run: bandit -r src/ -ll
      - name: Run tests
        run: pytest --cov=src --cov-fail-under=70
```

---

## ✅ Checklist de Implementação

### Fase 1 - Crítico (1-2 semanas)
- [ ] SEC-001: Revisar gestão de chaves em memória
- [ ] SEC-004: Atualizar dependências críticas
- [ ] BUG-001: Adicionar logging em exceções silenciadas
- [ ] BUG-002: Corrigir race condition em cache de clientes

### Fase 2 - Alto (2-4 semanas)
- [ ] PERF-001: Otimizar queries de duplicatas
- [ ] REF-001: Iniciar extração de responsabilidades de `App`
- [ ] TEST-001: Aumentar cobertura de `security/crypto.py`
- [ ] SEC-002: Melhorar rate limiting

### Fase 3 - Médio (1-2 meses)
- [ ] UX-001: Implementar feedback de progresso
- [ ] DEP-001: Atualizar todas as dependências
- [ ] TEST-002: Criar suite de integração
- [ ] Demais itens de média prioridade

### Fase 4 - Baixo (Backlog contínuo)
- [ ] Refatorações incrementais
- [ ] Melhorias de UX
- [ ] Features novas

---

*Documento gerado automaticamente em 22/12/2025*  
*Baseado na análise do projeto RC Gestor v1.4.72*
