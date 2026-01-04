# 02 - Mapa de Imports Baseline

> **Versão de referência:** v1.5.35  
> **Data:** 2025-01-02  
> **Última atualização:** 2025-01-02 (Correção via AST)  
> **Método:** Python AST (`ast.parse`) - contagem determinística

Este documento registra todos os imports que serão afetados pela refatoração.

---

## 📊 Resumo de Contagens

| Padrão de Import | Quantidade | Método Anterior |
|------------------|------------|-----------------|
| `infra.*` | **312** | ~~36~~ |
| `data.*` | **47** | ~~12~~ |
| `adapters.*` | **30** | ~~4~~ |
| `security.*` | **6** | ~~0~~ |
| `src.helpers.*` | **36** | ~~4~~ |
| `src.shared.*` | **7** | ~~3~~ |
| `src.utils.*` | **211** | ~~29~~ |
| `src.modules.*` | **1325** | ~~13~~ |
| `src.features.*` | **59** | ~~0~~ |

**Total de imports mapeados:** ~2033 ocorrências  
**Total de arquivos .py analisados:** 1001  
**Total de statements de import no projeto:** 6260

---

## 🔍 Detalhamento: Imports de `infra`

**Total:** 312 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\app_status.py` | 13 | `from infra.net_status import Status, probe` |
| 2 | `src\core\auth_bootstrap.py` | 14 | `from infra.supabase_client import bind_postgrest_auth_if_any, get_supabase` |
| 3 | `src\core\status_monitor.py` | 11 | `from infra.net_status import Status, probe` |
| 4 | `src\core\auth\auth.py` | 17 | `from infra.supabase_client import get_supabase` |
| 5 | `src\core\db_manager\db_manager.py` | 13 | `from infra.supabase_client import exec_postgrest, supabase` |
| 6 | `src\core\search\search.py` | 8 | `from infra.supabase_client import exec_postgrest, is_supabase_online, supabase` |
| 7 | `src\core\services\clientes_service.py` | 13 | `from infra.supabase_client import exec_postgrest, supabase` |
| 8 | `src\core\services\lixeira_service.py` | 17 | `from infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID` |
| 9 | `src\core\services\lixeira_service.py` | 18 | `from infra.supabase_client import exec_postgrest` |
| 10 | `src\core\services\lixeira_service.py` | 30 | `from infra.supabase_client import supabase` |

**...e mais 302 imports**

### Módulos mais usados de `infra`:
- `infra.supabase_client` - Cliente Supabase principal (maioria dos imports)
- `infra.db_schemas` - Schemas e constantes de banco
- `infra.net_status` - Status de conexão de rede
- `infra.healthcheck` - Verificação de saúde
- `infra.repositories.*` - Repositórios de dados

### Distribuição por diretório consumidor:
- `src/core/` - Alta concentração
- `src/modules/hub/` - Muitos imports de repositories
- `src/modules/anvisa/` - Integração com backend
- `infra/` (interno) - Imports entre módulos infra

---

## 🔍 Detalhamento: Imports de `data`

**Total:** 47 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\core\auth_bootstrap.py` | 8 | `from data.auth_bootstrap import _get_access_token` |
| 2 | `src\core\services\lixeira_service.py` | 16 | `from data.supabase_repo import delete_passwords_by_client` |
| 3 | `src\features\cashflow\repository.py` | 14 | `from data.supabase_repo import (...)` |
| 4 | `src\features\regulations\repository.py` | 14 | `from data.domain_types import RegObligationRow` |
| 5 | `src\features\regulations\repository.py` | 15 | `from data.supabase_repo import (...)` |
| 6 | `src\features\regulations\service.py` | 15 | `from data.domain_types import RegObligationRow` |
| 7 | `src\features\tasks\repository.py` | 14 | `from data.domain_types import RCTaskRow` |
| 8 | `src\features\tasks\repository.py` | 15 | `from data.supabase_repo import (...)` |
| 9 | `src\features\tasks\service.py` | 13 | `from data.domain_types import RCTaskRow` |
| 10 | `src\features\tasks\service.py` | 14 | `from data.supabase_repo import PostgrestAPIError, get_supabase_client` |

**...e mais 37 imports**

### Módulos de `data`:
- `data.supabase_repo` - Repositório principal Supabase
- `data.domain_types` - TypedDicts e tipos de domínio
- `data.auth_bootstrap` - Bootstrap de autenticação

---

## 🔍 Detalhamento: Imports de `adapters`

**Total:** 30 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\core\api\api_files.py` | 14 | `from adapters.storage import api as storage_api` |
| 2 | `src\core\api\api_files.py` | 26 | `from adapters.storage import api as storage_api` |
| 3 | `src\core\api\api_notes.py` | 20 | `from adapters.storage import api as storage_api` |
| 4 | `src\core\services\lixeira_service.py` | 11 | `from adapters.storage.api import delete_file as storage_delete_file` |
| 5 | `src\core\services\lixeira_service.py` | 12 | `from adapters.storage.api import list_files as storage_list_files` |
| 6 | `src\core\services\lixeira_service.py` | 13 | `from adapters.storage.api import upload_file as storage_upload_file` |
| 7 | `src\core\services\lixeira_service.py` | 14 | `from adapters.storage.api import using_storage_backend` |
| 8 | `src\core\services\lixeira_service.py` | 15 | `from adapters.storage.supabase_storage import SupabaseStorageAdapter` |
| 9 | `src\modules\anvisa\views\anvisa_footer.py` | 181 | `from adapters.storage.api import upload_file` |
| 10 | `src\modules\clientes\service.py` | 13 | `from adapters.storage.api import (...)` |

**...e mais 20 imports**

### Módulos de `adapters`:
- `adapters.storage.api` - API de abstração de storage
- `adapters.storage.supabase_storage` - Implementação Supabase
- `adapters.storage.port` - Interface/Port (hexagonal)

---

## 🔍 Detalhamento: Imports de `security`

**Total:** 6 ocorrências

### Todos os exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\modules\passwords\controller.py` | 7 | `from security.crypto import decrypt_text` |
| 2 | `data\supabase_repo.py` | 41 | `from security.crypto import decrypt_text, encrypt_text` |
| 3 | `tests\integration\passwords\test_passwords_crypto_integration.py` | 13 | `from security import crypto` |
| 4 | `tests\unit\security\test_crypto_edge_cases.py` | 14 | `from security.crypto import encrypt_text, decrypt_text, _reset_fernet_cache` |
| 5 | `tests\unit\security\test_crypto_keyring.py` | 8 | `from security import crypto` |
| 6 | `tests\unit\security\test_security_crypto_fase33.py` | 14 | `from security import crypto` |

### Módulos de `security`:
- `security.crypto` - Criptografia de senhas (único módulo usado)

---

## 🔍 Detalhamento: Imports de `src.helpers`

**Total:** 36 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\app_utils.py` | 37 | `from src.helpers.formatters import fmt_datetime_br` |
| 2 | `src\modules\anvisa\views\anvisa_screen.py` | 24 | `from src.helpers.auth_utils import current_user_id` |
| 3 | `src\modules\auditoria\viewmodel.py` | 8 | `from src.helpers.formatters import format_cnpj, fmt_datetime_br` |
| 4 | `src\modules\auditoria\views\client_helpers.py` | 5 | `from src.helpers.formatters import format_cnpj` |
| 5 | `src\modules\auditoria\views\main_frame.py` | 12 | `from src.helpers.formatters import fmt_datetime_br` |
| 6 | `src\modules\auditoria\views\upload_flow.py` | 124 | `from src.helpers.formatters import format_cnpj` |
| 7 | `src\modules\clientes\viewmodel.py` | 529 | `from src.helpers.formatters import fmt_datetime_br` |
| 8 | `src\modules\clientes\forms\client_picker.py` | 34 | `from src.helpers.formatters import format_cnpj as _format_cnpj_canonical` |
| 9 | `src\modules\clientes\forms\_prepare.py` | 15 | `from src.helpers.auth_utils import current_user_id, resolve_org_id` |
| 10 | `src\modules\clientes\forms\_prepare.py` | 16 | `from src.helpers.datetime_utils import now_iso_z` |

**...e mais 26 imports**

### Módulos de `src.helpers`:
- `src.helpers.formatters` - Formatação de CNPJ, datas
- `src.helpers.auth_utils` - Utilitários de autenticação
- `src.helpers.datetime_utils` - Utilitários de data/hora
- `src.helpers.storage_errors` - Classificação de erros
- `src.helpers.storage_utils` - Utilitários de storage

---

## 🔍 Detalhamento: Imports de `src.shared`

**Total:** 7 ocorrências

### Todos os exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\modules\auditoria\storage.py` | 9 | `from src.shared.storage_ui_bridge import build_client_prefix as _build_client_prefix_shared` |
| 2 | `src\modules\clientes\forms\client_subfolder_prompt.py` | 15 | `from src.shared.subfolders import sanitize_subfolder_name` |
| 3 | `src\modules\uploads\components\helpers.py` | 13 | `from src.shared.storage_ui_bridge import build_client_prefix` |
| 4 | `src\ui\subpastas_dialog.py` | 14 | `from src.shared.subfolders import sanitize_subfolder_name` |
| 5 | `tests\shared\test_storage_ui_bridge.py` | 8 | `import src.shared.storage_ui_bridge as bridge` |
| 6 | `tests\shared\test_subfolders.py` | 8 | `from src.shared.subfolders import (...)` |
| 7 | `tests\unit\core\test_text_normalization_canonical_fase4.py` | 183 | `from src.shared.subfolders import _strip_diacritics as subfolder_strip` |

### Módulos de `src.shared`:
- `src.shared.storage_ui_bridge` - Bridge entre storage e UI
- `src.shared.subfolders` - Lógica de subpastas

---

## 🔍 Detalhamento: Imports de `src.utils`

**Total:** 211 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\app_core.py` | 250 | `from src.utils.helpers import check_cloud_only_block` |
| 2 | `src\app_core.py` | 272 | `from src.utils.subpastas_config import load_subpastas_config` |
| 3 | `src\app_core.py` | 201 | `from src.utils.file_utils import ensure_subpastas, write_marker` |
| 4 | `src\app_core.py` | 202 | `from src.utils.subpastas_config import load_subpastas_config` |
| 5 | `src\app_gui.py` | 65 | `from src.utils.errors import install_global_exception_hook` |
| 6 | `src\config\environment.py` | 19 | `from src.utils.resource_path import resource_path` |
| 7 | `src\core\auth_bootstrap.py` | 11 | `from src.utils import prefs as prefs_utils` |
| 8 | `src\core\auth_bootstrap.py` | 261 | `from src.utils.network import check_internet_connectivity` |
| 9 | `src\core\bootstrap.py` | 17 | `from src.utils.resource_path import resource_path` |
| 10 | `src\core\bootstrap.py` | 91 | `from src.utils.helpers import configure_hidpi_support` |

**...e mais 201 imports**

### Módulos mais usados de `src.utils`:
- `src.utils.resource_path` - Caminhos de recursos
- `src.utils.helpers` - Helpers gerais
- `src.utils.network` - Utilitários de rede
- `src.utils.prefs` - Preferências do usuário
- `src.utils.subpastas_config` - Configuração de subpastas
- `src.utils.file_utils` - Utilitários de arquivo
- `src.utils.errors` - Tratamento de erros

---

## 🔍 Detalhamento: Imports de `src.modules`

**Total:** 1325 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\app_core.py` | 13 | `from src.modules.clientes.service import get_cliente_by_id, mover_cliente_para_lixeira` |
| 2 | `src\app_core.py` | 16 | `from src.modules.lixeira import abrir_lixeira as _module_abrir_lixeira, refresh_if_open as _module_refresh_if_open` |
| 3 | `src\app_core.py` | 86 | `from src.modules.clientes.forms.client_form import form_cliente` |
| 4 | `src\app_core.py` | 94 | `from src.modules.clientes.forms.client_form import form_cliente` |
| 5 | `src\app_core.py` | 271 | `from src.modules.clientes.forms import open_subpastas_dialog` |
| 6 | `src\app_core.py` | 297 | `from src.modules.lixeira.views.lixeira import abrir_lixeira as _abrir` |
| 7 | `src\app_gui.py` | 20 | `from src.modules.main_window.views.main_window import App` |
| 8 | `src\app_gui.py` | 91 | `from src.modules.login.view import show_splash` |
| 9 | `src\app_gui.py` | 34 | `from src.modules.main_window.views.constants import APP_ICON_PATH` |
| 10 | `src\app_gui.py` | 35 | `from src.modules.main_window.views.helpers import resource_path` |

**...e mais 1315 imports**

### Módulos mais referenciados em `src.modules`:
- `src.modules.clientes.*` - Módulo de clientes
- `src.modules.hub.*` - Dashboard/Hub
- `src.modules.main_window.*` - Janela principal
- `src.modules.anvisa.*` - Integração Anvisa
- `src.modules.login.*` - Autenticação
- `src.modules.uploads.*` - Upload de arquivos
- `src.modules.lixeira.*` - Lixeira

---

## 🔍 Detalhamento: Imports de `src.features`

**Total:** 59 ocorrências

### 10 Exemplos:

| # | Arquivo | Linha | Código |
|---|---------|-------|--------|
| 1 | `src\features\regulations\service.py` | 16 | `from src.features.regulations.repository import list_obligations_for_org` |
| 2 | `src\modules\cashflow\service.py` | 9 | `from src.features.cashflow import repository` |
| 3 | `src\modules\cashflow\views\fluxo_caixa_frame.py` | 11 | `from src.features.cashflow import repository as repo` |
| 4 | `src\modules\cashflow\views\fluxo_caixa_frame.py` | 213 | `from src.features.cashflow.dialogs import EntryDialog` |
| 5 | `src\modules\cashflow\views\fluxo_caixa_frame.py` | 243 | `from src.features.cashflow.dialogs import EntryDialog` |
| 6 | `src\modules\clientes\views\client_obligations_frame.py` | 15 | `from src.features.regulations.service import delete_obligation, list_obligations_for_client` |
| 7 | `src\modules\clientes\views\obligation_dialog.py` | 15 | `from src.features.regulations.service import (...)` |
| 8 | `src\modules\hub\dashboard\data_access.py` | 80 | `from src.features.tasks.repository import list_tasks_for_org` |
| 9 | `src\modules\hub\dashboard\data_access.py` | 136 | `from src.features.regulations.repository import list_obligations_for_org` |
| 10 | `src\modules\hub\dashboard\data_access.py` | 237 | `from src.features.tasks.repository import list_tasks_for_org` |

**...e mais 49 imports**

### Módulos de `src.features`:
- `src.features.cashflow.*` - Fluxo de caixa
- `src.features.regulations.*` - Obrigações regulatórias
- `src.features.tasks.*` - Tarefas

---

## ⚠️ Pontos de Atenção

### 1. Imports Lazy (dentro de funções)

A grande maioria dos imports está **dentro de funções** (lazy imports), não no topo do arquivo. Isso é intencional para:
- Evitar imports circulares
- Reduzir tempo de startup
- Permitir imports condicionais

**Impacto:** Scripts de refatoração precisam processar TODO o corpo das funções, não apenas o topo dos arquivos.

### 2. Dependências Cruzadas

```
infra/ ←→ data/     (imports bidirecionais)
src/   →  infra/    (src depende de infra)
src/   →  data/     (src depende de data)
src/   →  adapters/ (src depende de adapters)
data/  →  security/ (data usa crypto)
```

### 3. Volume de Trabalho Real

| O que | Estimativa |
|-------|------------|
| Imports a atualizar (total) | ~2033 |
| Arquivos únicos afetados | ~400+ |
| Fases de migração | 6 (uma por pasta + build) |

---

## 📋 Método de Coleta

```python
import ast
import os
from collections import defaultdict

DIRS = ['src', 'infra', 'data', 'adapters', 'security', 'tests']
IGNORE = {'.venv', '__pycache__', 'dist', 'build', '.git', 'htmlcov', 'third_party'}
PREFIXES = ['infra', 'data', 'adapters', 'security',
            'src.helpers', 'src.shared', 'src.utils', 'src.modules', 'src.features']

results = defaultdict(list)

def get_import_module(node):
    modules = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            modules.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            modules.append(node.module)
    return modules

for dir_name in DIRS:
    for root, dirs, files in os.walk(dir_name):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                    tree = ast.parse(fp.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        for mod in get_import_module(node):
                            for prefix in PREFIXES:
                                if mod == prefix or mod.startswith(prefix + '.'):
                                    results[prefix].append((filepath, node.lineno))
```

**Executado em:** 2025-01-02  
**Ambiente:** Python 3.11, Windows 11

```powershell
# Contar imports de infra
Select-String -Path "*.py","src\**\*.py","infra\**\*.py" -Pattern "from infra\b|^import infra\b" -AllMatches | Measure-Object -Line

# Exemplos de imports
Select-String -Path "*.py","src\**\*.py" -Pattern "from infra\b" -AllMatches | Select-Object -First 10
```
