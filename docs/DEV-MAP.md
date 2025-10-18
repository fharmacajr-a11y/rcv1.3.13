# DEV-MAP: Onde Editar o Quê

**Versão:** 1.0.15 (Batch 17X)  
**Propósito:** Mapa de navegação rápido para desenvolvedores — identifica onde mexer para cada funcionalidade.

---

## 📍 Índice Rápido

| Funcionalidade | Arquivo(s) Principal(is) |
|----------------|--------------------------|
| **Entry point** | `app_gui.py` |
| **Janela principal** | `gui/main_window.py` |
| **Splash screen** | `gui/splash.py` |
| **Login** | `ui/login/login.py` |
| **Menu superior** | `gui/menu_bar.py` |
| **Barra de título/status** | `ui/topbar.py` |
| **Navegação entre telas** | `application/navigation_controller.py` |
| **Status online/env** | `application/status_monitor.py` |
| **Atalhos de teclado** | `application/keybindings.py` |
| **Autenticação de usuário** | `application/auth_controller.py` |
| **Hub (tela inicial)** | `gui/hub_screen.py` |
| **Tela principal (CRUD)** | `gui/main_screen.py` |
| **Upload de arquivos** | `core/services/upload_service.py`, `ui/dialogs/upload_progress.py` |
| **Lixeira** | `core/services/lixeira_service.py`, `ui/lixeira/lixeira.py` |
| **Browser de arquivos** | `ui/files_browser.py` |
| **Subpastas** | `ui/subpastas/dialog.py`, `utils/subpastas_config.py` |
| **Busca de clientes** | `core/search/search.py` |
| **Storage (facade)** | `adapters/storage/api.py` |
| **Supabase adapter** | `adapters/storage/supabase_storage.py` |
| **Temas** | `utils/themes.py`, `utils/theme_manager.py` |
| **Config/paths** | `config/paths.py`, `shared/config/environment.py` |
| **Logging/auditoria** | `shared/logging/audit.py`, `shared/logging/configure.py` |

---

## 🏗️ Entrypoint & Janela Principal

### `app_gui.py` (Stub/Entrypoint)
**O que faz:**  
- Entry point da aplicação
- Configura modo cloud-only (`RC_NO_LOCAL_FS=1`)
- Carrega `.env` usando `resource_path` (PyInstaller-aware)
- Reexporta classe `App` de `gui.main_window`
- Inicia splash → login → janela principal

**Principais símbolos:**
- `App` (reexport de `gui.main_window.App`)
- Lógica de startup no `if __name__ == "__main__"`

**Quando editar:**
- Mudar lógica de inicialização (splash/login flow)
- Adicionar flags de ambiente global
- Modificar sequência de bootstrap

---

### `gui/main_window.py: class App`
**O que faz:**  
- Janela principal da aplicação (herda `tb.Window`)
- Gerencia frames (HubScreen, MainScreenFrame)
- Integra controllers: NavigationController, StatusMonitor, AuthController
- Configura menu bar, top bar, atalhos de teclado
- CRUD de clientes (criar/editar/deletar)
- Operações: upload, download zip, lixeira, subpastas

**Principais métodos (614 linhas):**
- `__init__()` — setup inicial
- `apply_theme(theme_name)` — troca de tema via `utils.themes`
- `_criar_cliente()`, `_editar_cliente()`, `_deletar_clientes()` — CRUD
- `_abrir_upload()`, `_abrir_lixeira()`, `_ver_subpastas()` — dialogs
- `_baixar_zip()` — download de pasta do storage
- `_atualizar_lista()` — refresh da treeview de clientes
- `_sair()` — encerramento da aplicação

**Quando editar:**
- Adicionar/remover menus
- Alterar layout da janela principal
- Modificar fluxos de CRUD
- Integrar novos dialogs ou telas

---

## 🎨 UI Base

### `ui/topbar.py: class TopBar`
**O que faz:**  
- Barra superior com botão "Início" e labels de status (env/user/online)
- Callback `on_home_click` para navegar ao hub
- Atualiza status via `set_status_text()` e `set_env_text()`

**Quando editar:**
- Modificar layout da barra superior
- Adicionar botões ou indicadores
- Alterar cores/estilos de status

---

### `gui/menu_bar.py: class AppMenuBar`
**O que faz:**  
- Menu superior: Arquivo (Sair), Exibir (Temas), Ajuda (Sobre)
- Callbacks para ações: `on_sair`, `on_sobre`, `on_theme_change`
- Detecta tema atual via `current_theme_callback()`

**Quando editar:**
- Adicionar/remover itens de menu
- Criar novos menus (ex: Ferramentas, Relatórios)
- Modificar atalhos de menu

---

### `gui/splash.py: splash_screen()`
**O que faz:**  
- Tela de carregamento inicial (logo + barra de progresso)
- Autoclose após 2 segundos
- Usa `resource_path("rc.ico")` para ícone

**Quando editar:**
- Alterar duração do splash
- Modificar logo ou mensagem
- Adicionar animações

---

## 🧭 Navegação & Estado

### `application/navigation_controller.py: class NavigationController`
**O que faz:**  
- Gerencia troca de frames (show_frame, hide_frame)
- Notifica TopBar sobre mudanças (habilitar/desabilitar botão Início)
- Cache de frames criados

**Principais métodos:**
- `show_frame(frame_name, **kwargs)` — exibe frame e oculta outros
- `current_frame() → str` — retorna frame ativo
- `home_button_state(enabled: bool)` — controla botão Início

**Quando editar:**
- Adicionar nova tela/frame
- Modificar lógica de navegação
- Implementar histórico de navegação

---

### `application/status_monitor.py: class StatusMonitor`
**O que faz:**  
- Monitora status de rede (online/offline) via polling
- Atualiza TopBar com status de conectividade
- Configura modo cloud-only vs. local

**Principais métodos:**
- `start()` — inicia polling de status
- `stop()` — para polling
- `_check_status()` — verifica conectividade

**Quando editar:**
- Alterar intervalo de polling
- Modificar lógica de detecção de status
- Adicionar métricas de conectividade

---

### `application/keybindings.py: bind_global_shortcuts()`
**O que faz:**  
- Configura atalhos de teclado globais
- Atalhos: Ctrl+Q (sair), F5 (refresh), Ctrl+N (novo cliente), etc.

**Quando editar:**
- Adicionar/modificar atalhos
- Implementar novos comandos de teclado

---

### `application/auth_controller.py: class AuthController`
**O que faz:**  
- Gerencia estado de autenticação do usuário
- Métodos: `current_user()`, `set_current_user()`, `require()`

**Quando editar:**
- Modificar lógica de autenticação
- Adicionar papéis/permissões
- Integrar com sistema de auth externo

---

## 🖥️ Telas

### `gui/hub_screen.py: class HubScreen`
**O que faz:**  
- Tela inicial (hub) com cards de navegação
- Cards: "Meus Clientes", "Lixeira", etc.
- Callbacks para navegação: `on_show_main`, `on_show_lixeira`

**Quando editar:**
- Adicionar/remover cards
- Modificar layout do hub
- Alterar navegação inicial

---

### `gui/main_screen.py: class MainScreenFrame`
**O que faz:**  
- Tela principal de CRUD de clientes
- Treeview com lista de clientes
- Botões: Novo, Editar, Deletar, Upload, Baixar ZIP, etc.
- Busca em tempo real via `core/search/search.py`

**Principais métodos:**
- `atualizar_lista()` — refresh da treeview
- `_on_novo_click()`, `_on_editar_click()`, `_on_deletar_click()` — callbacks CRUD
- `_on_busca_change()` — busca em tempo real

**Quando editar:**
- Modificar colunas da treeview
- Adicionar filtros/ordenação
- Alterar layout dos botões

---

### `gui/placeholders.py: PlaceholderFrame`
**O que faz:**  
- Telas "Em breve" para funcionalidades futuras

**Quando editar:**
- Criar novas telas placeholder

---

## 🔄 Diálogos e Fluxos

### `ui/dialogs/upload_progress.py: show_upload_progress()`
**O que faz:**  
- Dialog modal de progresso de upload
- Barra indeterminada + mensagem
- Autoclose ou close manual via callback

**Quando editar:**
- Modificar UI de progresso
- Adicionar cancelamento de upload
- Mostrar progresso determinado (percentual)

---

### `ui/files_browser.py: open_files_browser()`
**O que faz:**  
- Dialog de navegação de arquivos no storage (cloud)
- Lista pastas/arquivos de um cliente
- Permite download de arquivos individuais ou pasta completa (zip)

**Principais funções:**
- `open_files_browser(parent, org_id, client_id)` — abre dialog
- Callbacks: download individual, download zip

**Quando editar:**
- Adicionar preview de arquivos
- Implementar upload inline
- Modificar layout de navegação

---

### `ui/login/login.py: class LoginDialog`
**O que faz:**  
- Dialog de login com usuário/senha
- Valida contra `core/auth/auth.py`
- Retorna usuário autenticado ou None

**Quando editar:**
- Modificar UI de login
- Adicionar autenticação via token/OAuth
- Implementar "lembrar senha"

---

### `ui/subpastas/dialog.py: open_subpastas_dialog()`
**O que faz:**  
- Dialog de seleção de subpasta para upload (SIFAP, GERAL, etc.)
- Usa `utils/subpastas_config.py` para lista de subpastas obrigatórias

**Quando editar:**
- Adicionar/remover subpastas
- Modificar validação de subpastas
- Permitir criação de subpastas custom

---

### `ui/lixeira/lixeira.py: abrir_lixeira()`
**O que faz:**  
- Dialog de lixeira (clientes deletados)
- Lista clientes com soft_delete=1
- Permite restaurar ou purgar permanentemente

**Principais funções:**
- `abrir_lixeira(parent, org_id)` — abre dialog
- Callbacks: restaurar, purgar

**Quando editar:**
- Modificar UI da lixeira
- Adicionar filtros por data de deleção
- Implementar restauração em lote

---

## 🔧 Regras/Serviços

### `core/services/upload_service.py`
**O que faz:**  
- Orquestra upload de arquivos para storage
- Valida arquivos, detecta PDFs, classifica documentos
- Delega upload para `adapters/storage/api.py`

**Principais funções:**
- `upload_folder(local_path, org_id, client_id, subdir)` — upload de pasta
- `upload_file(file_path, remote_path)` — upload de arquivo único

**Quando editar:**
- Modificar validação de arquivos
- Adicionar novos tipos de documentos
- Implementar compressão/otimização

---

### `core/services/lixeira_service.py`
**O que faz:**  
- Gerencia operações de lixeira (soft delete, restore, purge)
- Integra com storage adapter para mover arquivos

**Principais funções:**
- `soft_delete_clients(org_id, client_ids)` — marca clientes como deletados
- `restore_clients(org_id, client_ids)` — restaura clientes
- `purge_clients(org_id, client_ids)` — deleta permanentemente

**Quando editar:**
- Modificar lógica de soft delete
- Adicionar período de retenção
- Implementar lixeira automática

---

### `core/services/clientes_service.py`
**O que faz:**  
- CRUD de clientes (insert, update, delete)
- Logging de auditoria via `shared/logging/audit.py`
- Criação de pastas no storage

**Principais funções:**
- `create_cliente(data)` — cria novo cliente
- `update_cliente(client_id, data)` — atualiza cliente
- `delete_cliente(client_id)` — soft delete

**Quando editar:**
- Adicionar campos de cliente
- Modificar validação de dados
- Implementar versionamento

---

### `core/search/search.py: search_clientes()`
**O que faz:**  
- Busca em tempo real de clientes por CNPJ, razão social, nome fantasia
- Usa `core/db_manager` para query

**Quando editar:**
- Adicionar campos de busca
- Implementar busca fuzzy
- Otimizar performance

---

## 💾 Storage & Config

### `adapters/storage/api.py`
**O que faz:**  
- Facade de alto nível para operações de storage
- Abstrai backend (Supabase, S3, etc.)

**Principais funções:**
- `upload_file(file_path, bucket, remote_path)` — upload
- `download_file(bucket, remote_path, local_path)` — download
- `list_files(bucket, prefix)` — listagem
- `download_folder_zip(bucket, prefix)` — download de pasta como zip

**Quando editar:**
- Adicionar novos backends de storage
- Implementar cache local
- Modificar lógica de retry/timeout

---

### `adapters/storage/supabase_storage.py: class SupabaseStorageAdapter`
**O que faz:**  
- Implementação concreta de StoragePort para Supabase
- Usa `infra/supabase_client.py` para acesso ao SDK

**Quando editar:**
- Modificar lógica de Supabase
- Adicionar buckets adicionais
- Implementar permissões granulares

---

### `utils/subpastas_config.py`
**O que faz:**  
- Define subpastas obrigatórias para cada cliente (SIFAP, GERAL, etc.)
- Função: `get_required_subpastas() → list[str]`

**Quando editar:**
- Adicionar/remover subpastas obrigatórias
- Modificar validação de subpastas

---

### `config/paths.py`
**O que faz:**  
- Centraliza paths e flags do projeto
- Variáveis: `BASE_DIR`, `DB_PATH`, `DOCS_DIR`, `CLOUD_ONLY`

**Quando editar:**
- Adicionar novos paths
- Modificar lógica de detecção de ambiente

---

### `shared/config/environment.py`
**O que faz:**  
- Helpers para carregar variáveis de ambiente
- Funções: `load_env()`, `env_str()`, `env_bool()`, `cloud_only_default()`

**Quando editar:**
- Adicionar novos helpers de env
- Modificar lógica de fallback

---

### `shared/logging/audit.py`
**O que faz:**  
- Logging de auditoria para operações críticas
- Funções: `log_client_action()`, `log_upload()`, etc.

**Quando editar:**
- Adicionar novos eventos de auditoria
- Modificar formato de log
- Integrar com sistema externo de auditoria

---

### `shared/logging/configure.py: setup_logging()`
**O que faz:**  
- Configura logging global da aplicação
- Níveis, formatters, handlers

**Quando editar:**
- Modificar nível de log
- Adicionar handlers (file, syslog, etc.)
- Configurar rotação de logs

---

## 🛠️ Infra & Scripts

### `infrastructure/scripts/healthcheck.py`
**O que faz:**  
- Script CLI de healthcheck/diagnóstico (959 linhas)
- Validação de imports, smoke tests, linting, coverage

**Quando executar:**
- `python infrastructure/scripts/healthcheck.py --smoke`
- `python infrastructure/scripts/healthcheck.py --lint`

---

### `scripts/dev/loc_report.py`
**O que faz:**  
- Gera relatório de LOC (lines of code) por arquivo
- Output: top 15 arquivos maiores + total

**Quando executar:**
- `python scripts/dev/loc_report.py`

---

### `scripts/dev/find_unused.py`
**O que faz:**  
- Scanner heurístico de dead-code
- Detecta módulos órfãos e low-usage

**Quando executar:**
- `python scripts/dev/find_unused.py --verbose`

---

## 🎨 Temas

### `utils/themes.py`
**O que faz:**  
- Gerenciamento de temas (claro/escuro)
- Funções: `load_theme()`, `save_theme()`, `apply_theme(root, theme_name)`
- Suporta modo cloud-only (sem escrita em disco)

**Quando editar:**
- Adicionar novos temas
- Modificar tema padrão
- Implementar temas customizáveis

---

### `utils/theme_manager.py: class ThemeManager`
**O que faz:**  
- Singleton para gerenciar estado de tema
- Integra com `ttkbootstrap.Style`

**Quando editar:**
- Modificar lógica de aplicação de tema
- Adicionar callbacks de mudança de tema

---

## 📋 Forms & CRUD

### `ui/forms/forms.py: form_cliente()`
**O que faz:**  
- Dialog de formulário para criar/editar cliente
- Campos: razão social, CNPJ, nome fantasia, WhatsApp, observações

**Quando editar:**
- Adicionar/remover campos
- Modificar validação
- Implementar auto-complete

---

### `ui/forms/actions.py`
**O que faz:**  
- Ações relacionadas a formulários e CRUD
- Detecção de cartão CNPJ, upload automático

**Quando editar:**
- Adicionar novos workflows de CRUD
- Modificar validação de documentos

---

## 🗄️ Database & Models

### `core/db_manager/db_manager.py`
**O que faz:**  
- Gerenciamento de banco de dados SQLite (ou cloud)
- CRUD de clientes, migrations, schema

**Principais funções:**
- `init_db()`, `init_or_upgrade()` — setup
- `list_clientes()`, `get_cliente()` — queries
- `insert_cliente()`, `update_cliente()`, `delete_cliente()` — mutations

**Quando editar:**
- Adicionar tabelas/colunas
- Modificar schema
- Implementar migrations

---

### `core/models.py`
**O que faz:**  
- Modelos de dados (dataclasses/TypedDicts)

**Quando editar:**
- Adicionar novos modelos
- Modificar estrutura de dados

---

## 🔐 Auth

### `core/auth/auth.py`
**O que faz:**  
- Autenticação de usuários (PBKDF2)
- Funções: `authenticate_user()`, `create_user()`, `ensure_users_db()`

**Quando editar:**
- Modificar algoritmo de hash
- Integrar com autenticação externa
- Adicionar 2FA

---

## 🔍 Detectors

### `detectors/cnpj_card.py`
**O que faz:**  
- Detecta cartão CNPJ em PDFs
- Extrai dados via OCR/parsing

**Quando editar:**
- Melhorar precisão de detecção
- Adicionar suporte a novos formatos

---

## ⚙️ Utils

### `utils/resource_path.py: resource_path()`
**O que faz:**  
- Resolve caminhos de recursos (PyInstaller-aware)
- Usado para assets (ícones, imagens, etc.)

**Quando editar:**
- Adicionar novos paths de recursos

---

### `utils/validators.py`
**O que faz:**  
- Validadores de dados (CNPJ, email, telefone, etc.)

**Quando editar:**
- Adicionar novos validadores
- Modificar regras de validação

---

### `utils/hash_utils.py: sha256_file()`
**O que faz:**  
- Hash SHA256 de arquivos
- Detecção de duplicatas

**Quando editar:**
- Adicionar novos algoritmos de hash

---

### `app_utils.py`
**O que faz:**  
- Utilitários compartilhados (fmt_data, slugify_name, only_digits, etc.)

**Quando editar:**
- Adicionar novos helpers
- Modificar formatação

---

### `app_core.py`
**O que faz:**  
- Lógica de negócio central (antiga, parcialmente substituída por services)
- Algumas funções ainda usadas pela GUI

**Quando editar:**
- Migrar lógica para `core/services/*` (refactoring contínuo)

---

## 📝 Resumo: Fluxos Principais

| Fluxo | Arquivos Envolvidos |
|-------|---------------------|
| **Criar cliente** | `gui/main_screen.py` → `ui/forms/forms.py` → `core/services/clientes_service.py` → `core/db_manager/db_manager.py` |
| **Upload** | `gui/main_screen.py` → `ui/dialogs/upload_progress.py` → `core/services/upload_service.py` → `adapters/storage/api.py` |
| **Busca** | `gui/main_screen.py` → `core/search/search.py` → `core/db_manager/db_manager.py` |
| **Lixeira** | `gui/main_screen.py` → `ui/lixeira/lixeira.py` → `core/services/lixeira_service.py` |
| **Download ZIP** | `gui/main_screen.py` → `adapters/storage/api.py` → `adapters/storage/supabase_storage.py` |
| **Troca tema** | `gui/menu_bar.py` → `gui/main_window.py.apply_theme()` → `utils/themes.py` |
| **Login** | `app_gui.py` → `ui/login/login.py` → `core/auth/auth.py` |

---

**Última atualização:** Batch 17X  
**Total de módulos mapeados:** 50+  
**Cobertura:** ~95% do código funcional
