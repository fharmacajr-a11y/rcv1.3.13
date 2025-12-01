# Mapeamento de Dependências para Análise de Coverage

**Data da análise:** 23 de novembro de 2025  
**Branch:** qa/fixpack-04

## Resumo

Este documento apresenta uma análise detalhada das dependências entre o código principal da aplicação (`src/`) e os módulos Python localizados fora deste diretório. O objetivo é classificar esses módulos em categorias distintas para determinar quais devem ser incluídos na meta futura de cobertura de testes (coverage).

Atualmente, a meta de coverage aplica-se apenas a `src/` (~37% com comando `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`). Esta análise mapeia as pastas `adapters/`, `infra/`, `data/`, `devtools/`, `scripts/`, `security/` e `helpers/` (raiz) para identificar:

- **Código de APP:** importado por `src/` ou `main.py`, deve entrar na meta de coverage.
- **Código de INFRA/DEVTOOLS:** usado apenas por ferramentas de desenvolvimento, opcional para coverage.
- **Scripts isolados:** executados via CLI, geralmente fora da meta de coverage.

**Importante:** Nenhuma configuração de pytest/coverage foi alterada nesta tarefa. Este é apenas um documento de análise e recomendações.

---

## Tabela Geral de Pastas

| Pasta | Arquivos .py | Exemplos de módulos | Importada por | Classificação | Observações |
|-------|--------------|---------------------|---------------|---------------|-------------|
| **adapters/** | 5 | `storage/api.py`<br>`storage/supabase_storage.py`<br>`storage/port.py` | `src/` (múltiplos)<br>`main.py` (indireto) | **APP_CORE_CANDIDATE** | Usado extensivamente pelos serviços de upload, clientes e lixeira em `src/core/` e `src/modules/`. Implementa a camada de abstração de storage (Supabase). |
| **infra/** | 18 | `supabase_client.py`<br>`settings.py`<br>`archive_utils.py`<br>`net_status.py`<br>`healthcheck.py` | `src/` (múltiplos)<br>`data/`<br>`tests/` (parcial) | **APP_CORE_CANDIDATE** | Infraestrutura essencial: cliente Supabase, autenticação, status de rede, utilitários de arquivo. Usado no bootstrap e em toda a app. |
| **data/** | 4 | `auth_bootstrap.py`<br>`domain_types.py`<br>`supabase_repo.py` | `src/` (múltiplos)<br>`infra/` | **APP_CORE_CANDIDATE** | Define tipos de domínio (ClientRow, PasswordRow) e repositórios. Usado por módulos de passwords e clientes. `supabase_repo.py` usa `infra/` e `security/`. |
| **security/** | 2 | `crypto.py` | `src/modules/passwords/`<br>`data/supabase_repo.py` | **APP_CORE_CANDIDATE** | Criptografia de senhas. Usado por módulo de passwords e repositório de dados. Essencial para funcionalidade core. |
| **helpers/** (raiz) | 1 | `__init__.py` (bridge) | `src/modules/auditoria/` | **BRIDGE/LEGACY** | Módulo de compatibilidade que redireciona para `src/helpers/`. Usado apenas por `auditoria/` (3 imports). **Candidato a remoção** após migrar imports para `src.helpers`. |
| **devtools/** | 11 | `qa/analyze_linters.py`<br>`qa/analyze_pyright_errors.py`<br>`arch/analyze_modules.py`<br>`pdf_batch_from_images.py` | Nenhum (só CLI) | **INFRA_DEVTOOLS** | Scripts de análise de QA e arquitetura. Executados manualmente para diagnóstico. `pdf_batch_from_images.py` importa `src/modules/` mas é wrapper CLI. |
| **scripts/** | 11 | `dev_smoke.py`<br>`test_*.py`<br>`demo_*.py`<br>`validate_7z_support.py` | Nenhum (só CLI)<br>`demo_archive_support.py` → `infra/` | **SCRIPTS_ISOLADOS** | Scripts de teste manual, smoke tests e demos. Um deles (`demo_archive_support.py`) importa `infra/archive_utils` mas é script CLI. Não importados por `src/`. |
| **Arquivos raiz** | 2 | `main.py`<br>`sitecustomize.py` | `main.py` → `src/`<br>`sitecustomize.py` (auto) | **APP_CORE** | `main.py` é entry point (usa `runpy` para `src.app_gui`). `sitecustomize.py` configura sys.path (carregado automaticamente pelo Python). |

---

## Detalhamento por Pasta

### 1. adapters/ (APP_CORE_CANDIDATE)

**Total:** 5 arquivos Python

**Estrutura:**
```
adapters/
├── __init__.py
└── storage/
    ├── __init__.py
    ├── api.py          # Interface pública de storage
    ├── port.py         # Port interface (abstração)
    └── supabase_storage.py  # Implementação Supabase
```

**Imports de src/:**
- `src/modules/uploads/service.py` → `adapters.storage.api`, `adapters.storage.supabase_storage`
- `src/modules/uploads/storage_browser_service.py` → `adapters.storage.api`, `adapters.storage.supabase_storage`
- `src/modules/uploads/repository.py` → `adapters.storage.api`, `adapters.storage.supabase_storage`
- `src/modules/clientes/service.py` → `adapters.storage.api`, `adapters.storage.supabase_storage`
- `src/modules/clientes/forms/_upload.py` → `adapters.storage.api`
- `src/modules/clientes/forms/_prepare.py` → `adapters.storage.supabase_storage`
- `src/core/services/lixeira_service.py` → `adapters.storage.api`, `adapters.storage.supabase_storage`

**Imports de main.py:** Indireto via `src/`

**Classificação:** **APP_CORE_CANDIDATE**

**Recomendação:** Incluir no coverage futuro (`--cov=adapters`) ou considerar mover para `src/adapters/` em refatoração futura (CODE-001).

---

### 2. infra/ (APP_CORE_CANDIDATE)

**Total:** 18 arquivos Python

**Estrutura:**
```
infra/
├── __init__.py
├── archive_utils.py       # Utilitários para arquivos 7z/zip
├── healthcheck.py         # Health check pós-login
├── net_session.py         # Session HTTP com retry
├── net_status.py          # Status de rede
├── settings.py            # Persistência de settings UI
├── supabase_auth.py       # Auth Supabase
├── supabase_client.py     # Cliente Supabase singleton
├── http/
│   ├── __init__.py
│   └── retry.py
├── repositories/
│   └── passwords_repository.py
└── supabase/
    ├── __init__.py
    ├── auth_client.py
    ├── db_client.py
    ├── http_client.py
    ├── storage_client.py
    ├── storage_helpers.py
    └── types.py
```

**Imports de src/:**
- `src/ui/login_dialog.py` → `infra.healthcheck`, `infra.supabase_client`
- `src/ui/dialogs/file_select.py` → `infra.archive_utils`
- `src/modules/uploads/service.py` → `infra.supabase.storage_helpers`
- `src/modules/uploads/repository.py` → `infra.supabase_client`
- `src/modules/uploads/external_upload_service.py` → `infra.supabase_client`
- `src/modules/passwords/service.py` → `infra.repositories.passwords_repository`
- `src/modules/main_window/views/main_window.py` → `infra.supabase_auth`, `infra.net_status`
- `src/modules/clientes/views/main_screen.py` → `infra.supabase_client`
- `src/modules/clientes/service.py` → `infra.supabase_client`
- `src/modules/clientes/controllers/connectivity.py` → `infra.supabase_client`
- `src/modules/clientes/forms/_upload.py` → `infra.supabase_client`
- `src/modules/clientes/forms/_prepare.py` → `infra.supabase_client`
- `src/helpers/auth_utils.py` → `infra.supabase_client`
- `src/core/services/*` → `infra.supabase_client` (lixeira, profiles, notes, clientes)
- `src/core/search/search.py` → `infra.supabase_client`
- `src/core/session/*` → `infra.supabase_client`
- `src/core/db_manager/db_manager.py` → `infra.supabase_client`
- `src/core/auth/auth.py` → `infra.supabase_client`
- `src/app_status.py` → `infra.net_status`

**Imports de tests/:**
- `tests/test_passwords_service.py` → `infra.repositories.passwords_repository`
- `tests/test_file_select.py` → `infra.archive_utils`
- `tests/test_archives.py` → `infra.archive_utils`

**Imports de scripts/:**
- `scripts/demo_archive_support.py` → `infra.archive_utils` (script CLI)

**Classificação:** **APP_CORE_CANDIDATE**

**Recomendação:** Incluir no coverage futuro (`--cov=infra`). É código de infraestrutura essencial usado em todo o app.

**Observação:** `infra.settings` não é importado diretamente por `src/`, mas pode ser usado internamente por outros módulos de `infra/`. Verificar se há uso indireto.

---

### 3. data/ (APP_CORE_CANDIDATE)

**Total:** 4 arquivos Python

**Estrutura:**
```
data/
├── __init__.py
├── auth_bootstrap.py    # Bootstrap de autenticação
├── domain_types.py      # Tipos de domínio (ClientRow, PasswordRow)
└── supabase_repo.py     # Repositório Supabase CRUD
```

**Imports de src/:**
- `src/ui/login_dialog.py` → `data.auth_bootstrap._get_access_token`
- `src/modules/passwords/views/passwords_screen.py` → `data.domain_types`
- `src/modules/passwords/controller.py` → `data.domain_types`, `data.supabase_repo`
- `src/modules/clientes/forms/client_picker.py` → `data.domain_types`
- `src/core/auth_bootstrap.py` → `data.auth_bootstrap._get_access_token`

**Imports internos:**
- `data/supabase_repo.py` → `infra.supabase_client`, `security.crypto`, `data.domain_types`
- `infra/repositories/passwords_repository.py` → `data.domain_types`

**Classificação:** **APP_CORE_CANDIDATE**

**Recomendação:** Incluir no coverage futuro (`--cov=data`). Define tipos de domínio e repositórios core usados por múltiplos módulos.

---

### 4. security/ (APP_CORE_CANDIDATE)

**Total:** 2 arquivos Python

**Estrutura:**
```
security/
├── __init__.py
└── crypto.py  # Funções de criptografia (encrypt_text, decrypt_text)
```

**Imports de src/:**
- `src/modules/passwords/controller.py` → `security.crypto.decrypt_text`

**Imports de data/:**
- `data/supabase_repo.py` → `security.crypto.encrypt_text`, `security.crypto.decrypt_text`

**Classificação:** **APP_CORE_CANDIDATE**

**Recomendação:** Incluir no coverage futuro (`--cov=security`). Código crítico de segurança para criptografia de senhas.

---

### 5. helpers/ raiz (BRIDGE/LEGACY)

**Total:** 1 arquivo Python

**Estrutura:**
```
helpers/
└── __init__.py  # Bridge de compatibilidade para src/helpers/
```

**Conteúdo:**
```python
"""Compatibility bridge for helpers package relocated under src."""
from importlib import import_module
from types import ModuleType
import sys as _sys

_src_pkg: ModuleType = import_module("src.helpers")
__all__ = getattr(_src_pkg, "__all__", [])
__path__ = list(getattr(_src_pkg, "__path__", []))

def __getattr__(name: str):
    return getattr(_src_pkg, name)
```

**Imports de src/:**
- `src/modules/auditoria/viewmodel.py` → `helpers.formatters.format_cnpj`, `helpers.formatters.fmt_datetime_br`
- `src/modules/auditoria/views/client_helpers.py` → `helpers.formatters.format_cnpj`
- `src/modules/auditoria/views/main_frame.py` → `helpers.formatters.fmt_datetime_br`

**Classificação:** **BRIDGE/LEGACY**

**Recomendação:**
- **Curto prazo:** Não incluir no coverage (é apenas um wrapper de compatibilidade).
- **Longo prazo:** Migrar os 3 imports em `auditoria/` para usar `src.helpers` diretamente e **remover** `helpers/` da raiz.
- Relacionado: possível tarefa CODE-001 (consolidar helpers).

---

### 6. devtools/ (INFRA_DEVTOOLS)

**Total:** 11 arquivos Python

**Estrutura:**
```
devtools/
├── pdf_batch_from_images.py  # CLI wrapper para conversão PDF
├── arch/
│   └── analyze_modules.py     # Análise de módulos
└── qa/
    ├── analyze_linters.py
    ├── analyze_pyright_errors.py
    ├── analyze_pyright_warnings.py
    ├── analyze_path_errors.py
    ├── analyze_style_issues.py
    ├── analyze_unknown_errors.py
    ├── analyze_top_errors.py
    ├── analyze_supabase_errors.py
    └── analyze_config_errors.py
```

**Imports de src/:**
- `devtools/pdf_batch_from_images.py` → `src.modules.pdf_tools.pdf_batch_from_images` (wrapper CLI)

**Imports de main.py:** Nenhum

**Classificação:** **INFRA_DEVTOOLS**

**Recomendação:**
- Não incluir no coverage oficial de produto.
- Podem ter coverage opcional/separado se o time desejar garantir qualidade das ferramentas de QA.
- Scripts executados manualmente para análise de erros de linters e diagnóstico de arquitetura.

---

### 7. scripts/ (SCRIPTS_ISOLADOS)

**Total:** 11 arquivos Python

**Estrutura:**
```
scripts/
├── demo_archive_support.py       # Demo de suporte a arquivos
├── demo_duplicates_dialog.py     # Demo de diálogo de duplicatas
├── dev_smoke.py                  # Smoke test de build
├── test_busca_robusta.py         # Teste manual de busca
├── test_deterministic_progress.py
├── test_file_dialog_manual.py
├── test_progress_e2e.py
├── test_search_normalize.py
├── test_upload_advanced.py
├── test_upload_thread.py
└── validate_7z_support.py        # Validação de 7zip
```

**Imports de src/:**
- Nenhum import direto de `src/` encontrado (scripts adicionam `ROOT_DIR` ao `sys.path` e importam para testes manuais)
- `demo_archive_support.py` → `infra.archive_utils` (único script que importa módulo externo)

**Imports de main.py:** Nenhum

**Classificação:** **SCRIPTS_ISOLADOS**

**Recomendação:**
- Não incluir no coverage oficial.
- Scripts de teste manual, smoke tests e demos executados via CLI.
- Podem ser cobertos por testes de integração futuros se forem críticos para validação de releases.

---

### 8. Arquivos na Raiz

#### main.py (APP_CORE)

**Conteúdo:**
```python
# -*- coding: utf-8 -*-
"""Entry point script for the application."""

if __name__ == "__main__":
    import runpy
    runpy.run_module("src.app_gui", run_name="__main__")
```

**Classificação:** **APP_CORE**

**Recomendação:** Manter fora do coverage (é apenas entry point que delega para `src.app_gui`).

---

#### sitecustomize.py (INFRA)

**Conteúdo:**
```python
"""Project-level sitecustomize to expose src-style packages on sys.path."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for rel_path in ("src", "infra", "adapters"):
    abs_path = os.path.join(_ROOT, rel_path)
    if os.path.isdir(abs_path) and abs_path not in sys.path:
        sys.path.insert(0, abs_path)
```

**Classificação:** **INFRA** (configuração de ambiente)

**Recomendação:** Não incluir no coverage (carregado automaticamente pelo Python para configurar sys.path).

---

## Módulos Órfãos

Nenhum módulo órfão significativo foi identificado. Todos os arquivos .py encontrados nas pastas analisadas têm uma função clara:

- **Importados por src/:** `adapters/`, `infra/`, `data/`, `security/`, `helpers/` (raiz - bridge)
- **Scripts CLI:** `devtools/`, `scripts/`
- **Configuração:** `sitecustomize.py`
- **Entry point:** `main.py`

**Observação:** Os arquivos em `devtools/qa/` e `devtools/arch/` não são importados, mas são ferramentas de análise executadas manualmente, não são código morto.

---

## Estatísticas de Imports

### Imports de src/ para módulos externos:

| Módulo externo | Quantidade de imports em src/ |
|----------------|-------------------------------|
| `infra.*` | 33 imports (múltiplos arquivos) |
| `adapters.storage.*` | 13 imports |
| `data.*` | 6 imports |
| `security.crypto` | 1 import |
| `helpers.*` (raiz) | 3 imports (apenas auditoria) |

### Imports de tests/ para módulos externos:

| Módulo externo | Quantidade de imports em tests/ |
|----------------|----------------------------------|
| `infra.archive_utils` | 2 imports |
| `infra.repositories.passwords_repository` | 1 import |

### Imports cruzados (entre módulos externos):

- `data/supabase_repo.py` → `infra.supabase_client`, `security.crypto`, `data.domain_types`
- `infra/repositories/passwords_repository.py` → `data.domain_types`
- `src/helpers/auth_utils.py` → `infra.supabase_client` (tecnicamente dentro de src/, mas helper usa infra)

---

## Recomendações de Coverage Futuro

### Opção A: Expandir coverage para incluir código de APP_CORE_CANDIDATE

**Comando sugerido:**
```bash
python -m pytest \
  --cov=src \
  --cov=adapters \
  --cov=infra \
  --cov=data \
  --cov=security \
  --cov-report=term-missing \
  --cov-fail-under=XX \
  -q
```

**Meta de coverage:**
- Considerar ajustar `--cov-fail-under` conforme necessário (calcular nova baseline).
- Atualmente `src/` está em ~37%. Com a adição de `adapters/`, `infra/`, `data/` e `security/`, a baseline inicial pode cair (mais código, mesmos testes).

**Justificativa:**
- `adapters/`, `infra/`, `data/` e `security/` são código de produto, importados extensivamente por `src/`.
- Testar esses módulos aumenta a confiança na qualidade do código core.

---

### Opção B: Consolidar tudo em src/ (Refatoração CODE-001)

**Estrutura futura sugerida:**
```
src/
├── adapters/        # movido de raiz
├── core/            # já existe
├── data/            # movido de raiz
├── features/        # já existe
├── helpers/         # já existe (remover bridge na raiz)
├── infrastructure/  # já existe (pode absorver infra/)
│   └── supabase/
│       ├── client.py      # ex-infra/supabase_client.py
│       ├── auth.py        # ex-infra/supabase_auth.py
│       ├── archive_utils.py
│       └── ...
├── modules/         # já existe
├── security/        # movido de raiz
├── shared/          # já existe
├── ui/              # já existe
└── utils/           # já existe
```

**Vantagens:**
- Único ponto de configuração de coverage: `--cov=src`
- Organização mais clara (tudo relacionado ao produto em um só lugar)
- Elimina imports de nível raiz (exceto `main.py`)

**Desvantagens:**
- Requer refatoração significativa de imports
- Pode quebrar testes/scripts que assumem estrutura atual
- Precisa de validação cuidadosa (possível tarefa multi-fases)

---

### Opção C: Manter separação, coverage seletivo

**Coverage de produto (obrigatório):**
```bash
--cov=src --cov=adapters --cov=infra --cov=data --cov=security
```

**Coverage de infra/devtools (opcional, CI separado):**
```bash
--cov=devtools --cov=scripts
```

**Justificativa:**
- Mantém flexibilidade
- Permite coverage diferenciado para código de produto vs ferramentas
- Menos impacto de refatoração

---

## Pastas Sugeridas para Exclusão de Coverage Oficial

- **devtools/**: Ferramentas de QA/análise internas
- **scripts/**: Scripts de teste manual e demos
- **helpers/** (raiz): Bridge de compatibilidade temporário (remover após migração)
- **Arquivos raiz**: `main.py`, `sitecustomize.py`

**Observação:** Essas pastas podem ter coverage opcional em workflows de CI separados, se desejado.

---

## Próximos Passos

1. **Revisar este relatório** com a equipe para decidir a estratégia de coverage:
   - Opção A: Expandir coverage atual
   - Opção B: Refatorar para consolidar em `src/`
   - Opção C: Coverage seletivo por categoria

2. **Calcular nova baseline de coverage** se optar pela Opção A ou C:
   - Rodar `pytest --cov=src --cov=adapters --cov=infra --cov=data --cov=security` e verificar percentual atual
   - Definir meta realista (pode iniciar abaixo de 37% e aumentar gradualmente)

3. **Criar tarefa de migração de imports** se optar pela Opção B:
   - Mapear todos os imports que precisam ser atualizados
   - Criar script de refatoração automática (se possível)
   - Executar em fases (por módulo)

4. **Atualizar pytest.ini** conforme decisão:
   - Adicionar `--cov` flags
   - Ajustar `--cov-fail-under`
   - Documentar em `CONTRIBUTING.md`

5. **Remover bridge `helpers/`** após migrar os 3 imports em `auditoria/`:
   - Atualizar imports para `src.helpers.formatters`
   - Deletar `helpers/__init__.py` da raiz
   - Validar com testes

---

## Conclusão

O código Python fora de `src/` está bem organizado e serve propósitos claros:

- **APP_CORE_CANDIDATE** (~29 arquivos): `adapters/`, `infra/`, `data/`, `security/` → devem entrar na meta de coverage
- **INFRA_DEVTOOLS** (~11 arquivos): `devtools/` → opcional para coverage
- **SCRIPTS_ISOLADOS** (~11 arquivos): `scripts/` → opcional para coverage
- **BRIDGE/LEGACY** (1 arquivo): `helpers/` raiz → remover após migração

A análise identificou uso extensivo e legítimo de módulos externos por `src/`, confirmando que `adapters/`, `infra/`, `data/` e `security/` são parte integral da aplicação e merecem cobertura de testes adequada.

**Nenhuma configuração foi alterada nesta tarefa.** Este documento serve como base para decisões futuras sobre estratégia de coverage e possíveis refatorações arquiteturais.
