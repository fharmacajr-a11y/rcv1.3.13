# Auditoria Completa do Codebase — RC Gestor v1.4.72

**Data:** 21 de dezembro de 2025  
**Modo:** Read-only (análise sem refatoração)  
**Objetivo:** Mapear arquitetura, identificar riscos, recomendar melhorias

---

## A) Visão Geral

### Como Rodar o App

```bash
# 1. Clonar repositório
git clone <repo-url>
cd v1.4.72

# 2. Criar ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell

# 3. Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desenvolvimento

# 4. Configurar .env (copiar do .env.example)
# Adicionar credenciais Supabase: SUPABASE_URL, SUPABASE_KEY
# Adicionar: RC_INITIALS_MAP (JSON com mapeamento email → nome)

# 5. Executar aplicação
python -m src.app_gui

# 6. Testes
pytest -v  # Todos os testes (215+)
pytest tests/unit/modules/hub -v  # Somente módulo Hub
```

### Entrypoint Principal

**Arquivo:** `main.py`  
- Simplesmente executa `runpy.run_module("src.app_gui", run_name="__main__")`

**Arquivo:** `src/app_gui.py`  
- Configura ambiente (bootstrap.configure_environment)
- Configura logging (bootstrap.configure_logging)
- Importa e reexporta classe `App` de `src.modules.main_window.views.main_window`
- No `__main__`: instala exception hook, executa cleanup, mostra splash, verifica login, cria App

**Fluxo de boot:**
```
main.py → src.app_gui.__main__
  → bootstrap.configure_environment()
  → bootstrap.configure_logging()
  → show_splash()
  → ensure_logged()
  → App(start_hidden=True).mainloop()
```

### Variáveis .env Relevantes

| Variável | Uso | Exemplo |
|----------|-----|---------|
| `SUPABASE_URL` | URL do projeto Supabase | https://xyz.supabase.co |
| `SUPABASE_KEY` | Anon key do Supabase | eyJ... |
| `RC_NO_LOCAL_FS` | Forçar cloud-only (1=sim) | 1 |
| `RC_LOG_LEVEL` | Nível de log | INFO, DEBUG |
| `RC_INITIALS_MAP` | JSON {email: nome} | {"farmacajr@gmail.com":"Junior"} |
| `RC_ENV` | Ambiente (production, dev) | production |

---

## B) Mapa de Arquitetura

### Camadas Principais

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                             │
│  src/modules/<modulo>/views/  (Tkinter + ttkbootstrap)      │
│  src/ui/  (componentes compartilhados: topbar, menu_bar)   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Controller Layer                          │
│  src/modules/<modulo>/controllers/  (headless, testável)    │
│  src/core/navigation_controller.py  (gerencia telas)        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   ViewModel Layer (MVVM)                     │
│  src/modules/<modulo>/viewmodels/  (lógica de apresentação) │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  src/modules/<modulo>/services/  (lógica de negócio)        │
│  src/core/notifications_service.py                          │
│  src/core/services/profiles_service.py                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Repository Layer                           │
│  infra/repositories/  (acesso a dados)                      │
│  data/supabase_repo.py  (operações clientes/org)            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│  infra/supabase/  (client, auth, storage, retry)            │
│  infra/http/  (HTTPX client, retry logic)                   │
└─────────────────────────────────────────────────────────────┘
```

### Módulos Principais

| Módulo | Diretório | Responsabilidade |
|--------|-----------|------------------|
| **Main Window** | src/modules/main_window/ | Janela principal, navegação global |
| **Login** | src/modules/login/ | Splash, autenticação Supabase |
| **Hub** | src/modules/hub/ | Central de anotações compartilhadas |
| **Clientes** | src/modules/clientes/ | CRUD de clientes |
| **Passwords** | src/modules/passwords/ | Gerenciamento seguro de senhas |
| **Uploads** | src/modules/uploads/ | Upload de arquivos para Storage |
| **Auditoria** | src/modules/auditoria/ | Tracking de auditorias |
| **ANVISA** | src/modules/anvisa/ | Workflow específico ANVISA |
| **Lixeira** | src/modules/lixeira/ | Recuperação de clientes deletados |
| **Cashflow** | src/features/cashflow/ | Controle de fluxo de caixa |
| **Tasks** | src/features/tasks/ | Gerenciamento de tarefas |

---

## C) Arquivos Principais (Top 30)

### Entrypoints e Core (Ranking 1-10)

1. **main.py** (7 linhas)  
   **Por quê:** Ponto de entrada oficial, usa runpy para executar src.app_gui

2. **src/app_gui.py** (155 linhas, 5.7KB)  
   **Por quê:** Entrypoint real, orquestra bootstrap, splash, login, cria App

3. **src/modules/main_window/views/main_window.py** (1371 linhas, 52.8KB)  
   **Por quê:** Classe App principal (Tk.Window), navegação entre telas, menu, footer, health check

4. **src/core/bootstrap.py** (194 linhas)  
   **Por quê:** Configuração inicial (environment, logging, HiDPI), health check assíncrono

5. **src/core/notifications_service.py** (380 linhas)  
   **Por quê:** Service headless para notificações org (fetch, publish, count, mark read)

6. **src/core/navigation_controller.py** (desconhecido)  
   **Por quê:** Gerencia troca de telas no container principal

7. **infra/supabase_client.py** (módulo agregador)  
   **Por quê:** Barrel module para Supabase (DB, Storage, Auth, HTTP)

8. **infra/supabase/db_client.py** (389 linhas)  
   **Por quê:** Singleton Supabase client, exec_postgrest com retry, health check

9. **infra/supabase/auth_client.py** (desconhecido)  
   **Por quê:** Bind de token JWT no PostgREST para RLS

10. **infra/http/retry.py** (desconhecido)  
    **Por quê:** Lógica de retry para chamadas HTTP (exponential backoff)

### Hub (Ranking 11-15)

11. **src/modules/hub/views/hub_screen.py** (35.8KB)  
    **Por quê:** Tela principal do Hub, orquestra panels, dashboard, lifecycle

12. **src/modules/hub/controllers/notes_controller.py** (497 linhas, 16.8KB)  
    **Por quê:** Controller headless para ações de notas (add, edit, delete, toggle)

13. **src/modules/hub/viewmodels/notes_vm.py** (19.4KB)  
    **Por quê:** ViewModel de notas (formatação, ordenação, paginação)

14. **src/modules/hub/services/hub_component_factory.py** (21.3KB)  
    **Por quê:** Factory que injeta dependências (notifications_service, notes_service)

15. **src/modules/hub/hub_lifecycle.py** (342 linhas)  
    **Por quê:** Gerenciamento de timers (polling, live sync, authors refresh)

### Clientes (Ranking 16-20)

16. **src/modules/clientes/views/main_screen_helpers.py** (30.2KB)  
    **Por quê:** Helpers para UI de clientes (formatação, validação)

17. **src/modules/clientes/views/main_screen_controller.py** (28.8KB)  
    **Por quê:** Controller da tela de clientes (CRUD, filtros, navegação)

18. **src/modules/clientes/service.py** (desconhecido)  
    **Por quê:** Lógica de negócio para clientes (validação CNPJ, persistência)

19. **src/modules/clientes/viewmodel.py** (19.4KB)  
    **Por quê:** ViewModel de clientes (formatação Treeview, busca)

20. **data/supabase_repo.py** (22.6KB)  
    **Por quê:** Repositório de clientes (select, insert, update, delete com RLS)

### Infra e Repositórios (Ranking 21-25)

21. **infra/repositories/notifications_repository.py** (358 linhas)  
    **Por quê:** Repositório de notificações (list, count, mark_read, insert com dedupe)

22. **infra/repositories/anvisa_requests_repository.py** (desconhecido)  
    **Por quê:** Repositório de requisições ANVISA

23. **infra/supabase/storage_client.py** (desconhecido)  
    **Por quê:** Client para Storage (upload, download, baixar_pasta_zip)

24. **infra/net_status.py** (desconhecido)  
    **Por quê:** Status de rede (ping, probe, online/offline)

25. **src/core/status_monitor.py** (161 linhas)  
    **Por quê:** Monitor de status com worker thread (polling de rede)

### UI Compartilhada (Ranking 26-30)

26. **src/ui/topbar.py** (19.9KB)  
    **Por quê:** Barra superior com botões Home, Sites, ChatGPT, Notificações

27. **src/ui/menu_bar.py** (desconhecido)  
    **Por quê:** Menu principal (Arquivo, Editar, Ferramentas, Temas)

28. **src/ui/login_dialog.py** (desconhecido)  
    **Por quê:** Dialog de login moderno com Supabase

29. **src/ui/splash.py** (desconhecido)  
    **Por quê:** Splash screen com progressbar

30. **src/modules/main_window/app_actions.py** (17KB)  
    **Por quê:** Delegação de ações (novo_cliente, editar_cliente, lixeira)

---

## D) Fluxos Críticos

### Fluxo 1: Boot → Login → MainWindow

```
1. main.py executa src.app_gui.__main__

2. src.app_gui.__main__:
   - bootstrap.configure_environment()  # Carrega .env
   - bootstrap.configure_logging(preload=True)
   - install_global_exception_hook()
   - cleanup_on_startup()  # Remove temp files antigos
   - show_splash()  # Mostra splash screen

3. show_splash() (src.ui.splash):
   - Cria Toplevel com progressbar animada
   - Fecha automaticamente após delay

4. ensure_logged() (src.core.auth_bootstrap):
   - Verifica se existe sessão válida (token JWT)
   - Se não: abre LoginDialog
   - LoginDialog autentica via Supabase Auth
   - Salva token + user metadata em session

5. App(start_hidden=True) (src.modules.main_window.views.main_window):
   - Cria tb.Window (Tkinter)
   - Inicializa serviços:
     * NotificationsService
     * StatusMonitor (worker thread)
     * AuthController
     * AppActions
   - Cria UI:
     * TopBar (botões Home, Sites, etc.)
     * MenuBar (menu superior)
     * NavigationController (container de conteúdo)
     * StatusFooter (status online/offline, ambiente)
   - Exibe janela (deiconify)
   - Agenda health check inicial após 2s
   - Navega para Hub (show_hub_screen)

6. Health Check Assíncrono:
   - StatusMonitor cria worker thread
   - Loop: probe() a cada 30s → callback _apply_status
   - Atualiza dot indicator (verde/vermelho)
   - Atualiza tooltip no footer
```

### Fluxo 2: Hub → Anotações Compartilhadas

#### Carregamento de Notas

```
1. HubScreen.__init__():
   - Cria panels (TopPanel, CenterPanel, RightPanel)
   - Injeta NotesController via hub_component_factory
   - Inicializa HubLifecycle (gerencia timers)

2. HubLifecycle.start():
   - Agenda initial_load de notas (delay 100ms)
   - Agenda polling periódico (a cada 15s)
   - Tenta ativar live sync (Realtime se disponível)

3. _load_notes_async():
   - Executa em thread: notes_service.fetch_shared_notes(org_id)
   - Retorna via callback UI-thread: _on_notes_loaded(notes_data)

4. NotesViewModel.refresh(notes_data):
   - Converte data → NotesViewState
   - Ordena: fixados primeiro, depois por created_at desc
   - Calcula paginação (20 por página)

5. HubScreen.render_notes():
   - Limpa Text widget
   - Para cada nota visível:
     * Renderiza cabeçalho (autor + timestamp + ícones)
     * Renderiza texto com quebra de linha
     * Adiciona separador
   - Bind de eventos (botões editar/deletar/fixar)
```

#### Criação de Nota

```
1. Usuário digita texto no Entry e clica "Adicionar"

2. NotesController.handle_add_note_click(text):
   - Valida: texto não vazio, autenticado, online
   - Obter org_id e user_email
   - Cria preview (trunca em 120 chars)

3. notes_service.create_shared_note():
   - INSERT na tabela shared_notes
   - Retorna note_data com ID

4. notifications_service.publish():
   - Resolve display name (RC_INITIALS_MAP)
   - Gera request_id (hub_notes_created:{note_id})
   - INSERT em org_notifications (com dedupe check)

5. Callback success:
   - Limpa Entry
   - Força reload_notes()
   - Reload dashboard (atualiza count)
```

#### Soft Delete de Nota

```
1. Usuário clica ícone 🗑️ na nota

2. NotesController.handle_delete_note_click(note_id):
   - Mostra confirm_delete_note dialog
   - Se confirmado: notes_service.soft_delete_note(note_id)

3. notes_service.soft_delete_note():
   - UPDATE shared_notes SET deleted_at = NOW()
   - (RLS garante que só autor/admin pode deletar)

4. Callback success:
   - Força reload_notes()
   - Mostra toast "Nota removida"
```

### Fluxo 3: Notificações (Polling → Badge/Toast)

#### Polling de Notificações

```
1. App.__init__() cria NotificationsService:
   - Injeta org_id_provider, user_provider
   - Injeta notifications_repository

2. TopBar cria NotificationsButton:
   - Registra callback _poll_notifications
   - Inicia timer: self.after(5000, _poll_notifications)

3. _poll_notifications():
   - notifications_service.fetch_unread_count(exclude_actor_email=current_user)
   - Atualiza badge com count
   - Se count > 0: badge visível (vermelho)
   - Se count == 0: badge invisível

4. Clique no botão:
   - Abre NotificationsDialog
   - Lista: notifications_service.fetch_latest(limit=20, exclude_actor_email=current_user)
   - Renderiza lista com scroll
   - Botão "Marcar todas como lidas"

5. Marcar como lidas:
   - notifications_service.mark_all_read(org_id)
   - Fecha dialog
   - Força novo poll (count volta a 0)
```

#### Publicação de Notificação

```
1. Controller (ex: NotesController) publica:
   - notifications_service.publish(
       module="hub_notes",
       event="created",
       message="Anotações • Junior: texto preview",
       request_id="hub_notes_created:123"
     )

2. NotificationsService.publish():
   - Obter org_id, actor_user_id, actor_email
   - Resolver display name via RC_INITIALS_MAP
   - Chamar repository.insert_notification()

3. NotificationsRepository.insert_notification():
   - Dedupe check: SELECT com request_id
   - Se já existe: return True (skip)
   - Se não existe: INSERT na tabela org_notifications
   - Retorna sucesso

4. Usuários da mesma org:
   - Polling detecta novo unread_count
   - Badge aparece (vermelho)
   - Clique mostra notificação na lista
```

### Fluxo 4: Supabase / DB (Retry + Healthcheck)

#### Criação do Cliente Supabase

```
1. Primeiro acesso: get_supabase()
   - Lock singleton
   - Carrega SUPABASE_URL e SUPABASE_KEY do .env
   - create_client() com ClientOptions(
       schema="public",
       headers={"apikey": key},
       auto_refresh_token=True,
       httpx_client=HTTPX_CLIENT  # Custom com timeouts
     )
   - Salva em _SUPABASE_SINGLETON
   - Retorna client

2. Bind de Auth (se usuário logado):
   - bind_postgrest_auth_if_any(client, token_jwt)
   - Adiciona header Authorization: Bearer <token>
   - Necessário para RLS (Row Level Security)
```

#### Exec PostgREST com Retry

```
1. Chamada: exec_postgrest(query_builder)
   - query_builder = supabase.table("clients").select("*").eq("org_id", org_id)

2. retry_call() (infra/http/retry.py):
   - Configuração: 3 tentativas, backoff exponencial (1s, 2s, 4s)
   - Try 1: query_builder.execute()
   - Se APIError 504/503/500: retry
   - Se APIError 401/403: raise (não retry)
   - Se HTTPX timeout: retry
   - Se success: return response

3. Verificação de colunas:
   - Risco: se .select("id, nome, email") mas "email" não existe no schema
   - Supabase retorna APIError com PGRST204 (coluna não existe)
   - NÃO há retry (é erro permanente)
```

#### Health Check

```
1. Inicialização: _start_health_checker(client)
   - Cria thread daemon
   - Loop infinito: _health_check_once() a cada 15s

2. _health_check_once(client):
   - Tenta RPC ping(): client.rpc("ping").execute()
   - Se RPC não existe (404): fallback para /auth/v1/health
   - Se ambos falham: tenta SELECT na tabela fallback
   - Atualiza estado global: _IS_ONLINE, _LAST_SUCCESS_TIMESTAMP

3. is_supabase_online():
   - Retorna _IS_ONLINE (sem blocking)
   - UI usa isso para mostrar dot verde/vermelho

4. get_cloud_status_for_ui():
   - Retorna (texto, estilo, tooltip) para footer
   - Ex: ("Online", "success.Toolbutton", "Conectado (último check: 5s atrás)")
```

#### Centralização de Colunas (Risco)

**Problema Atual:**  
Cada repositório/service define colunas manualmente em `.select(...)`. Se o schema Supabase mudar (renomear coluna, remover campo), queries quebram.

**Localização dos .select():**
- data/supabase_repo.py: clients, memberships
- infra/repositories/notifications_repository.py: org_notifications
- src/modules/auditoria/repository.py: auditorias
- src/modules/uploads/repository.py: clientes storage
- src/features/tasks/repository.py: tasks
- src/features/cashflow/repository.py: cashflow

**Recomendação (ver seção F):**  
Criar DTOs ou Schema Contracts centralizados.

---

## E) Pontos de Risco (Hotspots) — Top 10

### 1. **main_window.py** (1371 linhas, 52.8KB)

**Descrição:**  
Arquivo gigante com múltiplas responsabilidades: navegação, menu, footer, health check, temas, actions.

**Riscos:**
- Difícil de testar (muito código de UI acoplado)
- Mudanças podem quebrar múltiplos fluxos
- Coverage baixo (~19% direto)

**Evidência:**
```python
# Múltiplas responsabilidades no __init__:
- criar top_bar
- criar menu_bar
- criar navigation_controller
- criar status_footer
- criar status_monitor
- criar auth_controller
- criar app_actions
- bind keybindings
- setup theme
```

**Impacto:**  
Alto - é o coração da aplicação, qualquer bug afeta todos os módulos.

**Recomendação:**  
Extrair responsabilidades para classes separadas (WindowManager, ThemeManager, StatusManager). Ver "Next Steps Recommended".

---

### 2. **Queries .select() com Colunas Hardcoded**

**Descrição:**  
Múltiplos locais com `.select("id, nome, email, ...")` sem validação central.

**Riscos:**
- Schema drift: se Supabase mudar coluna, queries quebram em runtime
- Duplicação: mesma tabela com colunas diferentes em locais distintos
- Debug difícil: erro só aparece em produção (PGRST204)

**Evidência:**
```python
# data/supabase_repo.py
.select("id, org_id, razao_social, cnpj, nome, numero, obs, cnpj_norm")

# src/modules/clientes/service.py
.select("id,razao_social,cnpj,nome,numero,obs,ultima_alteracao,ultima_por")

# PROBLEMA: lista de colunas diferente para mesma tabela!
```

**Impacto:**  
Médio-Alto - pode causar falhas silenciosas ou erros em produção.

**Recomendação:**  
Criar DTOs ou Schema Contracts (ex: `ClientsSchema.FIELDS = "id,razao_social,..."`) e usar em todos os selects.

---

### 3. **Except Exception Sem Log**

**Descrição:**  
Múltiplos `except Exception` que silenciam erros sem logging adequado.

**Riscos:**
- Bugs ocultos: erros acontecem mas não aparecem nos logs
- Debug impossível: sem stacktrace, não dá pra investigar
- Comportamento inesperado: código continua com estado inconsistente

**Evidência:**
```python
# src/modules/hub/services/authors_service.py linha 291
try:
    email_prefix_aliases = EMAIL_PREFIX_ALIASES
except Exception:  # ← sem log!
    email_prefix_aliases = {}
```

**Localização (sample):**
- src/modules/hub/services/authors_service.py (5 ocorrências)
- tests/unit/ui/* (múltiplas ocorrências em tests)
- src/app_gui.py (2 ocorrências com `# noqa: BLE001`)

**Impacto:**  
Médio - pode mascarar bugs críticos.

**Recomendação:**  
Adicionar `log.debug()` ou `log.exception()` em todos os `except Exception`. Usar `except Exception as exc` sempre.

---

### 4. **Polling com .after() Sem Cleanup Garantido**

**Descrição:**  
Uso extensivo de `widget.after(delay, callback)` sem sempre cancelar job IDs.

**Riscos:**
- Memory leak: timers continuam rodando após widget destruído
- Duplicação: múltiplos timers agendados simultaneamente
- Concorrência: callbacks executam em ordem inesperada

**Evidência:**
```python
# src/modules/hub/hub_lifecycle.py
self._notes_poll_job_id = screen.after(15000, _poll_notes)

# PROBLEMA: se stop() não for chamado, timer nunca cancela
```

**Localização:**
- src/ui/topbar.py (polling de notificações)
- src/modules/hub/hub_lifecycle.py (polling de notas)
- src/app_status.py (status updates)
- src/ui/splash.py (progress bar)

**Impacto:**  
Médio - pode causar vazamento de memória em sessões longas.

**Recomendação:**  
Garantir que todo `.after()` tenha cleanup correspondente em `stop()` ou `destroy()`. Usar pattern: `if self._job_id: self.after_cancel(self._job_id)`.

---

### 5. **Dependencies Entre Módulos (Acoplamento)**

**Descrição:**  
Módulos importam uns dos outros sem camada clara de abstração.

**Riscos:**
- Dependências circulares potenciais
- Difícil refatorar (mudança em A quebra B, C, D)
- Testes difíceis (precisa mockar muitas coisas)

**Evidência:**
```python
# src/modules/hub/services/hub_component_factory.py
from src.modules.hub.services.hub_auth_helpers import get_app_from_widget
app = get_app_from_widget(screen)
notifications_service = getattr(app, "notifications_service", None)

# PROBLEMA: factory precisa conhecer estrutura interna de App
```

**Impacto:**  
Médio - aumenta complexidade e dificulta testes.

**Recomendação:**  
Usar injeção de dependência via Protocol (como já feito em NotesController). Evitar `getattr()` para acessar serviços de App.

---

### 6. **Testes com Coverage Baixo em UI**

**Descrição:**  
Arquivos de UI têm coverage ~19% devido a dificuldade de testar Tkinter.

**Riscos:**
- Regressões não detectadas
- Mudanças quebram UI sem testes alertarem
- Confiança baixa em refatorações

**Evidência:**
```
src/modules/main_window/views/main_window.py: 19% coverage
src/modules/hub/views/hub_screen.py: coverage desconhecida
```

**Impacto:**  
Médio - aumenta risco de bugs em produção.

**Recomendação:**  
Separar lógica de UI (extrair para controllers/viewmodels). Testar controllers isoladamente. Ver padrão usado em NotesController.

---

### 7. **Supabase Client Singleton com Lock**

**Descrição:**  
Cliente Supabase é singleton global com lock threading, mas usado em múltiplos contextos (UI thread, workers, health check).

**Riscos:**
- Deadlock potencial se lock for mantido durante I/O longo
- Concorrência: múltiplas threads usando mesmo client
- State management: sessão muda mas client não atualiza (bind_auth)

**Evidência:**
```python
# infra/supabase/db_client.py
_SINGLETON_LOCK: Final[threading.Lock] = threading.Lock()

def get_supabase() -> Client:
    with _SINGLETON_LOCK:  # ← pode bloquear threads
        if _SUPABASE_SINGLETON is None:
            _SUPABASE_SINGLETON = create_client(...)
```

**Impacto:**  
Baixo-Médio - funcionando atualmente, mas pode causar problemas em escala.

**Recomendação:**  
Considerar client pool ou context manager para evitar lock global. Documentar que `bind_postgrest_auth_if_any` deve ser chamado após login/refresh.

---

### 8. **Duplicação de Lógica de Formatação**

**Descrição:**  
Código de formatação (datas, CNPJ, telefone) espalhado em múltiplos arquivos.

**Riscos:**
- Inconsistência: formatos diferentes em telas diferentes
- Duplicação: mesmo código em 5+ lugares
- Bugs: correção em um lugar não propaga para outros

**Evidência:**
```python
# Formatação de data aparece em:
- src/modules/hub/format.py
- src/modules/hub/notes_rendering.py
- src/modules/clientes/views/main_screen_helpers.py
- src/modules/auditoria/views/main_frame.py

# Cada um com lógica ligeiramente diferente
```

**Impacto:**  
Baixo-Médio - mais um problema de manutenibilidade.

**Recomendação:**  
Centralizar em `src/utils/formatters.py` ou similar. Criar funções puras e testáveis.

---

### 9. **Hard-coded Timings e Magic Numbers**

**Descrição:**  
Valores de delay, timeouts, limites espalhados como literais no código.

**Riscos:**
- Difícil ajustar comportamento (precisa procurar em N arquivos)
- Sem documentação de porquê aquele valor específico
- Testes dependem de timings exatos

**Evidência:**
```python
# src/app_gui.py
app.after(1250, _continue_after_splash)  # Por que 1250ms?

# src/modules/hub/hub_lifecycle.py
screen.after(15000, _poll_notes)  # Por que 15s?

# infra/http/retry.py
retry_call(max_attempts=3, backoff_factor=2.0)  # Por que 3 e 2.0?
```

**Impacto:**  
Baixo - mas dificulta tuning de performance.

**Recomendação:**  
Extrair para constantes nomeadas ou config. Ex: `SPLASH_DELAY_MS = 1250`, `NOTES_POLL_INTERVAL_MS = 15000`.

---

### 10. **Health Check com Estado Global**

**Descrição:**  
Status de conectividade em variáveis globais (`_IS_ONLINE`, `_LAST_SUCCESS_TIMESTAMP`) sem thread-safety total.

**Riscos:**
- Race condition: leitura/escrita simultânea
- Estado inconsistente: UI mostra online mas worker detectou offline
- Debug difícil: estado não é visível em logs

**Evidência:**
```python
# infra/supabase/db_client.py
_IS_ONLINE: bool = False  # Global sem lock
_STATE_LOCK: Final[threading.Lock] = threading.Lock()  # Lock existe mas não é usado em todos os acessos
```

**Impacto:**  
Baixo - race rara, mas possível.

**Recomendação:**  
Envolver TODOS os acessos a `_IS_ONLINE` com lock. Ou usar threading.Event para sinalização.

---

## F) Qualidade e Manutenção

### Estilo e Lint (Ruff)

**Configuração Atual:**
- `pyproject.toml` configurado com Ruff
- Select: E (pycodestyle), F (pyflakes), N (naming)
- Ignore: E501 (linhas longas), F403 (star imports), F821 (nomes indefinidos)
- Line length: 120
- Target: Python 3.13

**Status:**
- Execução de `ruff check .` cancelada (comando interrompido)
- Não há evidência de CI/CD rodando ruff automaticamente

**Recomendações:**
1. Rodar `ruff check . --fix` para corrigir issues automáticos
2. Adicionar ruff ao pre-commit hook (`.pre-commit-config.yaml` existe)
3. Configurar CI para bloquear PRs com lint errors

---

### Tipagem (Pyright)

**Configuração Atual:**
- `pyrightconfig.json` configurado
- Mode: basic
- Strict habilitado para módulo clientes/views (4 arquivos)
- Ignora: tests, scripts, migrations, .venv

**Status:**
- Não foi executado análise pyright nesta sessão
- Arquivos com strict mode: apenas clientes (sample pequeno)

**Recomendações:**
1. Expandir strict mode progressivamente para outros módulos
2. Priorizar: core, notifications_service, repositories
3. Adicionar pyright ao CI (opcional, pode ser lento)

---

### Testes Existentes

**Estrutura:**
```
tests/
  unit/  (215+ testes)
    core/  (auth, bootstrap, notifications)
    modules/  (hub, clientes, passwords, anvisa, etc.)
    infra/  (supabase, http, repositories)
    ui/  (components, topbar, menu_bar)
  integration/  (flows end-to-end)
  gui_legacy/  (testes UI antigos, deprecated)
```

**Cobertura por Módulo:**

| Módulo | Testes Unitários | Coverage Estimado |
|--------|------------------|-------------------|
| core/notifications | ✅ 7 tests | ~80% |
| core/bootstrap | ✅ 3 tests | ~60% |
| modules/hub/controllers | ✅ 25 tests | ~85% |
| modules/clientes | ✅ 15+ tests | ~50% |
| infra/repositories/notifications | ✅ 9 tests | ~90% |
| infra/supabase | ✅ 10+ tests | ~70% |
| UI (main_window, hub_screen) | ⚠️ 5 tests | ~19% |

**Frameworks Usados:**
- pytest (runner)
- unittest.mock (mocking)
- pytest-cov (coverage)

**Comando de Execução:**
```bash
# Todos os testes
pytest -v

# Módulo específico
pytest tests/unit/modules/hub -v

# Com coverage
pytest --cov=src --cov=infra --cov-report=html
```

**Issues Conhecidos:**
- Tests de UI são difíceis (Tkinter não é headless)
- Alguns tests dependem de timing (.after() simulado)
- Falta tests de integração para fluxos completos (boot → login → hub)

---

## G) Sugestões de Melhoria

### Quick Wins (Baixo Risco, Alto Impacto)

#### 1. **Adicionar Logging em Except Exception**

**Objetivo:**  
Capturar e logar erros silenciosos.

**Impacto:**  
Facilita debug de bugs ocultos.

**Risco:** Baixo  
**Esforço:** S (1-2h)

**Arquivos:**
- src/modules/hub/services/authors_service.py (5 ocorrências)
- src/app_gui.py (2 ocorrências)
- infra/repositories/*.py (verificar)

**Mudança:**
```python
# ANTES
try:
    ...
except Exception:
    fallback_value = None

# DEPOIS
try:
    ...
except Exception as exc:
    log.debug("Descrição do contexto", exc_info=exc)
    fallback_value = None
```

**Testes:**
- Rodar suite completa: `pytest -v`
- Verificar logs em modo DEBUG

---

#### 2. **Extrair Constantes de Timing**

**Objetivo:**  
Centralizar magic numbers de delay/timeout.

**Impacto:**  
Facilita tuning de performance.

**Risco:** Baixo  
**Esforço:** S (2-3h)

**Arquivos:**
- src/app_gui.py
- src/modules/hub/hub_lifecycle.py
- src/core/status_monitor.py
- infra/http/retry.py

**Mudança:**
```python
# Criar src/config/timings.py
SPLASH_DELAY_MS = 1250
NOTES_POLL_INTERVAL_MS = 15000
STATUS_MONITOR_INTERVAL_MS = 30000
HTTP_RETRY_MAX_ATTEMPTS = 3
HTTP_RETRY_BACKOFF_FACTOR = 2.0

# Usar em vez de literais
app.after(SPLASH_DELAY_MS, _continue_after_splash)
```

**Testes:**
- Testes existentes devem passar sem mudanças
- Opcional: criar test_timings.py para validar valores

---

#### 3. **Centralizar Schema de Colunas**

**Objetivo:**  
Evitar schema drift em queries `.select()`.

**Impacto:**  
Reduz risco de PGRST204 errors em produção.

**Risco:** Baixo-Médio  
**Esforço:** M (4-6h)

**Arquivos:**
- Criar: src/core/db_schemas.py
- Modificar: data/supabase_repo.py, infra/repositories/*.py, src/modules/*/repository.py

**Mudança:**
```python
# src/core/db_schemas.py
class ClientsSchema:
    TABLE = "clients"
    FIELDS = "id,org_id,razao_social,cnpj,nome,numero,obs,cnpj_norm,ultima_alteracao,ultima_por"

class NotificationsSchema:
    TABLE = "org_notifications"
    FIELDS = "id,created_at,message,is_read,module,event,client_id,request_id,actor_email"

# data/supabase_repo.py
from src.core.db_schemas import ClientsSchema

def fetch_clients(org_id: str):
    return supabase.table(ClientsSchema.TABLE).select(ClientsSchema.FIELDS).eq("org_id", org_id)
```

**Testes:**
- Rodar tests de repositórios: `pytest tests/unit/infra/repositories -v`
- Validar que queries retornam mesmos campos

---

#### 4. **Garantir Cleanup de .after() Jobs**

**Objetivo:**  
Prevenir memory leaks de timers.

**Impacto:**  
Melhora estabilidade em sessões longas.

**Risco:** Baixo  
**Esforço:** M (3-4h)

**Arquivos:**
- src/modules/hub/hub_lifecycle.py
- src/ui/topbar.py
- src/app_status.py

**Mudança:**
```python
# Pattern correto
def start_polling(self):
    if self._poll_job_id:
        self.after_cancel(self._poll_job_id)
    self._poll_job_id = self.after(INTERVAL_MS, self._poll_callback)

def stop_polling(self):
    if self._poll_job_id:
        self.after_cancel(self._poll_job_id)
        self._poll_job_id = None
```

**Testes:**
- Criar test que verifica: start() → stop() → job_id is None
- Rodar: `pytest tests/unit/modules/hub/test_hub_lifecycle*.py -v`

---

#### 5. **Executar Ruff Fix Automático**

**Objetivo:**  
Corrigir issues de lint detectáveis automaticamente.

**Impacto:**  
Melhora consistência de código.

**Risco:** Baixo  
**Esforço:** S (30min)

**Comando:**
```bash
ruff check . --fix
git diff  # Revisar mudanças
git add .
git commit -m "chore: aplicar ruff --fix automático"
pytest -v  # Garantir que nada quebrou
```

**Testes:**
- Suite completa deve passar
- Verificar visualmente diff antes de commit

---

### Melhorias Estruturais (Médio Prazo)

#### 1. **Separar Lógica de main_window.py**

**Objetivo:**  
Quebrar arquivo de 1371 linhas em componentes menores.

**Impacto:**  
Melhora testabilidade e manutenibilidade.

**Risco:** Médio  
**Esforço:** L (10-15h)

**Plano:**
```
src/modules/main_window/
  views/
    main_window.py  (apenas orchestration)
    window_manager.py  (cria/gerencia window)
    theme_manager.py  (troca tema, aplica estilos)
    status_manager.py  (integra status_monitor + footer)
    navigation_manager.py  (wrapper de navigation_controller)
```

**Etapas:**
1. Extrair ThemeManager (métodos _set_theme, _handle_menu_theme_change)
2. Extrair StatusManager (métodos _handle_status_update, _refresh_status_display, _update_status_dot)
3. Extrair NavigationManager (métodos show_*_screen)
4. Manter App.__init__ como orchestrator leve

**Testes:**
- Criar tests unitários para cada manager
- Smoke test: app deve iniciar e navegar normalmente
- Rodar: `pytest tests/unit/modules/main_window -v`

---

#### 2. **Implementar DTOs para Entidades**

**Objetivo:**  
Criar classes Pydantic para validação de dados.

**Impacto:**  
Reduz bugs de tipo, facilita serialização.

**Risco:** Médio  
**Esforço:** L (12-16h)

**Plano:**
```python
# src/core/models.py
from pydantic import BaseModel, Field
from datetime import datetime

class Client(BaseModel):
    id: str = Field(..., description="UUID do cliente")
    org_id: str
    razao_social: str
    cnpj: str
    nome: str | None = None
    numero: str | None = None
    obs: str | None = None
    ultima_alteracao: datetime | None = None
    ultima_por: str | None = None

class Notification(BaseModel):
    id: str
    org_id: str
    module: str
    event: str
    message: str
    is_read: bool
    created_at: datetime
    actor_email: str | None = None
    client_id: str | None = None
    request_id: str | None = None
```

**Integração:**
- Repositories retornam DTOs em vez de dicts
- ViewModels consomem DTOs
- Validação automática no parse

**Testes:**
- Tests de serialização/deserialização
- Tests de validação (campos obrigatórios, tipos)

---

#### 3. **Migrar Polling para Event-driven**

**Objetivo:**  
Reduzir polling, usar Supabase Realtime quando possível.

**Impacto:**  
Melhora performance, reduz latência de updates.

**Risco:** Médio-Alto  
**Esforço:** L (16-20h)

**Plano:**
1. Hub notes: usar Realtime subscriptions em vez de polling 15s
2. Notifications: usar Realtime para badge em tempo real
3. Fallback: manter polling se Realtime falhar

**Desafios:**
- Realtime requer WebSocket (pode não funcionar em redes corporativas)
- Precisa gerenciar reconexão

**Testes:**
- Simular online/offline
- Validar fallback para polling
- Performance: medir latência de updates

---

### Itens para "Não Mexer Agora" (Alto Risco)

#### 1. **Refatorar Arquitetura de Módulos**

**Por quê evitar:**  
- Mudanças estruturais afetam todos os imports
- Risco alto de quebrar features existentes
- Requer migração de testes
- Pode introduzir dependências circulares

**Quando considerar:**  
Apenas se houver necessidade crítica de escalabilidade (ex: migrar para plugins).

---

#### 2. **Trocar Tkinter por Framework Moderno**

**Por quê evitar:**  
- Reescrever UI do zero
- Perda de features existentes
- Curva de aprendizado da equipe
- Não há problema crítico com Tkinter atual

**Quando considerar:**  
Se houver requisito de web app ou mobile.

---

## Resumo Executivo

### Status Geral: **Saudável com Pontos de Atenção**

**Pontos Fortes:**
- ✅ Arquitetura MVVM bem definida no Hub
- ✅ Testes unitários cobrindo fluxos críticos (215+ tests)
- ✅ Uso de Protocols para dependency injection
- ✅ Retry logic implementado para chamadas Supabase
- ✅ Health check assíncrono funcionando
- ✅ Configuração de lint/type check presente

**Pontos de Atenção:**
- ⚠️ main_window.py muito grande (52KB, 1371 linhas)
- ⚠️ Schema de DB hardcoded em múltiplos locais
- ⚠️ Except Exception sem logging em alguns lugares
- ⚠️ Polling timers sem cleanup garantido
- ⚠️ UI com coverage baixo (~19%)

**Dívida Técnica:** Moderada  
**Manutenibilidade:** Média-Alta  
**Risco de Bugs Críticos:** Baixo

---

## Próximos Passos

Ver documento separado: `NEXT_STEPS_RECOMMENDED.md`
