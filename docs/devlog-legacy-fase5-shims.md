# Devlog: FASE 5 – Limpeza de Legados e Shims de Compatibilidade

**Data:** 2025-01-28  
**Branch:** qa/fixpack-04

## Objetivo

Limpeza de shims de compatibilidade em `src/ui/` que apenas reexportam de `src/modules/`. A estratégia foi **marcar como DEPRECATED** ao invés de remover, garantindo compatibilidade com scripts externos.

## Shims Identificados e Marcados como DEPRECATED

### Nível Raiz (`src/ui/`)

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `hub_screen.py` | `src.modules.hub.views.hub_screen` | ✅ DEPRECATED |
| `main_screen.py` | `src.modules.clientes.views.main_screen` | ✅ DEPRECATED |
| `passwords_screen.py` | `src.modules.passwords.views.passwords_screen` | ✅ DEPRECATED |

### Pacote `src/ui/hub/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `__init__.py` | `src.modules.hub` | ✅ DEPRECATED |
| `actions.py` | `src.modules.hub.actions` | ✅ DEPRECATED |
| `actions_filter.py` | `src.modules.hub.actions_filter` | ✅ DEPRECATED |
| `actions_notes.py` | `src.modules.hub.actions_notes` | ✅ DEPRECATED |
| `authors.py` | `src.modules.hub.authors` | ✅ DEPRECATED |
| `config.py` | `src.modules.hub.config` | ✅ DEPRECATED |
| `hub_screen.py` | `src.modules.hub.views.hub_screen` | ✅ DEPRECATED |
| `notecell.py` | `src.modules.hub.notecell` | ✅ DEPRECATED |
| `notes_service.py` | `src.modules.hub.notes_service` | ✅ DEPRECATED |
| `search_state.py` | `src.modules.hub.search_state` | ✅ DEPRECATED |
| `views.py` | `src.modules.hub.views` | ✅ DEPRECATED |

### Pacote `src/ui/lixeira/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `__init__.py` | `src.modules.lixeira.views.lixeira` | ✅ DEPRECATED |
| `lixeira.py` | `src.modules.lixeira.views.lixeira` | ✅ DEPRECATED |

### Pacote `src/ui/main_window/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `__init__.py` | (vários) | ✅ DEPRECATED |
| `app.py` | `src.modules.main_window.views.main_window` | ✅ DEPRECATED |
| `frame_factory.py` | `src.modules.main_window.controller` | ✅ DEPRECATED |
| `router.py` | `src.modules.main_window.controller` | ✅ DEPRECATED |
| `tk_report.py` | `src.modules.main_window.controller` | ✅ DEPRECATED |

### Pacote `src/ui/forms/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `forms.py` | `src.modules.clientes.forms` | ✅ DEPRECATED |
| `pipeline.py` | `src.modules.clientes.forms._pipeline` | ✅ DEPRECATED |

### Pacote `src/ui/widgets/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `client_picker.py` | `src.modules.clientes.forms` | ✅ DEPRECATED |

### Pacote `src/ui/subpastas/`

| Arquivo | Reexporta de | Status |
|---------|--------------|--------|
| `dialog.py` | `src.modules.clientes.forms` | ✅ DEPRECATED |

## Migrações de Imports Internos

Antes de deprecar, migramos os imports internos que usavam os shims:

| Arquivo | Import Antigo | Import Novo |
|---------|---------------|-------------|
| `src/modules/lixeira/views/lixeira.py` | `src.ui.hub.authors` | `src.modules.hub.authors` |
| `src/modules/clientes/views/main_screen.py` | `src.ui.hub.authors` | `src.modules.hub.authors` |
| `src/app_core.py` | `src.ui.subpastas` | `src.modules.clientes.forms` |
| `src/app_core.py` | `src.ui.lixeira` | `src.modules.lixeira.views.lixeira` |
| `src/modules/main_window/app_actions.py` | `src.ui.lixeira` | `src.modules.lixeira.views.lixeira` |
| `src/app_gui.py` | `src.ui.main_window` | `src.modules.main_window.views.main_window` |

## Padrão de Deprecação

Todos os shims agora incluem:

```python
"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.X import Y
"""

import warnings

warnings.warn(
    "src.ui.X está deprecated. Use src.modules.X",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.X import Y  # noqa: E402
```

## QA Executado

- [x] `ruff check src/ui --select=E,F,W` → 6 erros E501 (linhas longas, não relacionados aos shims)
- [x] `pyright src/ui/...shims...` → 0 erros
- [x] Import test → OK (emite DeprecationWarning como esperado)

## Próximos Passos

1. **Versão futura:** Remover os shims completamente após período de depreciação
2. **Documentação:** Atualizar CONTRIBUTING.md com guia de imports canônicos
3. **CI:** Considerar adicionar check que falha se imports deprecated forem usados internamente

## Arquivos Alterados

```
src/ui/hub_screen.py
src/ui/main_screen.py
src/ui/passwords_screen.py
src/ui/hub/__init__.py
src/ui/hub/actions.py
src/ui/hub/actions_filter.py
src/ui/hub/actions_notes.py
src/ui/hub/authors.py
src/ui/hub/config.py
src/ui/hub/hub_screen.py
src/ui/hub/notecell.py
src/ui/hub/notes_service.py
src/ui/hub/search_state.py
src/ui/hub/views.py
src/ui/lixeira/__init__.py
src/ui/lixeira/lixeira.py
src/ui/main_window/__init__.py
src/ui/main_window/app.py
src/ui/main_window/frame_factory.py
src/ui/main_window/router.py
src/ui/main_window/tk_report.py
src/ui/forms/forms.py
src/ui/forms/pipeline.py
src/ui/widgets/client_picker.py
src/ui/subpastas/dialog.py
src/modules/lixeira/views/lixeira.py
src/modules/clientes/views/main_screen.py
src/app_core.py
src/modules/main_window/app_actions.py
src/app_gui.py
src/ui/window_utils.py (whitespace fixes)
src/ui/pdf_preview_native.py (unused import fix)
```
