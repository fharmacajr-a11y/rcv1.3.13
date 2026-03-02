# Handoff — Migração Widgets `tkinter` → `CustomTkinter` (CTk)

**Data:** 25/02/2026  
**Versão:** v1.5.87  
**Status:** ~95% concluída  
**Testes:** 453 passed (zero falhas)

---

## 1. O que foi feito

### 1.1 Escopo da migração

Migração de **~111 instâncias** de widgets `tkinter` nativos para equivalentes `CustomTkinter` em **27 arquivos fonte**, eliminando todo código dual-mode (`HAS_CUSTOMTKINTER` condicional) e padronizando a UI no CTk.

### 1.2 Mapa de widgets migrados

| Widget tkinter | Equivalente CTk | Instâncias |
|---|---|---|
| `tk.Toplevel` | `ctk.CTkToplevel` | ~12 |
| `tk.Frame` | `ctk.CTkFrame` | ~20 |
| `tk.Label` | `ctk.CTkLabel` | ~15 |
| `tk.Button` | `make_btn()` (button_factory) | ~18 |
| `tk.Entry` | `ctk.CTkEntry` | ~8 |
| `tk.Text` / `tk.Text` | `ctk.CTkTextbox` | ~6 |
| `tk.Scrollbar` | `ctk.CTkScrollbar` | ~4 |
| `tk.Checkbutton` | `ctk.CTkCheckBox` | ~5 |
| `tk.Tk()` | `ctk.CTk()` | 1 |
| Heranças de classe condicionais | Herança direta CTk | 8 |
| Blocos dual-mode `HAS_CUSTOMTKINTER` | Removidos (branch CTk mantido) | ~60 blocos |

**Total: ~111 instâncias + ~60 blocos condicionais eliminados.**

### 1.3 Widgets INTENCIONALMENTE mantidos como tkinter

| Widget | Motivo |
|---|---|
| `tk.messagebox` | Migrado em processo separado para `rc_dialogs` (ver `MIGRATION_MESSAGEBOX_HANDOFF.md`) |
| `tk.filedialog` | Não tem equivalente CTk; funciona corretamente |
| `tk.StringVar` / `tk.IntVar` / `tk.BooleanVar` | Variáveis Tk — não são widgets visuais |
| `tk.TclError` / `tk.Event` | Exceções e eventos — não são widgets |
| `tk.Menu` | Menu nativo da janela — `ctk.CTkMenu` não existe |
| `tkinter.font` | Módulo de fontes — não é widget |
| `tkinter.ttk` (Treeview, Combobox, etc.) | Widgets complexos sem equivalente CTk direto |
| `tk.Canvas` | Usado por CTk internamente; manter para overlays |
| `tk.Listbox` | Sem equivalente CTk; usado em autocomplete |

---

## 2. Arquivos migrados — detalhamento completo

### 2.1 Herança de classe (8 arquivos)

Classes que herdavam condicionalmente de `tk.Widget` ou `ctk.CTkWidget` agora herdam **diretamente de CTk**:

| # | Arquivo | Classe | Antes | Depois |
|---|---|---|---|---|
| 1 | `src/modules/chatgpt/views/chatgpt_window.py` | `ChatGPTWindow` | `tk.Toplevel if not HAS_CTK else ctk.CTkToplevel` | `ctk.CTkToplevel` |
| 2 | `src/modules/main_window/views/main_window.py` (pdf_preview) | `PdfViewerWin` | Condicional | `ctk.CTkToplevel` |
| 3 | `src/modules/pdf_preview/views/pdf_converter_dialogs.py` | Dialogs | Condicional | `ctk.CTkToplevel` |
| 4 | `src/ui/scrollable_frame.py` | `ScrollableFrame` | Condicional | `ctk.CTkScrollableFrame` |
| 5 | `src/ui/users/users.py` | `UsersWindow` | Condicional | `ctk.CTkToplevel` |
| 6 | `src/modules/pdf_preview/views/pdf_batch_progress.py` | `PdfBatchProgressDialog` | Condicional | `ctk.CTkToplevel` |
| 7 | `src/ui/login_dialog.py` | `LoginDialog` | Condicional | `ctk.CTkToplevel` |
| 8 | `src/modules/hub/views/hub_screen.py` | `HubScreen` | `tk.Frame if not HAS_CTK else ctk.CTkFrame` | `ctk.CTkFrame` |

### 2.2 Remoção de blocos dual-mode `HAS_CUSTOMTKINTER` (14 arquivos)

Cada arquivo continha blocos `if HAS_CUSTOMTKINTER and ctk:` / `else:` que criavam widgets CTk ou tk conforme disponibilidade. O branch `else` (tkinter puro) foi removido, mantendo apenas o código CTk.

| # | Arquivo | Blocos removidos | Widgets afetados |
|---|---|---|---|
| 1 | `src/ui/login_dialog.py` | ~12 | Frame, Label, Entry, Button, Checkbutton, Text |
| 2 | `src/ui/splash.py` | ~8 | Frame, Label, Progressbar |
| 3 | `src/ui/feedback.py` | ~1 | Toplevel → CTkToplevel |
| 4 | `src/modules/hub/panels.py` | ~7 | Frame, Label, Button |
| 5 | `src/ui/topbar.py` | ~4 | Frame, Label, Button |
| 6 | `src/ui/widgets/placeholders.py` | ~4 | Frame, Label |
| 7 | `src/ui/widgets/buttons.py` | ~8 | Button (make_btn factory) |
| 8 | `src/ui/widgets/inputs.py` | ~7 | Combobox, Label, Button |
| 9 | `src/ui/widgets/misc.py` | ~4 | Frame, Label |
| 10 | `src/ui/dialogs/progress_dialog.py` | ~17 | Frame, Label, Progressbar, Button (BusyDialog + ProgressDialog) |
| 11 | `src/modules/hub/views/hub_quick_actions_view.py` | ~4 | Button (mk_btn), Frame (mk_section), Panel |
| 12 | `src/modules/hub/views/hub_screen.py` | ~2 | configure(), placeholder |
| 13 | `src/modules/hub/views/hub_screen_view_pure.py` | ~1 | Button (make_module_button) |
| 14 | `src/modules/main_window/views/main_window_layout.py` | ~1 | content_container `if ctk is not None:` |

**Em cada arquivo**, o import `from src.ui.ctk_config import HAS_CUSTOMTKINTER` também foi removido quando não era mais necessário.

### 2.3 Substituições simples de widget (14 arquivos)

Trocas diretas `tk.Widget(...)` → `ctk.CTkWidget(...)` sem envolver lógica condicional:

| # | Arquivo | Mudanças | Detalhes |
|---|---|---|---|
| 1 | `src/ui/dialogs/custom_dialogs.py` | 3 | 2× `tk.Toplevel` → `ctk.CTkToplevel`, 1× `tk.Label(bitmap="info")` → `ctk.CTkLabel(text="ℹ")` |
| 2 | `src/modules/lixeira/views/lixeira.py` | 1 | `tk.Toplevel` → `ctk.CTkToplevel` |
| 3 | `src/modules/hub/views/hub_dialogs.py` | 1 | `tk.Toplevel` → `ctk.CTkToplevel` |
| 4 | `src/ui/components/notifications/notifications_popup.py` | 5 | `tk.Toplevel` → `ctk.CTkToplevel`, 4× `tk.Button` → `make_btn`, adicionado imports `ctk` + `make_btn` |
| 5 | `src/ui/busy.py` | 1 | `tk.Toplevel` → `ctk.CTkToplevel` |
| 6 | `src/ui/components/autocomplete_entry.py` | 2 | `tk.Toplevel` → `ctk.CTkToplevel`, `tk.Frame` → `ctk.CTkFrame` |
| 7 | `src/modules/hub/views/modules_panel.py` | 3 | ToolTip: `tk.Toplevel` + `tk.Label` → `CTkToplevel` + `CTkLabel`, `tk.Button` → `make_btn` |
| 8 | `src/ui/components/lists.py` | 2 | Tooltip: `tk.Toplevel` + `tk.Label` → `CTkToplevel` + `CTkLabel` |
| 9 | `src/modules/hub/views/hub_screen_view.py` | 5 | 5× `tk.Frame` → `ctk.CTkFrame`, adicionado `from src.ui.ctk_config import ctk` |
| 10 | `src/modules/hub/services/hub_async_tasks_service.py` | 2 | `tk.Label` → `ctk.CTkLabel`, removido `import tkinter as tk` (não mais usado) |
| 11 | `src/modules/clientes/ui/widgets/file_list.py` | 1 | `tk.Scrollbar` → `ctk.CTkScrollbar` (horizontal) |
| 12 | `src/ui/page_view.py` | 1 | `tk.Scrollbar` → `ctk.CTkScrollbar` (vertical) |
| 13 | `src/utils/network.py` | 1 | `tk.Tk()` → `ctk.CTk()` |
| 14 | `src/ui/window_utils.py` | 1 | Atualização de docstring/exemplo |

### 2.4 Limpeza de imports

Após todas as migrações, foi feita uma verificação de imports órfãos:

- **`hub_async_tasks_service.py`**: `import tkinter as tk` removido (não mais usado após migação de `tk.Label` → `ctk.CTkLabel`)
- **14 arquivos de dual-mode**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER` removido de todos
- **`notifications_popup.py`**: Bug pré-existente corrigido — arquivo usava `ctk.` sem importar. Adicionado `from src.ui.ctk_config import ctk` e `from src.ui.widgets.button_factory import make_btn`

---

## 3. O que FALTA (pendências reais)

### 3.1 `src/modules/hub/views/hub_screen_view.py` — 3× `tk.LabelFrame` (PRIORIDADE ALTA)

Linhas 193, 204, 215 contêm `tk.LabelFrame` para seções de módulos ("Fiscal", "Gestão", etc.).

```python
# ANTES (atual)
fiscal_frame = tk.LabelFrame(inner, text="Fiscal e Tributário", padding=8)
gestao_frame = tk.LabelFrame(inner, text="Gestão", padding=8)
farma_frame = tk.LabelFrame(inner, text="Farmácias", padding=8)
```

**Para migrar:**
- `CTkFrame` não suporta `text=` nem `padding=` como `LabelFrame`
- Opção 1: Criar helper `CTkSection(parent, title)` que combina `CTkFrame` + `CTkLabel` como cabeçalho
- Opção 2: Usar `ctk.CTkFrame` com `border_width=1` + `CTkLabel` separado para o título
- Opção 3: Manter `ttk.LabelFrame` (via `tkinter.ttk`) que já funciona com temas

**Risco: MÉDIO.** `LabelFrame` é um widget composto sem equivalente direto em CTk. Requer decisão de design.

### 3.2 `src/ui/components/inputs.py` — 1× `tk.Frame` + 2× `tk.Label` (PRIORIDADE MÉDIA)

| Linha | Widget | Uso | Risco de migrar |
|---|---|---|---|
| 149 | `tk.Frame` | Container invisível para barra de busca | Baixo — pode ser `ctk.CTkFrame` |
| 169 | `tk.Label` | Ícone da lupa (overlay via `.place()` sobre Entry) | Alto — controle pixel-level de `bg`, `borderwidth=0` |
| 212 | `tk.Label` | Placeholder flutuante (overlay via `.place()`) | Alto — precisa casar `background` exatamente com Entry |

**Recomendação:** Migrar o `tk.Frame` da linha 149. Manter os `tk.Label` overlays como estão — funcionam e migrá-los pode causar regressão visual (CTkLabel não suporta `.place()` com mesmo nível de controle).

### 3.3 `src/ui/components/misc.py` — 1× `tk.Label` (NÃO MIGRAR)

Linha 184: `tk.Label(tree, image=icon, borderwidth=0, cursor="hand2")` — overlay via `.place()` sobre `ttk.Treeview`. **Intencional.** CTkLabel não deve ser filho de Treeview.

### 3.4 `HAS_CUSTOMTKINTER` em outros arquivos (NÃO MIGRAR)

`HAS_CUSTOMTKINTER` permanece em **8 arquivos** fora do escopo da migração de widgets. São usos legítimos em lógica de theming/bootstrap:

| Arquivo | Usos | Motivo |
|---|---|---|
| `src/ui/ctk_config.py` | Definição | SSoT — é onde a flag é definida |
| `src/ui/theme_toggle.py` | 4 | Lógica de toggle de tema |
| `src/ui/theme_manager.py` | 4 | Gerenciador de temas |
| `src/ui/components/topbar_nav.py` | 3 | Navegação TopBar com styling condicional |
| `src/ui/components/notifications/notifications_button.py` | 2 | Botão de notificações |
| `src/modules/main_window/views/main_window.py` | 2 | Seleção de base class (`ctk.CTk` vs `tk.Tk`) |
| `src/modules/main_window/views/main_window_actions.py` | 1 | Estilização condicional do status dot |
| `src/modules/hub/views/dashboard_center.py` | 6 | Renderização de dashboard |

**Estes NÃO devem ser removidos** — são guardas de segurança para ambientes sem CTk (testes, CI, etc.).

### 3.5 Bug visual: tela preta ao minimizar/restaurar no Windows (NÃO RESOLVIDO)

**Sintoma:** Ao minimizar o app e restaurar (clicar na taskbar), a área de conteúdo (Hub, dashboard, notas) fica toda preta por ~1-2 segundos antes de renderizar.

**Causa provável:** CustomTkinter desenha widgets via Canvas internos do Tk. No Windows, ao minimizar/restaurar, esses Canvas não recebem eventos de expose/repaint do Window Manager.

**O que foi tentado:**
- Bind de `<Unmap>`/`<Map>` para detectar minimize→restore e forçar `_draw()` recursivo nos widgets CTk do content container
- O fix foi implementado em `main_window_bootstrap.py` mas **não resolveu** e foi **revertido**

**Possíveis abordagens futuras:**
1. Investigar se é bug do CustomTkinter (testar com app CTk mínimo)
2. Usar `<Visibility>` ou `<Configure>` em vez de `<Map>`
3. Forçar `update_idletasks()` + `update()` no root após restore
4. Verificar se `fg_color=APP_BG` está sendo perdido durante minimize
5. Testar `app.after(100, lambda: app.configure(fg_color=APP_BG))` no `<Map>` event
6. Verificar se o problema existia ANTES da migração (pode ser bug pré-existente do CTk)

**Componentes visíveis após restore:** TopBar (topo) e StatusFooter (rodapé) renderizam normalmente. O problema está no `content_container` (`ctk.CTkFrame`) e tudo dentro dele (HubScreen, modules_panel, dashboard, notes).

---

## 4. Padrão de transformação aplicado

### 4.1 Herança de classe

```python
# ANTES
_Base = ctk.CTkToplevel if (HAS_CUSTOMTKINTER and ctk) else tk.Toplevel

class MyDialog(_Base):
    def __init__(self, parent):
        super().__init__(parent)

# DEPOIS
class MyDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
```

### 4.2 Bloco dual-mode

```python
# ANTES
if HAS_CUSTOMTKINTER and ctk:
    self.my_btn = ctk.CTkButton(parent, text="OK", command=self._ok)
else:
    self.my_btn = tk.Button(parent, text="OK", command=self._ok)

# DEPOIS
self.my_btn = ctk.CTkButton(parent, text="OK", command=self._ok)
```

### 4.3 Substituição simples de widget

```python
# ANTES
popup = tk.Toplevel(self)
popup.configure(bg="#1a1a2e")

# DEPOIS
popup = ctk.CTkToplevel(self)
popup.configure(fg_color="#1a1a2e")
```

### 4.4 Botão via button_factory

```python
# ANTES
btn = tk.Button(parent, text="Ação", command=callback, bg="#333", fg="#fff")

# DEPOIS
from src.ui.widgets.button_factory import make_btn
btn = make_btn(parent, text="Ação", command=callback)
```

### 4.5 Parâmetros que mudam entre tk e CTk

| Parâmetro tk | Parâmetro CTk | Notas |
|---|---|---|
| `bg` / `background` | `fg_color` | Cores de fundo |
| `fg` / `foreground` | `text_color` | Cor do texto |
| `font=("Segoe UI", 12)` | `font=("Segoe UI", 12)` | Mesmo formato |
| `bd` / `borderwidth` | `border_width` | Espessura da borda |
| `relief="flat"` | `corner_radius=0` | Sem borda arredondada |
| `bitmap="info"` | `text="ℹ"` | Ícones como Unicode |
| `orient="horizontal"` | `orientation="horizontal"` | Scrollbar |

---

## 5. Arquitetura de referência

### 5.1 Import centralizado do CTk

```python
# Fonte única (SSoT) — SEMPRE importar daqui
from src.ui.ctk_config import ctk              # módulo customtkinter
from src.ui.ctk_config import HAS_CUSTOMTKINTER # bool (True se CTk disponível)
```

### 5.2 Tokens visuais

```python
# src/ui/ui_tokens.py
APP_BG = ("#f5f5f5", "#1a1a2e")   # (light, dark) — fundo principal
SEP    = ("#e0e0e0", "#333333")   # separadores
```

### 5.3 Button factory

```python
# src/ui/widgets/button_factory.py
from src.ui.widgets.button_factory import make_btn

# Cria CTkButton com estilo padrão do projeto
btn = make_btn(parent, text="Label", command=callback)
```

### 5.4 Layout da janela principal

```
┌─────────────────────────────────────┐
│  AppMenuBar (tk.Menu — nativo)      │  ← NÃO migrado (intencional)
├─────────────────────────────────────┤
│  TopBar (CTkFrame — migrado)        │  ← Botões Home, PDF, Chat, etc.
├─────────────────────────────────────┤
│                                     │
│  content_container (CTkFrame)       │  ← NavigationController troca frames aqui
│  ┌─────────────────────────────┐    │
│  │  HubScreen (CTkFrame)       │    │
│  │  ├── modules_panel          │    │
│  │  ├── dashboard_scroll       │    │
│  │  └── notes_panel            │    │
│  └─────────────────────────────┘    │
│                                     │
├─────────────────────────────────────┤
│  StatusFooter (CTkFrame)            │  ← Contagem de clientes, status, user
└─────────────────────────────────────┘
```

**Build em 2 fases:**
1. `_build_layout_skeleton()` — cria `content_container` vazio + variáveis Tk (imediato)
2. `_build_layout_deferred()` — via `after(0)`, cria TopBar, Footer, Nav (não bloqueia paint)

---

## 6. Cuidados para smoke test da migração

### 6.1 Fluxos críticos a testar

- [ ] **Iniciar app** → Login dialog (CTkToplevel) renderiza corretamente
- [ ] **Hub** → Módulos, dashboard, notas carregam sem erro
- [ ] **TopBar** → Botões Home, PDF Converter, ChatGPT, Sites, Notificações funcionam
- [ ] **Navegar para Clientes** → Treeview + barra de busca funcional
- [ ] **Abrir PDF Viewer** → CTkToplevel abre corretamente
- [ ] **Abrir ChatGPT** → CTkToplevel abre e responde
- [ ] **Abrir Lixeira** → CTkToplevel com lista de itens
- [ ] **Notificações popup** → CTkToplevel com botões make_btn
- [ ] **ProgressDialog** → Barra de progresso CTk durante operações longas
- [ ] **Minimizar/Restaurar** → ⚠️ BUG CONHECIDO: tela preta temporária (ver seção 3.5)
- [ ] **Trocar tema** (Exibir → Tema) → Light ↔ Dark sem crash
- [ ] **Scrollbar vertical** → Lista de clientes (page_view.py) rola suavemente
- [ ] **Scrollbar horizontal** → Lista de arquivos (file_list.py) rola suavemente
- [ ] **Tooltips** → Módulos panel + Treeview mostram tooltip CTk
- [ ] **Autocomplete** → Dropdown de busca (CTkToplevel + CTkFrame)
- [ ] **Fechar app** → Sem exceções no console

### 6.2 O que observar em cada tela

1. **Sem mistura de cores** — widgets CTk devem respeitar `APP_BG` (sem patches cinza/branco)
2. **Texto legível** — `text_color` deve contrastar com fundo em ambos os temas
3. **Botões consistentes** — todos devem ter corner_radius padrão CTk
4. **Sem flash branco** — dialogs devem aparecer suavemente (alpha transition)
5. **Scrollbars funcionais** — CTkScrollbar responde a mouse wheel e drag

### 6.3 Problemas potenciais

| Problema | Sintoma | Causa provável | Fix |
|---|---|---|---|
| Widget cinza em fundo escuro | Retângulo cinza visível | `fg_color` não definido no CTkFrame | Adicionar `fg_color=APP_BG` |
| Botão não responde | Clique sem efeito | `make_btn` não recebeu `command=` | Verificar parâmetros |
| Tooltip com fundo branco | Tooltip aparece mas com cores erradas | `tk.Label` remanescente em tooltip | Verificar se migrou para `CTkLabel` |
| Scrollbar invisível | Scroll funciona mas barra não aparece | CTkScrollbar precisa de `configure(command=)` | Verificar binding |
| Crash ao fechar dialog | `TclError: bad window path` | CTkToplevel destruído antes de `wait_window` terminar | Adicionar `try/except` |
| LabelFrame sem borda | Seções sem moldura visual | `tk.LabelFrame` → não migrado (pendência 3.1) | Criar helper ou manter ttk |

---

## 7. Resumo numérico

| Métrica | Valor |
|---|---|
| Instâncias de widgets migradas | ~111 |
| Blocos dual-mode removidos | ~60 |
| Arquivos fonte editados | 27 |
| Heranças de classe corrigidas | 8 |
| Imports `HAS_CUSTOMTKINTER` removidos | 14 |
| Imports tk órfãos removidos | 1 |
| Bugs pré-existentes corrigidos | 1 (notifications_popup.py — faltava import ctk) |
| Instâncias pendentes (migráveis) | ~7 (3× LabelFrame + 1× Frame + 2× Label + 1× Label intencional) |
| `HAS_CUSTOMTKINTER` mantidos intencionalmente | 22 usos em 8 arquivos |
| Testes passando | 453/453 |
| Bug visual conhecido | 1 (tela preta no minimize/restore) |

---

## 8. Checklist final antes de release

- [ ] Decidir abordagem para `tk.LabelFrame` em `hub_screen_view.py` (3 instâncias)
- [ ] Avaliar migração de `tk.Frame` em `inputs.py` linha 149
- [ ] Investigar bug de tela preta no minimize/restore (pode ser bug CTk upstream)
- [ ] Smoke test manual completo (seção 6.1)
- [ ] Verificar grep final: `grep -rn "tk\.Toplevel\|tk\.Frame\|tk\.Label\|tk\.Button\|tk\.Entry\|tk\.Scrollbar" src/` — deve restar apenas os intencionais listados na seção 1.3 e 3
- [ ] Rodar `python -m pytest tests/ -q` após cada mudança adicional
- [ ] Testar em resolução 1080p e 4K (HiDPI) — CTk escala diferente de tk
- [ ] Testar com tema Light e Dark separadamente
