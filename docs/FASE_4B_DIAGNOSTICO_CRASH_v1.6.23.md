# Fase 4B — Diagnóstico e Correção do Crash Real do EXE v1.6.23

**Data**: 2026-03-19  
**Escopo**: Diagnosticar e corrigir o `ModuleNotFoundError` real do EXE empacotado.  
**Regra**: Correção mínima sem refatoração, sem tocar lógica de negócio.

---

## 1. Resumo Executivo

| Item | Detalhe |
|------|---------|
| **Causa real** | `src/modules/hub/dashboard_service.py` (shim DEPRECATED) usava `importlib.import_module("src.modules.hub.dashboard.service")` via `__getattr__` (PEP 562). O PyInstaller não rastreia imports dinâmicos, então o pacote `src.modules.hub.dashboard/` inteiro não era coletado no bundle. |
| **Tipo** | Import dinâmico não coletado pelo PyInstaller (NÃO é import path quebrado, NÃO é hidden import ausente) |
| **Correção** | Substituídos `__getattr__`/`__dir__` dinâmicos por re-exports estáticos explícitos. 1 arquivo alterado, 0 linhas de lógica de negócio tocadas. |
| **Risco** | Mínimo. O shim já era DEPRECATED e o `__getattr__` era acionado imediatamente (sem benefício de lazy loading real). A API pública é idêntica. |

---

## 2. Evidência do Problema

### Traceback completo capturado do EXE

```
Traceback (most recent call last):
  File "app.py", line 10, in <module>
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\main_window\__init__.py", line 1, in <module>
    from src.modules.main_window.controller import create_frame, navigate_to, tk_report
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\main_window\controller.py", line 8, in <module>
    from src.modules.notas import HubFrame
  File "src\modules\notas\__init__.py", line 19, in __getattr__
    from .view import HubFrame as _HubFrame
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\notas\view.py", line 12, in <module>
    from src.modules.hub.views.hub_screen import HubScreen
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\hub\__init__.py", line 11, in <module>
    from .views import HubScreen
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\hub\views\__init__.py", line 7, in <module>
    from .hub_screen import HubScreen
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\hub\views\hub_screen.py", line 44, in <module>
    from src.modules.hub.viewmodels import DashboardViewState
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\hub\viewmodels\__init__.py", line 18, in <module>
    from src.modules.hub.viewmodels.dashboard_vm import (...)
  File "pyimod02_importers.py", line 457, in exec_module
  File "src\modules\hub\viewmodels\dashboard_vm.py", line 15, in <module>
    from src.modules.hub.dashboard_service import DashboardSnapshot, get_dashboard_snapshot
  File "src\modules\hub\dashboard_service.py", line 22, in __getattr__
    mod = importlib.import_module("src.modules.hub.dashboard.service")
  File "importlib\__init__.py", line 88, in import_module
ModuleNotFoundError: No module named 'src.modules.hub.dashboard'
```

### Cadeia de imports que leva ao crash

```
app.py
  → src.modules.main_window.__init__
    → src.modules.main_window.controller
      → src.modules.notas (HubFrame via __getattr__)
        → src.modules.notas.view
          → src.modules.hub.views.hub_screen
            → src.modules.hub.viewmodels
              → src.modules.hub.viewmodels.dashboard_vm
                → src.modules.hub.dashboard_service  ← SHIM
                  → importlib.import_module("src.modules.hub.dashboard.service")  ← CRASH
```

### Ponto exato da quebra

- **Arquivo**: `src/modules/hub/dashboard_service.py`, função `__getattr__`, linha 22
- **Operação**: `importlib.import_module("src.modules.hub.dashboard.service")`
- **Motivo**: O pacote `src.modules.hub.dashboard/` não foi coletado pelo PyInstaller

---

## 3. Diagnóstico Técnico

### O módulo existe no source?

**SIM.** O pacote `src/modules/hub/dashboard/` contém 4 arquivos:

| Arquivo | Propósito |
|---------|-----------|
| `__init__.py` | Re-exports de `service.py` (imports estáticos) |
| `service.py` | Implementação real do dashboard service |
| `models.py` | `DashboardSnapshot` dataclass |
| `data_access.py` | Funções de acesso a dados |

### Import path correto ou stale?

**O path está correto.** O import `src.modules.hub.dashboard.service` resolve corretamente no Python normal:

```
>>> from src.modules.hub.dashboard.service import DashboardSnapshot
>>> # OK
>>> from src.modules.hub.dashboard_service import DashboardSnapshot
>>> # OK (via shim __getattr__)
```

### Hidden import ausente ou não?

**NÃO é um problema de hidden import.** O módulo existe e importa normalmente. O problema é que `dashboard_service.py` usava `importlib.import_module()` (import dinâmico) que é **invisível para a análise estática do PyInstaller**. O analisador nunca vê a string `"src.modules.hub.dashboard.service"` como dependência.

### Decisão técnica final

| Opção | Avaliação |
|-------|-----------|
| Adicionar `hiddenimports` no spec | ❌ Mascara o problema. O import dinâmico continua frágil. |
| Corrigir o shim para import estático | ✅ Resolve a causa raiz. PyInstaller rastreia naturalmente. |
| Criar hook PyInstaller | ❌ Overengineering para um shim de 1 arquivo. |

**Decisão**: Substituir `importlib.import_module` por re-exports estáticos no shim.

---

## 4. Diff Aplicado

**1 arquivo alterado**: `src/modules/hub/dashboard_service.py`

```diff
 from __future__ import annotations

-import importlib
-from typing import Any
-
-# __all__ definido no módulo real (src.modules.hub.dashboard.service)
-# Aqui usamos __getattr__ para lazy loading (PEP 562)
-
-
-def __getattr__(name: str) -> Any:
-    """Lazy import from src.modules.hub.dashboard.service."""
-    mod = importlib.import_module("src.modules.hub.dashboard.service")
-    return getattr(mod, name)
-
-
-def __dir__() -> list[str]:
-    """List available attributes from the real module."""
-    mod = importlib.import_module("src.modules.hub.dashboard.service")
-    return sorted(set(dir(mod)))
+# Re-exports estáticos do módulo real (substitui importlib.import_module
+# dinâmico que era invisível ao PyInstaller — causa do crash no EXE).
+from src.modules.hub.dashboard.service import (  # noqa: F401
+    DashboardSnapshot,
+    _due_badge,
+    _format_due_br,
+    _get_first_day_of_month,
+    _get_last_day_of_month,
+    _parse_due_date_iso,
+    _parse_timestamp,
+    due_badge,
+    format_due_br,
+    get_dashboard_snapshot,
+    get_first_day_of_month,
+    get_last_day_of_month,
+    parse_due_date_iso,
+    parse_timestamp,
+)
```

### O que NÃO foi alterado

- `rcgestor.spec` — nenhum `hiddenimports` adicionado
- Nenhum outro arquivo fonte
- Nenhuma lógica de negócio
- Nenhum hook PyInstaller criado
- `.env` não tocado

---

## 5. Resultado do Rebuild

| Item | Resultado |
|------|-----------|
| Build | ✅ `Building EXE from EXE-00.toc completed successfully.` |
| Artefato | `dist/RC-Gestor-Clientes-1.6.23.exe` |
| `hiddenimports` alterados | Nenhum (spec inalterado) |
| Warnings críticos | 0 (mesmos 48 módulos opcionais de antes) |

O PyInstaller agora rastreia a cadeia estática:
`dashboard_service.py` → `dashboard/service.py` → `dashboard/models.py` + `dashboard_formatters.py`

---

## 6. Resultado do Smoke Real

### Smoke test do EXE rebuildado (30 segundos)

| Critério | Resultado |
|----------|-----------|
| Processo vivo após 30s | ✅ `ALIVE after 30s` |
| `ModuleNotFoundError` | ✅ **ZERO** — ponto que antes crashava foi atravessado |
| Startup completo | ✅ Logging, CTk, layout, ícone, topbar, footer |
| Splash | ✅ Fechou após 5.2s |
| Autenticação | ✅ Sessão detectada e ativa |
| Janela principal | ✅ Maximizada e visível (alpha=1.0) |
| Health check | ✅ Internet OK |
| Stderr | Logs INFO normais, 0 tracebacks |

### Stderr completo capturado (logs do app)

```
2026-03-19 14:56:48 | INFO | startup | Logging level ativo: INFO
2026-03-19 14:56:48 | INFO | startup | Timezone local detectado: America/Sao_Paulo
2026-03-19 14:56:49 | INFO | theme_manager | CustomTkinter: mode=light, color=blue
2026-03-19 14:56:49 | INFO | app_gui | Janela inicializada com CTk
2026-03-19 14:56:49 | INFO | app_gui.layout | Ícone aplicado: rc.ico
2026-03-19 14:56:49 | INFO | app_gui.layout | Layout skeleton criado
2026-03-19 14:56:49 | INFO | app_gui | Bootstrap do MainWindow concluído
2026-03-19 14:56:49 | WARNING | topbar_nav | Ícone do Sites não encontrado: sites.png
2026-03-19 14:56:49 | WARNING | topbar_nav | Ícone do ChatGPT não encontrado: chatgpt.png
2026-03-19 14:56:49 | INFO | app_gui.layout | TopBar criado
2026-03-19 14:56:49 | INFO | app_gui.layout | StatusFooter criado
2026-03-19 14:56:54 | INFO | splash | Splash fechado após 5.2s
2026-03-19 14:56:54 | INFO | auth | Sessão ativa: uid=44900b9f...
2026-03-19 14:56:54 | INFO | app_gui | Janela maximizada após login
2026-03-19 14:56:55 | INFO | startup | Alpha restaurado para 1.0
2026-03-19 14:56:55 | INFO | startup | Background health check: Internet OK
```

### Warnings cosméticos (não-bloqueantes)

| Warning | Causa | É bug de empacotamento? |
|---------|-------|------------------------|
| `sites.png` não encontrado | Arquivo nunca existiu no source `assets/` | ❌ Ausência no source |
| `chatgpt.png` não encontrado | Arquivo nunca existiu no source `assets/` | ❌ Ausência no source |

---

## 7. Validação Final

### Import smoke no source

```
$ python -c "from src.modules.hub.dashboard_service import DashboardSnapshot; print('OK')"
→ shim OK: DashboardSnapshot

$ python -c "import src.core.app; print('OK')"
→ app import OK
```

### pytest

```
1035 passed in 36.10s
```

### EXE rebuildado

```
Build: ✅ completed successfully
Smoke: ✅ ALIVE 30s, zero crashes, login completo, janela visível
```

### Classificação final

**✅ CORRIGIDO NO SOURCE E NO EXE**

| Aspecto | Status |
|---------|--------|
| Import funciona no Python normal | ✅ (já funcionava antes) |
| Import funciona no EXE empacotado | ✅ (CORRIGIDO — antes crashava) |
| Tests passando | ✅ 1035/1035 |
| Spec inalterado | ✅ Nenhum hiddenimport adicionado |
| Correção mínima | ✅ 1 arquivo, 0 lógica de negócio |

---

## Retificação da Fase 4A

A aprovação da Fase 4A foi revisada. O smoke test de 12–15 segundos era insuficiente:
- O app abria a janela Tk e mostrava o splash (5s de animação)
- O crash ocorria mais adiante, ao importar a cadeia hub → dashboard
- O processo "vivo por 12s" incluía apenas splash + inicialização parcial
- O `ModuleNotFoundError` acontecia quando o app tentava navegar para o HUB

A Fase 4B corrigiu a causa raiz e provou que o EXE agora passa do ponto que antes explodia.
