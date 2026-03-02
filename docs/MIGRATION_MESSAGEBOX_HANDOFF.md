# Handoff — Migração `tkinter.messagebox` → `rc_dialogs`

**Data:** 25/02/2026  
**Versão:** v1.5.87  
**Status:** ~95% concluída  
**Testes:** 453 passed (zero falhas)

---

## 1. O que foi feito

### 1.1 Expansão do `rc_dialogs.py`

Arquivo: `src/ui/dialogs/rc_dialogs.py` (~464 linhas)

Adicionadas **3 novas funções** ao sistema de diálogos CTk:

| Função | Equivalente nativo | Retorno | Detalhes visuais |
|---|---|---|---|
| `show_warning(parent, title, message)` | `messagebox.showwarning` | `None` | Botão OK âmbar `("#d97706", "#f59e0b")`, ícone warning |
| `ask_ok_cancel(parent, title, message)` | `messagebox.askokcancel` | `bool` | OK azul + Cancelar cinza, ícone warning |
| `ask_retry_cancel(parent, title, message)` | `messagebox.askretrycancel` | `bool` | "Tentar novamente" azul (wider: `BTN_W+30`) + Cancelar cinza |

Já existiam: `ask_yes_no`, `show_info`, `show_error`.

**API completa atual (6 funções):**
```python
ask_yes_no(parent, title, message)      → bool
ask_ok_cancel(parent, title, message)   → bool
ask_retry_cancel(parent, title, message)→ bool
show_info(parent, title, message)       → None
show_warning(parent, title, message)    → None
show_error(parent, title, message)      → None
```

Todas usam: `alpha=0` → reveal em 220ms, `_center_on_parent`, ícone do app via `apply_window_icon`, temas dark/light via `APP_BG`.

### 1.2 Arquivos migrados (25 arquivos fonte)

| # | Arquivo | Chamadas migradas | Tipos |
|---|---|---|---|
| 1 | `src/ui/feedback.py` | 4 | showerror, showwarning, showinfo, askokcancel |
| 2 | `src/modules/clientes/ui/views/client_editor_dialog.py` | 14 | showerror, showwarning, showinfo, askyesno |
| 3 | `src/modules/clientes/ui/views/client_files_dialog.py` | 14 | showerror, showwarning, showinfo |
| 4 | `src/modules/clientes/ui/view.py` | 10 | showerror, showwarning, showinfo |
| 5 | `src/modules/clientes/forms/_dupes.py` | 2 | showwarning, askokcancel |
| 6 | `src/modules/clientes/core/viewmodel.py` | 6 | showwarning, showinfo, showerror |
| 7 | `src/modules/main_window/app_actions.py` | 18 | showerror, showwarning, showinfo, askyesno |
| 8 | `src/modules/main_window/views/main_window_actions.py` | 6 | showwarning, showerror, askyesno, showinfo |
| 9 | `src/modules/main_window/views/main_window.py` | 1 | showerror |
| 10 | `src/modules/main_window/controller.py` | 1 | showwarning |
| 11 | `src/modules/uploads/views/browser.py` | 27 | showinfo, showerror, askyesno |
| 12 | `src/modules/uploads/uploader_supabase.py` | 11 | showinfo, showwarning, showerror, askyesno |
| 13 | `src/modules/uploads/views/upload_dialog.py` | 1 | showerror |
| 14 | `src/modules/hub/views/hub_dashboard_callbacks.py` | 9 | showwarning, showerror, showinfo |
| 15 | `src/modules/hub/views/hub_dialogs.py` | 1 | showwarning |
| 16 | `src/modules/hub/views/notes_text_interactions.py` | 1 | showinfo (parent=None) |
| 17 | `src/modules/hub/helpers/debug.py` | 2 | showinfo, showerror |
| 18 | `src/modules/hub/controller.py` | 2 | showwarning |
| 19 | `src/modules/forms/actions_impl.py` | 4 | showwarning, showerror |
| 20 | `src/modules/tasks/views/task_dialog.py` | 3 | showerror |
| 21 | `src/modules/cashflow/views/fluxo_caixa_frame.py` | 7 | showwarning, showerror, showinfo, askyesno |
| 22 | `src/features/cashflow/ui.py` | 8 | showerror, showwarning, showinfo, askyesno |
| 23 | `src/features/cashflow/dialogs.py` | 1 | showerror |
| 24 | `src/modules/pdf_preview/views/pdf_viewer_actions.py` | 5 | showwarning, showinfo, showerror |
| 25 | `src/ui/components/notifications/notifications_popup.py` | 11 | showinfo, showerror, showwarning, askyesno |
| 26 | `src/ui/users/users.py` | 8 | showwarning, askyesno, showerror |
| 27 | `src/ui/subpastas_dialog.py` | 1 | showerror |
| 28 | `src/ui/menu_bar.py` | 1 | showinfo |
| 29 | `src/ui/login_dialog.py` | 3 | showerror |
| 30 | `src/core/services/lixeira_service.py` | 2 | showerror |
| 31 | `src/utils/storage_ui_bridge.py` | 5 | showwarning |

**Total: ~140 chamadas migradas.**

### 1.3 Padrão de transformação aplicado

```python
# ANTES
from tkinter import messagebox
messagebox.showerror("Título", "Mensagem", parent=self)
messagebox.askyesno("Título", "Mensagem", parent=self._app)

# DEPOIS
from src.ui.dialogs.rc_dialogs import show_error, ask_yes_no
show_error(self, "Título", "Mensagem")
ask_yes_no(self._app, "Título", "Mensagem")
```

Regra: `parent` sai de keyword arg para primeiro positional arg.

---

## 2. O que FALTA (pendências reais)

### 2.1 `src/modules/lixeira/views/lixeira.py` — NÃO FOI MIGRADO

**8 chamadas** `tkmsg.*` dentro de wrappers locais (`_info`, `_warn`, `_err`, `_ask_yesno`).

O arquivo usa `from tkinter import messagebox as tkmsg` (alias) e wraps com try/except para fallback sem parent:

```python
def _info(title, msg):
    try:
        tkmsg.showinfo(title, msg, parent=win)
    except Exception:
        tkmsg.showinfo(title, msg)  # fallback sem parent
```

**Para migrar:**
1. Remover `from tkinter import messagebox as tkmsg` (linha 11)
2. Adicionar `from src.ui.dialogs.rc_dialogs import show_info, show_warning, show_error, ask_yes_no`
3. Simplificar os wrappers — `rc_dialogs` já trata `parent=None` internamente, então o try/except não é necessário:
```python
def _info(title: str, msg: str) -> None:
    show_info(win, title, msg)
```
4. Repetir para `_warn` → `show_warning`, `_err` → `show_error`, `_ask_yesno` → `ask_yes_no`

**Risco: BAIXO.** O `win` é uma `CTkToplevel` criada localmente, sempre válida quando os wrappers são chamados.

### 2.2 `src/modules/hub/views/hub_debug_helpers.py` — SHIM DE COMPATIBILIDADE

Linha 15: `from tkinter import messagebox  # noqa: F401`

Este é um **shim deprecated** que re-exporta de `src/modules/hub/helpers/debug.py`. O import de `messagebox` existe apenas para que **testes que patcheiam** `hub_debug_helpers.messagebox` não quebrem.

**Para migrar:**
- Verificar se algum teste faz `patch("src.modules.hub.views.hub_debug_helpers.messagebox")`. Se sim, atualizar o patch target para `src.ui.dialogs.rc_dialogs.show_error` (ou equivalente).
- Depois, remover o import de messagebox do shim.

**Risco: MÉDIO.** Mudança afeta surface de testes.

---

## 3. Arquivos INTENCIONALMENTE NÃO MIGRADOS (manter messagebox nativo)

Estes **6 arquivos** usam `messagebox` em contextos onde a janela CTk pode não existir:

| Arquivo | Motivo | Chamadas |
|---|---|---|
| `src/core/auth_bootstrap.py` | Executa ANTES da janela CTk existir. `askretrycancel` + `showerror` durante bootstrap de autenticação. | 3 |
| `src/core/tk_exception_handler.py` | Handler global de exceção `Tk.report_callback_exception`. Pode não ter parent CTk válido. | 1 |
| `src/core/app.py` | Bloco `except` durante init catastrófico da janela principal. | 1 |
| `src/utils/errors.py` | `sys.excepthook` global. Pode rodar sem qualquer janela. | 1 |
| `src/utils/network.py` | Cria seu próprio `tk.Tk()` root para mostrar erro offline. Contexto isolado. | 1 |
| `src/utils/helpers/cloud_guardrails.py` | Função sem parâmetro `parent`. Chamada de contextos variados. | 1 |

**Total: 8 chamadas nativas MANTIDAS intencionalmente.**

---

## 4. Cuidados para o smoke test

### 4.1 Fluxos críticos a testar

- [ ] **Login com credenciais erradas** → `login_dialog.py` deve mostrar erro CTk (não nativo)
- [ ] **Salvar cliente com campos vazios** → `client_editor_dialog.py` → validação com `show_error`
- [ ] **Editar cliente existente** → `client_editor_dialog.py` → todas as validações
- [ ] **Upload de arquivo** → `browser.py` + `uploader_supabase.py` → progresso + erros
- [ ] **Excluir cliente** → `view.py` → `ask_yes_no` deve retornar bool correto
- [ ] **Excluir notificação** → `notifications_popup.py` → confirm + error paths
- [ ] **Fluxo de caixa: adicionar/editar/excluir** → `fluxo_caixa_frame.py` + `cashflow/ui.py`
- [ ] **Hub: abrir tarefas/obrigações** → `hub_dashboard_callbacks.py` warnings
- [ ] **Subpastas: erro de criação** → `subpastas_dialog.py`
- [ ] **Menu "Sobre"** → `menu_bar.py` → `show_info`
- [ ] **Gerenciamento de usuários** → `users.py` → warnings e exclusão
- [ ] **PDF preview: salvar/exportar** → `pdf_viewer_actions.py`
- [ ] **Lixeira: restaurar/limpar** → `lixeira_service.py`
- [ ] **Senhas do cliente** → verificar se Senhas dialog (se usa rc_dialogs) funciona

### 4.2 O que observar em cada dialog

1. **Ícone RC** visível na barra de título (não deve exibir ícone genérico Tk/feather)
2. **Sem flash branco** ao abrir (alpha=0 → reveal suave)
3. **Centralizado** sobre a janela pai
4. **Botões respondem** corretamente (Sim/Não retorna bool, OK fecha, etc.)
5. **Tema dark/light** — se o app estiver em dark mode, o dialog deve ser escuro
6. **Não deve travar** — `wait_window()` bloqueia corretamente até fechar

### 4.3 Problemas potenciais a observar

| Problema | Sintoma | Causa provável | Fix |
|---|---|---|---|
| Dialog não aparece | Ação executa mas nenhum popup | `parent=None` passado para função que precisa de parent válido | Passar `self` ou widget mais próximo |
| Dialog aparece atrás da janela | Popup existe mas não é visível | `transient()` não setado corretamente | Verificar `_make_dialog` com o parent passado |
| Botão retorna valor errado | Exclusão não executa após confirmar | `ask_yes_no` retorna `False` indevidamente | Verificar se `result["value"]` está correto |
| Import error no startup | `ModuleNotFoundError: rc_dialogs` | Path de import incorreto | Verificar se usa `src.ui.dialogs.rc_dialogs` (com `src.`) |
| Flash de janela branca | Dialog pisca branco brevemente | `alpha=0` não sendo aplicado antes de `deiconify` | Verificar `_deferred_show` timing |

---

## 5. Referência técnica do `rc_dialogs.py`

### Arquitetura interna

```
show_info / show_error / show_warning
    └── _make_dialog(parent, title, w, h)  →  CTkToplevel (alpha=0)
    └── _deferred_show(dlg, parent)        →  after(220ms) → alpha=1.0
    └── dlg.wait_window()                  →  bloqueia até fechar
```

```
ask_yes_no / ask_ok_cancel / ask_retry_cancel
    └── _make_dialog(parent, title, w, h)  →  CTkToplevel (alpha=0)
    └── result = {"value": False}          →  dict mutável
    └── botão "Sim/OK/Retry" → result["value"] = True + destroy
    └── botão "Não/Cancelar"  → destroy (mantém False)
    └── _deferred_show(dlg, parent)        →  after(220ms) → alpha=1.0
    └── dlg.wait_window()                  →  bloqueia até fechar
    └── return result["value"]
```

### Tokens visuais

```python
DIALOG_BTN_W = 100     # src/ui/ui_tokens.py
DIALOG_BTN_H = 32
BUTTON_RADIUS = 6
APP_BG = ("#f5f5f5", "#1a1a2e")  # light, dark

# Cores por tipo de botão:
# Confirmação (Sim/OK/Retry): azul padrão CTk
# Negação (Não/Cancelar):     cinza ("#555", "#444") / ("#666", "#555")
# Warning OK:                  âmbar ("#d97706", "#f59e0b") / ("#b45309", "#d97706")
# Error OK:                    vermelho ("#dc2626", "#ef4444") / ("#b91c1c", "#dc2626")
# Info OK:                     azul padrão CTk
```

---

## 6. Resumo numérico

| Métrica | Valor |
|---|---|
| Chamadas migradas | ~140 |
| Arquivos fonte editados | 25 |
| Chamadas pendentes (migrável) | ~8 (lixeira.py) + 1 shim (hub_debug_helpers.py) |
| Chamadas mantidas intencionalmente | 8 (6 arquivos unsafe) |
| Funções no rc_dialogs.py | 6 |
| Testes passando | 453/453 |

---

## 7. Checklist final antes de release

- [ ] Migrar `lixeira.py` (8 chamadas, risco baixo)
- [ ] Resolver shim `hub_debug_helpers.py` (verificar testes)
- [ ] Smoke test manual completo (seção 4.1)
- [ ] Rodar `python -m pytest tests/ -q` novamente após cada mudança
- [ ] Verificar grep final: `grep -rn "messagebox\.\(show\|ask\)" src/` — só deve restar os 6 arquivos skip + comentários
- [ ] Considerar adicionar testes unitários para as 3 novas funções do `rc_dialogs.py`
