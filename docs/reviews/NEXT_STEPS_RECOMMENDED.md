# Próximos Passos Recomendados — RC Gestor v1.4.72

**Data:** 21 de dezembro de 2025  
**Baseado em:** Auditoria completa do codebase (CODEBASE_REVIEW.md)

---

## Sistema de Prioridades

- **P0:** Crítico - afeta produção ou previne bugs graves
- **P1:** Alta - melhora significativa em qualidade/manutenibilidade
- **P2:** Média - nice-to-have, benefício de longo prazo

**Riscos:**
- **Baixo:** Mudanças isoladas, sem dependências cruzadas
- **Médio:** Afeta múltiplos arquivos, requer testes cuidadosos
- **Alto:** Mudanças estruturais, risco de regressão

**Esforço:**
- **S (Small):** 1-4h
- **M (Medium):** 4-8h
- **L (Large):** 8-20h

---

## Tarefas Priorizadas

### P0: Adicionar Logging em Exception Handlers

**Objetivo:**  
Capturar erros silenciosos que estão sendo suprimidos por `except Exception` sem log.

**Impacto no Usuário:**  
Bugs ocultos serão identificáveis nos logs, facilitando suporte e debug.

**Risco:** Baixo  
**Esforço:** S (2h)

**Arquivos a Modificar:**
1. `src/modules/hub/services/authors_service.py` (5 ocorrências)
2. `src/app_gui.py` (2 ocorrências - remover `# noqa: BLE001`)
3. `infra/repositories/notifications_repository.py` (verificar)
4. `src/core/bootstrap.py` (verificar)

**Mudança Exemplo:**
```python
# ANTES (linha 291 de authors_service.py)
try:
    from src.core.services.profiles_service import EMAIL_PREFIX_ALIASES
    email_prefix_aliases = EMAIL_PREFIX_ALIASES
except Exception:
    email_prefix_aliases = {}

# DEPOIS
try:
    from src.core.services.profiles_service import EMAIL_PREFIX_ALIASES
    email_prefix_aliases = EMAIL_PREFIX_ALIASES
except Exception as exc:
    log.debug("Falha ao carregar EMAIL_PREFIX_ALIASES, usando dict vazio", exc_info=exc)
    email_prefix_aliases = {}
```

**Testes a Rodar:**
```bash
# Rodar suite completa
pytest -v

# Verificar logs em modo DEBUG
RC_LOG_LEVEL=DEBUG python -m src.app_gui
```

**Critério de Sucesso:**
- ✅ Todos os `except Exception` têm logging
- ✅ Tests passam sem mudanças
- ✅ Logs mostram contexto quando exceptions ocorrem

---

### P0: Garantir Cleanup de .after() Jobs

**Objetivo:**  
Prevenir memory leaks de timers Tkinter que não são cancelados.

**Impacto no Usuário:**  
App mais estável em sessões longas (8+ horas), sem consumo crescente de memória.

**Risco:** Médio  
**Esforço:** M (4h)

**Arquivos a Modificar:**
1. `src/modules/hub/hub_lifecycle.py` (verificar todos os timers)
2. `src/ui/topbar.py` (polling de notificações)
3. `src/app_status.py` (status updates)
4. `src/ui/splash.py` (progress bar e close_job)

**Mudança Exemplo:**
```python
# hub_lifecycle.py - Pattern correto

def _schedule_notes_poll(self):
    """Agenda próximo polling de notas."""
    if self._notes_poll_job_id:
        self.tk_root.after_cancel(self._notes_poll_job_id)

    self._notes_poll_job_id = self.tk_root.after(
        NOTES_POLL_INTERVAL_MS,
        self._poll_notes_callback
    )

def stop(self):
    """Para todos os timers."""
    if self._notes_poll_job_id:
        self.tk_root.after_cancel(self._notes_poll_job_id)
        self._notes_poll_job_id = None

    # Repetir para cada timer
    if self._authors_refresh_job_id:
        self.tk_root.after_cancel(self._authors_refresh_job_id)
        self._authors_refresh_job_id = None

    # ... outros timers
```

**Testes a Rodar:**
```bash
# Testes de lifecycle
pytest tests/unit/modules/hub/test_hub_lifecycle*.py -v

# Smoke test: abrir app, navegar por módulos, fechar
python -m src.app_gui
```

**Critério de Sucesso:**
- ✅ Todos os `.after()` têm ID armazenado
- ✅ Todos os IDs são cancelados em stop/destroy
- ✅ Tests de lifecycle passam
- ✅ Não há leaks após 1h de uso (verificar com memory profiler)

---

### P1: Centralizar Schema de Colunas DB

**Objetivo:**  
Criar contratos centralizados para queries `.select()`, evitando schema drift.

**Impacto no Usuário:**  
Menos erros PGRST204 em produção quando schema Supabase mudar.

**Risco:** Médio  
**Esforço:** M (6h)

**Arquivos a Criar:**
1. `src/core/db_schemas.py` (novo)

**Arquivos a Modificar:**
1. `data/supabase_repo.py`
2. `infra/repositories/notifications_repository.py`
3. `infra/repositories/anvisa_requests_repository.py`
4. `src/modules/auditoria/repository.py`
5. `src/modules/uploads/repository.py`
6. `src/features/tasks/repository.py`
7. `src/features/cashflow/repository.py`

**Implementação:**

```python
# src/core/db_schemas.py (novo arquivo)
"""Contratos de schema para tabelas Supabase.

Define colunas de cada tabela para garantir consistência.
Se o schema mudar no Supabase, atualizar aqui PRIMEIRO.
"""

class ClientsSchema:
    TABLE = "clients"
    FIELDS = "id,org_id,razao_social,cnpj,nome,numero,obs,cnpj_norm,ultima_alteracao,ultima_por"

    # Para queries específicas
    FIELDS_LIST = "id,razao_social,cnpj,nome"  # Para listas
    FIELDS_DETAIL = FIELDS  # Para detalhes

class NotificationsSchema:
    TABLE = "org_notifications"
    FIELDS = "id,created_at,message,is_read,module,event,client_id,request_id,actor_email"

class MembershipsSchema:
    TABLE = "memberships"
    FIELDS_ORG = "org_id"
    FIELDS_ROLE = "role"
    FIELDS_FULL = "user_id,org_id,role"

class AuditoriasSchema:
    TABLE = "auditorias"
    FIELDS = "id,status,created_at,updated_at,cliente_id"
```

```python
# data/supabase_repo.py - ANTES
def fetch_clients(org_id: str):
    return supabase.table("clients").select(
        "id,org_id,razao_social,cnpj,nome,numero,obs,cnpj_norm"
    ).eq("org_id", org_id)

# data/supabase_repo.py - DEPOIS
from src.core.db_schemas import ClientsSchema

def fetch_clients(org_id: str):
    return supabase.table(ClientsSchema.TABLE).select(
        ClientsSchema.FIELDS
    ).eq("org_id", org_id)
```

**Testes a Rodar:**
```bash
# Tests de repositórios
pytest tests/unit/infra/repositories -v
pytest tests/unit/core/test_data_supabase_repo*.py -v

# Verificar que queries retornam mesmos dados
pytest tests/integration -v -k supabase
```

**Critério de Sucesso:**
- ✅ Todos os `.select()` usam constantes de db_schemas.py
- ✅ Nenhum hardcoded "id,nome,email,..." em repositories
- ✅ Tests passam sem modificação de mocks
- ✅ Doc atualizado: "Se mudar schema Supabase, atualizar db_schemas.py"

---

### P1: Extrair Constantes de Timing

**Objetivo:**  
Centralizar magic numbers de delay, timeout, intervalos.

**Impacto no Usuário:**  
Facilita ajuste de performance (ex: reduzir polling de 15s para 10s).

**Risco:** Baixo  
**Esforço:** S (2h)

**Arquivos a Criar:**
1. `src/config/timings.py` (novo)

**Arquivos a Modificar:**
1. `src/app_gui.py`
2. `src/modules/hub/hub_lifecycle.py`
3. `src/core/status_monitor.py`
4. `infra/http/retry.py`
5. `src/ui/splash.py`
6. `src/ui/topbar.py`

**Implementação:**

```python
# src/config/timings.py (novo arquivo)
"""Constantes de timing/delay usadas na aplicação.

Centraliza valores de delay, timeout, intervalos de polling.
Facilita ajuste de performance sem procurar por magic numbers.
"""

# App Startup
SPLASH_DELAY_MS = 1250  # Delay antes de continuar após splash
HEALTH_CHECK_INITIAL_DELAY_MS = 2000  # Delay para primeiro health check

# Hub Polling
NOTES_POLL_INTERVAL_MS = 15000  # 15s - polling de notas compartilhadas
AUTHORS_REFRESH_INTERVAL_MS = 60000  # 60s - refresh de authors
DASHBOARD_INITIAL_LOAD_DELAY_MS = 100  # Delay para load inicial

# Status Monitor
STATUS_MONITOR_INTERVAL_MS = 30000  # 30s - verificação de status de rede
STATUS_MONITOR_WORKER_TIMEOUT_SEC = 1.5  # Timeout para join de worker thread

# Notifications
NOTIFICATIONS_POLL_INTERVAL_MS = 5000  # 5s - polling de notificações

# HTTP Retry
HTTP_RETRY_MAX_ATTEMPTS = 3
HTTP_RETRY_BACKOFF_FACTOR = 2.0  # Exponential: 1s, 2s, 4s
HTTP_RETRY_BASE_DELAY_SEC = 1.0

# Splash Screen
SPLASH_PROGRESS_STEP_DELAY_MS = 100  # Delay entre steps da progressbar
SPLASH_MIN_DISPLAY_MS = 1000  # Tempo mínimo de exibição

# UI Debounce
AUTOCOMPLETE_DEBOUNCE_MS = 300  # Delay para autocomplete
DROPDOWN_CLOSE_DELAY_MS = 200  # Delay para fechar dropdown
```

```python
# src/app_gui.py - ANTES
app.after(1250, _continue_after_splash)

# src/app_gui.py - DEPOIS
from src.config.timings import SPLASH_DELAY_MS
app.after(SPLASH_DELAY_MS, _continue_after_splash)
```

**Testes a Rodar:**
```bash
# Suite completa (timings não afetam lógica)
pytest -v

# Smoke test: verificar comportamento visual
python -m src.app_gui
```

**Critério de Sucesso:**
- ✅ Nenhum número literal de timing/delay no código (exceto 0 e 1)
- ✅ Todos usam constantes de timings.py
- ✅ Tests passam sem mudanças
- ✅ Doc em timings.py explica cada constante

---

### P1: Executar Ruff Fix e Commitar

**Objetivo:**  
Corrigir issues de lint automaticamente.

**Impacto no Usuário:**  
Código mais consistente, facilita reviews.

**Risco:** Baixo  
**Esforço:** S (1h)

**Comandos:**
```bash
# 1. Backup (opcional)
git stash

# 2. Aplicar fix automático
ruff check . --fix

# 3. Revisar mudanças
git diff

# 4. Validar que não quebrou nada
pytest -v

# 5. Commitar
git add .
git commit -m "chore: aplicar ruff --fix automático"

# 6. Push
git push origin <branch>
```

**Testes a Rodar:**
```bash
pytest -v  # Suite completa deve passar
```

**Critério de Sucesso:**
- ✅ `ruff check .` não retorna errors (apenas warnings OK)
- ✅ Tests passam
- ✅ Commit limpo sem mudanças manuais misturadas

---

### P2: Separar main_window.py em Managers

**Objetivo:**  
Quebrar arquivo de 1371 linhas em componentes menores.

**Impacto no Usuário:**  
Código mais fácil de manter e testar.

**Risco:** Médio-Alto  
**Esforço:** L (12h)

**Arquivos a Criar:**
1. `src/modules/main_window/managers/__init__.py`
2. `src/modules/main_window/managers/theme_manager.py`
3. `src/modules/main_window/managers/status_manager.py`
4. `src/modules/main_window/managers/navigation_manager.py`

**Arquivos a Modificar:**
1. `src/modules/main_window/views/main_window.py` (reduzir de 1371 para ~400 linhas)

**Implementação em Etapas:**

**Etapa 1: Extrair ThemeManager** (3h)
```python
# src/modules/main_window/managers/theme_manager.py
class ThemeManager:
    """Gerencia troca de tema e aplicação de estilos."""

    def __init__(self, window, config_path: Path):
        self.window = window
        self.config_path = config_path
        self._current_theme = self._load_theme()

    def get_current_theme(self) -> str:
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Troca tema e reinicia app."""
        ...

    def _load_theme(self) -> str:
        """Carrega tema do config."""
        ...

    def _save_theme(self, theme_name: str) -> None:
        """Salva tema no config."""
        ...
```

**Etapa 2: Extrair StatusManager** (4h)
```python
# src/modules/main_window/managers/status_manager.py
class StatusManager:
    """Gerencia status monitor e atualização de footer."""

    def __init__(self, footer, status_monitor):
        self.footer = footer
        self.status_monitor = status_monitor

    def handle_status_update(self, is_online: bool) -> None:
        """Callback de mudança de status."""
        ...

    def refresh_display(self) -> None:
        """Refresh completo do footer."""
        ...

    def update_status_dot(self, is_online: bool) -> None:
        """Atualiza indicador verde/vermelho."""
        ...
```

**Etapa 3: Extrair NavigationManager** (3h)
```python
# src/modules/main_window/managers/navigation_manager.py
class NavigationManager:
    """Gerencia navegação entre telas."""

    def __init__(self, nav_controller, app_context):
        self.nav_controller = nav_controller
        self.app_context = app_context

    def show_hub_screen(self) -> None:
        ...

    def show_main_screen(self) -> None:
        ...

    def show_passwords_screen(self) -> None:
        ...
```

**Etapa 4: Refatorar main_window.py** (2h)
```python
# main_window.py - DEPOIS
class App(tb.Window):
    def __init__(self, start_hidden: bool = False):
        super().__init__(...)

        # Managers
        self.theme_manager = ThemeManager(self, config_path)
        self.status_manager = StatusManager(status_footer, status_monitor)
        self.navigation_manager = NavigationManager(nav_controller, self)

        # Delegação
        self.show_hub_screen = self.navigation_manager.show_hub_screen
        self.set_theme = self.theme_manager.set_theme
```

**Testes a Rodar:**
```bash
# Após cada etapa
pytest tests/unit/modules/main_window -v

# Smoke test completo
python -m src.app_gui
# Verificar: boot, login, navegação entre telas, troca de tema
```

**Critério de Sucesso:**
- ✅ main_window.py tem <500 linhas
- ✅ Cada manager tem <300 linhas
- ✅ Tests passam sem mudanças (compatibilidade mantida)
- ✅ Smoke test: todas as features funcionam normalmente

---

### P2: Implementar DTOs com Pydantic

**Objetivo:**  
Criar classes de dados validadas para entidades principais.

**Impacto no Usuário:**  
Menos bugs de tipo, validação automática de dados.

**Risco:** Médio  
**Esforço:** L (14h)

**Arquivos a Criar:**
1. `src/core/models.py` (DTOs principais)
2. `src/modules/hub/models.py` (DTOs específicos do Hub)
3. `src/modules/clientes/models.py` (DTOs de clientes)

**Dependências:**
```bash
# Pydantic já está em requirements.txt
pip install pydantic
```

**Implementação:**

```python
# src/core/models.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class Client(BaseModel):
    """Cliente da organização."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID do cliente")
    org_id: str = Field(..., description="UUID da organização")
    razao_social: str = Field(..., min_length=1)
    cnpj: str = Field(..., pattern=r"^\d{14}$")
    nome: Optional[str] = None
    numero: Optional[str] = None
    obs: Optional[str] = None
    cnpj_norm: Optional[str] = None
    ultima_alteracao: Optional[datetime] = None
    ultima_por: Optional[str] = None

class Notification(BaseModel):
    """Notificação da organização."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    module: str
    event: str
    message: str
    is_read: bool
    created_at: datetime
    actor_email: Optional[str] = None
    client_id: Optional[str] = None
    request_id: Optional[str] = None
```

**Integração em Repositórios:**

```python
# data/supabase_repo.py - ANTES
def fetch_clients(org_id: str) -> list[dict]:
    response = supabase.table("clients").select("*").eq("org_id", org_id).execute()
    return response.data or []

# data/supabase_repo.py - DEPOIS
from src.core.models import Client

def fetch_clients(org_id: str) -> list[Client]:
    response = supabase.table("clients").select("*").eq("org_id", org_id).execute()
    data = response.data or []
    return [Client.model_validate(item) for item in data]
```

**Testes a Rodar:**
```bash
# Tests de models (novos)
pytest tests/unit/core/test_models.py -v

# Tests de repositórios (atualizar para DTOs)
pytest tests/unit/infra/repositories -v
pytest tests/unit/core/test_data_supabase_repo*.py -v

# Integration tests
pytest tests/integration -v
```

**Critério de Sucesso:**
- ✅ DTOs criados para: Client, Notification, Note, User, Membership
- ✅ Repositories retornam DTOs em vez de dicts
- ✅ Validação automática (ex: CNPJ com 14 dígitos)
- ✅ Tests passam com DTOs
- ✅ ViewModels consomem DTOs sem quebrar

---

### P2: Adicionar Tests de UI com Protocolo Gateway

**Objetivo:**  
Aumentar coverage de controllers usando Protocol-based testing.

**Impacto no Usuário:**  
Menos regressões em lógica de controllers.

**Risco:** Baixo  
**Esforço:** M (6h)

**Arquivos a Criar:**
1. `tests/unit/modules/clientes/controllers/test_clientes_controller.py`
2. `tests/unit/modules/passwords/controllers/test_passwords_controller.py`

**Padrão a Seguir:**  
Usar mesmo pattern de `tests/unit/modules/hub/controllers/test_notes_controller.py`

**Implementação Exemplo:**

```python
# tests/unit/modules/clientes/controllers/test_clientes_controller.py
import pytest
from src.modules.clientes.controllers.clientes_controller import ClientesController

class FakeClientesGateway:
    """Fake gateway para testes."""

    def __init__(self):
        self.shown_dialogs = []
        self.org_id = "org-test-123"
        self.user_email = "test@example.com"
        self.is_authenticated = True
        self.is_online = True

    def show_client_editor(self, client_data=None):
        self.shown_dialogs.append(("editor", client_data))
        return {"id": "new-123", "razao_social": "Test Client"}

    def confirm_delete_client(self, client_data):
        self.shown_dialogs.append(("confirm_delete", client_data))
        return True

    def show_error(self, title, message):
        self.shown_dialogs.append(("error", title, message))

    # ... outros métodos do protocol

@pytest.fixture
def fake_gateway():
    return FakeClientesGateway()

@pytest.fixture
def fake_service():
    class FakeClientesService:
        def create_client(self, org_id, data):
            return {"id": "new-123", **data}
    return FakeClientesService()

@pytest.fixture
def controller(fake_gateway, fake_service):
    return ClientesController(gateway=fake_gateway, service=fake_service)

def test_create_client_success(controller, fake_gateway):
    """Teste de criação de cliente."""
    success, message = controller.handle_create_client_click()

    assert success
    assert "editor" in [d[0] for d in fake_gateway.shown_dialogs]
```

**Testes a Rodar:**
```bash
# Novos tests
pytest tests/unit/modules/clientes/controllers -v
pytest tests/unit/modules/passwords/controllers -v

# Verificar coverage
pytest --cov=src/modules --cov-report=term-missing
```

**Critério de Sucesso:**
- ✅ Controllers têm >80% coverage
- ✅ Padrão de FakeGateway reutilizável
- ✅ Tests isolados (sem Tkinter, sem DB real)
- ✅ Documentação de como criar testes similares

---

## Plano de 3 Iterações

### Iteração 1: Fundações Sólidas (1 semana)

**Objetivo:** Corrigir riscos P0 e melhorar observabilidade.

**Entregáveis:**
1. ✅ Logging em todos os Exception handlers
2. ✅ Cleanup de .after() jobs garantido
3. ✅ Constantes de timing centralizadas
4. ✅ Ruff fix aplicado

**Testes:**
```bash
pytest -v  # Suite completa
python -m src.app_gui  # Smoke test com RC_LOG_LEVEL=DEBUG
```

**Critério de Aceite:**
- Zero `except Exception` sem logging
- Zero memory leaks de timers (verificar após 1h de uso)
- Zero lint errors do ruff
- Logs claros em modo DEBUG

---

### Iteração 2: Contratos e Estrutura (1-2 semanas)

**Objetivo:** Centralizar schemas e reduzir complexidade de main_window.

**Entregáveis:**
1. ✅ Schema de DB centralizado (db_schemas.py)
2. ✅ main_window.py refatorado em managers
3. ✅ Tests de managers criados

**Testes:**
```bash
pytest tests/unit/infra/repositories -v
pytest tests/unit/modules/main_window -v
# Smoke test: navegação entre todas as telas
```

**Critério de Aceite:**
- Nenhum `.select("...")` hardcoded em repositories
- main_window.py com <500 linhas
- Coverage de managers >70%
- Todas as features funcionando normalmente

---

### Iteração 3: Validação e Qualidade (1-2 semanas)

**Objetivo:** DTOs e testes de controllers.

**Entregáveis:**
1. ✅ DTOs implementados (Client, Notification, Note)
2. ✅ Repositories retornam DTOs
3. ✅ Tests de controllers (clientes, passwords)

**Testes:**
```bash
pytest tests/unit/core/test_models.py -v
pytest tests/unit/modules/*/controllers -v
pytest --cov=src --cov-report=html
```

**Critério de Aceite:**
- DTOs validam dados automaticamente
- Controllers têm >80% coverage
- Tests de integração passam com DTOs
- Coverage geral >65%

---

## Resumo de Impacto

| Iteração | Riscos Mitigados | Coverage Ganho | Manutenibilidade |
|----------|------------------|----------------|------------------|
| 1 | Memory leaks, bugs ocultos | +5% (logs) | +10% (menos magic numbers) |
| 2 | Schema drift, complexidade | +15% (managers) | +30% (separação de concerns) |
| 3 | Type bugs, regressões | +20% (DTOs + tests) | +25% (validação automática) |

**Total:** +40% coverage, +65% manutenibilidade

---

## Métricas de Sucesso (Pós-3 Iterações)

- ✅ Zero `except Exception` sem logging
- ✅ Zero memory leaks detectados (profiler)
- ✅ Coverage >65% (atualmente ~40-50%)
- ✅ main_window.py <500 linhas (atualmente 1371)
- ✅ Tempo de onboarding de novo dev: -30% (código mais claro)
- ✅ Bugs em produção: -40% (validação automática)
- ✅ Tempo de debug: -50% (logs adequados)

---

## Notas Finais

**Priorização Justificada:**

P0 items atacam riscos imediatos (leaks, bugs ocultos) com baixo esforço.  
P1 items melhoram estrutura e previnem dívida técnica.  
P2 items são investimento de longo prazo em qualidade.

**Quando NÃO seguir este plano:**

- Se houver bug crítico em produção: parar e corrigir primeiro
- Se houver requisito urgente de feature: priorizar feature
- Se equipe estiver reduzida: fazer apenas P0

**Manutenção do Plano:**

- Revisar a cada 2 semanas
- Ajustar prioridades conforme feedback de produção
- Adicionar novos itens conforme codebase evolui
