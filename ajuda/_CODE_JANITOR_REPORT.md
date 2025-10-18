# 🧹 Code Janitor Report - RC-Gestor v1.0.37

**Data da Análise:** 18 de outubro de 2025  
**Modo:** Dry-run (sem alterações aplicadas)  
**Projeto:** Python Desktop App (Tkinter + Supabase)

---

## 📊 Executive Summary

- **Total de itens analisados:** 28 pastas/arquivos principais
- **Marcados como KEEP:** 20 itens
- **Marcados como UNUSED?:** 8 itens
- **Total de espaço a liberar:** ~50+ arquivos em `ajuda/`, `build/`, scripts de desenvolvimento

---

## 📋 Tabela de Análise Detalhada

| Item | Status | Evidência | Motivo |
|------|--------|-----------|--------|
| **`app_gui.py`** | **KEEP** | Entry point principal (`if __name__ == "__main__"`), referenciado em `rcgestor.spec` | Entry point do aplicativo |
| **`app_core.py`** | **KEEP** | Importado por `gui/main_window.py`, contém funções de CRUD | Lógica de negócio core |
| **`app_status.py`** | **KEEP** | Importado por `app_gui.py` (linha 12), usado para status de rede | Monitor de status de conexão |
| **`app_utils.py`** | **KEEP** | Importado por `app_core.py` (linha 20), funções utilitárias | Helpers compartilhados |
| **`config.yml`** | **KEEP** | Lido por `app_status.py` (linha 21), configuração de probe | Configuração runtime |
| **`rc.ico`** | **KEEP** | Referenciado em `rcgestor.spec`, usado em múltiplos arquivos UI via `resource_path("rc.ico")` | Ícone da aplicação |
| **`rcgestor.spec`** | **KEEP** | Arquivo de build do PyInstaller | Build configuration |
| **`pyproject.toml`** | **KEEP** | Configuração do projeto (Ruff, Mypy, Deptry, Vulture) | Project config |
| **`requirements.txt`** | **KEEP** | Dependências do projeto | Dependencies |
| **`requirements-min.txt`** | **KEEP** | Dependências mínimas | Dependencies (minimal) |
| **`requirements.in`** | **KEEP** | Source para pip-compile | Dependencies source |
| **`requirements-min.in`** | **KEEP** | Source para pip-compile (minimal) | Dependencies source |
| **`pytest.ini`** | **KEEP** | Configuração de testes | Test configuration |
| **`README.md`** | **KEEP** | Documentação principal do projeto | Project documentation |
| **`sign_rcgestor.ps1`** | **KEEP** | Script de assinatura de código | Build script |
| **`.env`** *(se existir)* | **KEEP** | Variáveis de ambiente (runtime) | Environment config |
| **`.gitignore`** | **KEEP** | Git configuration | VCS |
| **`.gitattributes`** | **KEEP** | Git configuration | VCS |
| **`.editorconfig`** | **KEEP** | Editor configuration | Dev tools |
| **`adapters/`** | **KEEP** | Importado por `ui/forms/actions.py`, `core/services/*`, `application/api.py` | Storage abstraction layer |
| **`application/`** | **KEEP** | Importado por `gui/main_window.py` (controllers, commands, keybindings) | Application layer |
| **`config/`** | **KEEP** | Importado em múltiplos módulos (`config.paths`, `config.constants`) | Configuration module |
| **`core/`** | **KEEP** | Importado extensivamente (db_manager, auth, services, session, search) | Core business logic |
| **`gui/`** | **KEEP** | Importado por `app_gui.py`, contém UI principal | GUI layer |
| **`infra/`** | **KEEP** | Importado por 26 arquivos (supabase_client, net_status, healthcheck) | Infrastructure layer |
| **`shared/`** | **KEEP** | Importado por `app_gui.py`, `infra/`, `config/` (logging, environment) | Shared utilities |
| **`ui/`** | **KEEP** | Importado por 26 arquivos (forms, dialogs, widgets, login) | UI components |
| **`utils/`** | **KEEP** | Importado por 42 arquivos (resource_path, validators, themes, file_utils) | Utility functions |
| **`runtime_docs/`** | **KEEP** | `CHANGELOG.md` referenciado em `rcgestor.spec` e `gui/main_window.py:629` | Runtime documentation |
| **`__pycache__/`** *(múltiplos)* | **UNUSED?** | Caches de bytecode Python | Cache temporário (regenerável) |
| **`.ruff_cache/`** | **UNUSED?** | Cache do linter Ruff | Cache temporário |
| **`.import_linter_cache/`** | **UNUSED?** | Cache do import-linter | Cache temporário |
| **`build/`** | **UNUSED?** | Artefatos de build do PyInstaller | Build artifacts (regenerável) |
| **`dist/`** *(se existir)* | **UNUSED?** | Binários compilados | Build output (regenerável) |
| **`ajuda/`** | **UNUSED?** | Documentação de desenvolvimento, relatórios, ferramentas | Dev docs (não usado em runtime) |
| **`scripts/`** | **UNUSED?** | Scripts de desenvolvimento (`audit_consolidation.py`, `convert_utf16_to_utf8.py`, etc.) | Dev scripts (não usado em runtime) |
| **`detectors/`** | **UNUSED?** | Pasta vazia (apenas `__init__.py` e `__pycache__`) | Empty module |
| **`infrastructure/`** | **UNUSED?** | Wrapper legacy que apenas faz `from infra import *` | Legacy alias (redundante) |
| **`RELATORIO_*.md`** | **UNUSED?** | Relatórios de build/análise (não referenciados em código) | Dev documentation |
| **`EXCLUSOES_SUGERIDAS.md`** | **UNUSED?** | Documentação de desenvolvimento | Dev documentation |
| **`PYINSTALLER_BUILD.md`** | **UNUSED?** | Documentação de build | Dev documentation |

---

## 🗑️ Candidatos à Remoção (Detalhado)

### Caches (seguros para limpar)
```
__pycache__/                          # Raiz
adapters/__pycache__/
adapters/storage/__pycache__/
application/__pycache__/
config/__pycache__/
core/__pycache__/
core/auth/__pycache__/
core/db_manager/__pycache__/
core/logs/__pycache__/
core/search/__pycache__/
core/services/__pycache__/
core/session/__pycache__/
detectors/__pycache__/
gui/__pycache__/
infra/__pycache__/
infra/db/__pycache__/
infrastructure/__pycache__/
infrastructure/scripts/__pycache__/
scripts/__pycache__/
shared/__pycache__/
shared/config/__pycache__/
shared/logging/__pycache__/
ui/__pycache__/
ui/dialogs/__pycache__/
ui/forms/__pycache__/
ui/login/__pycache__/
ui/lixeira/__pycache__/
ui/subpastas/__pycache__/
ui/widgets/__pycache__/
utils/__pycache__/
utils/file_utils/__pycache__/
utils/helpers/__pycache__/
.ruff_cache/
.import_linter_cache/
```

### Build Artifacts (regeneráveis via PyInstaller)
```
build/
dist/                                 # Se existir
```

### Documentação de Desenvolvimento (não usada em runtime)
```
ajuda/
RELATORIO_BUILD_PYINSTALLER.md
RELATORIO_ONEFILE.md
EXCLUSOES_SUGERIDAS.md
PYINSTALLER_BUILD.md
```

### Scripts de Desenvolvimento (não usados em runtime)
```
scripts/audit_consolidation.py
scripts/convert_utf16_to_utf8.py
scripts/generate_tree.py
scripts/make_runtime.py
scripts/quarantine_orphans.py
scripts/regenerate_inventario.ps1
scripts/remove_bom.py
scripts/smoke_runtime.py
scripts/__pycache__/
```

### Módulos Vazios/Redundantes
```
detectors/                            # Apenas __init__.py vazio
infrastructure/                       # Legacy wrapper para infra/
```

---

## 🎯 Recomendações

### ✅ Seguros para Remover
1. **Todos os `__pycache__/`** - Regenerados automaticamente pelo Python
2. **`.ruff_cache/`** - Regenerado automaticamente pelo Ruff
3. **`build/`** - Regenerado pelo PyInstaller quando necessário
4. **`dist/`** - Saída do build, regenerável

### ⚠️ Verificar com Usuário
1. **`ajuda/`** - Contém documentação valiosa de desenvolvimento. Sugestão: mover para um repo separado de docs ou manter backup externo
2. **`scripts/`** - Scripts úteis de manutenção. Podem ser necessários ocasionalmente
3. **`detectors/`** - Pode ser parte de feature futura. Verificar se é resíduo
4. **`infrastructure/`** - Wrapper legacy. Pode ter sido usado antes, verificar histórico git

### 🔒 NUNCA Remover (Whitelist)
- `config/`, `assets/` (se houver), `ui/`, `core/`, `gui/`, `utils/`, `shared/`, `application/`, `infra/`, `adapters/`
- `config.yml`, `pyproject.toml`, `requirements*.txt`, `rcgestor.spec`, `rc.ico`
- `app_*.py`, `README.md`, `.env*`, `.git*`

---

## 📦 Tamanho Estimado

| Categoria | Arquivos | Tamanho Estimado |
|-----------|----------|------------------|
| `__pycache__/` (todos) | ~30 pastas | ~5-10 MB |
| `build/` | 1 pasta | ~50-200 MB |
| `ajuda/` | ~40 arquivos | ~2-5 MB |
| `scripts/` | ~8 arquivos | ~100 KB |
| `detectors/` | 1 arquivo | ~1 KB |
| `infrastructure/` | 2 arquivos | ~2 KB |
| **TOTAL** | **~80 itens** | **~60-220 MB** |

---

## ⚙️ Próximos Passos

1. **Revisar este relatório** e confirmar itens para remoção
2. **Executar comandos de dry-run** (fornecidos abaixo)
3. **Validar** com `python -m compileall .`
4. **Smoke test** executando `python app_gui.py`
5. **Commit** das mudanças se tudo funcionar

---

## 🔍 Notas Técnicas

### Entry Points Detectados
- `app_gui.py` - Principal (GUI)
- `app_core.py` - Lógica de negócio
- `app_status.py` - Monitor de rede
- `app_utils.py` - Utilitários

### Dependências Críticas de Runtime
- `runtime_docs/CHANGELOG.md` - Carregado em `gui/main_window.py`
- `rc.ico` - Ícone usado em todas as janelas
- `config.yml` - Configuração de network probe
- `.env` - Variáveis de ambiente (se existir)

### Padrões de Import Encontrados
- `from adapters.storage.*` (3 locais)
- `from shared.logging.*` (2 locais)
- `from shared.config.*` (4 locais)
- `from utils.resource_path import resource_path` (10+ locais)
- `from config.paths import *` (13 locais)
- `from infra.*` (26 locais)
- `from core.*` (33 locais)
- `from gui.*` (7 locais)
- `from ui.*` (26 locais)
- `from utils.*` (42 locais)
- `from application.*` (15 locais)

### Assets Runtime
- **Ícone:** `rc.ico` (usado via `resource_path()`)
- **Docs:** `runtime_docs/CHANGELOG.md`
- **Pasta assets/:** Vazia (não usada atualmente)

---

**Gerado por:** Code Janitor AI  
**Timestamp:** 2025-10-18 (Dry-run)
