# Plano de Migração CustomTkinter (CTk) - v1.5.73

## 📊 Estado Atual (Diagnóstico)

**Data**: 13/02/2026  
**Versão**: v1.5.73

### Resultados dos Testes CI
- ✅ `validate_ttk_policy.py --ci`: **PASS**
- ✅ `test_ttk_policy.py`: **16/16 testes passaram**
- ⚠️ `ctk_audit`: **227 ocorrências em 28 arquivos**

### TOP 5 Arquivos por Ocorrências

| Rank | Arquivo | Ocorrências | Prioridade |
|------|---------|-------------|------------|
| 1 | `src/modules/hub/views/dashboard_center.py` | 39 | 🔴 ALTA |
| 2 | `src/ui/components/inputs.py` | 23 | 🔴 ALTA |
| 3 | `src/ui/components/lists.py` | 19 | 🟡 MÉDIA |
| 4 | `src/modules/hub/views/hub_dialogs.py` | 15 | 🔴 ALTA |
| 5 | `src/ui/components/buttons.py` | 14 | 🟡 MÉDIA |

### Distribuição por Categoria

| Categoria | Quantidade | % |
|-----------|------------|---|
| `tk.Label` | 45 | 19.8% |
| `tk.Frame` | 42 | 18.5% |
| `tk.Button` | 31 | 13.7% |
| `ScrolledText` | 14 | 6.2% |
| `background=` / `foreground=` | 28 | 12.3% |
| `tk.Text` / `tk.Entry` | 11 | 4.8% |
| `ttk.*` (exceto Treeview) | 8 | 3.5% |
| Outros atributos (relief, bd, highlightthickness) | 48 | 21.2% |

---

## 🎯 Estratégia de Migração

### Princípios
1. **Não quebrar testes/CI** - Cada commit deve manter os testes passando
2. **Respeitar política TTK** - Manter `ttk.Treeview` com `CTkTreeviewContainer`
3. **Mudanças pequenas e seguras** - Commits atômicos por arquivo/função
4. **Priorizar impacto visual** - Dashboard e dialogs primeiro (alta visibilidade)

### Regras de Substituição

| De | Para | Observação |
|-----|------|------------|
| `tk.Frame` | `ctk.CTkFrame` | Use `fg_color` em vez de `bg` |
| `tk.Label` | `ctk.CTkLabel` | Use `text_color` em vez de `foreground` |
| `tk.Button` | `ctk.CTkButton` | Já tem suporte a dark mode |
| `tk.Entry` | `ctk.CTkEntry` | Use `placeholder_text` quando aplicável |
| `tk.Text` | `ctk.CTkTextbox` | Replace ScrolledText também |
| `ScrolledText` | `ctk.CTkTextbox` | Já tem scroll embutido |
| `bg=` | `fg_color=` | Para CTkFrame/CTkLabel |
| `foreground=` | `text_color=` | Para CTkLabel |
| `relief=` | _remover_ | Não suportado em CTk |
| `bd=` | `border_width=` | Para CTkFrame |
| `highlightthickness=` | _remover_ | Não suportado em CTk |

### Exceções
- **`ttk.Treeview`**: Manter com `CTkTreeviewContainer` e `TtkTreeviewManager`
- **Type hints**: Não alterar anotações de tipo (ex: `parent: tk.Frame`)
- **Fallbacks**: Código dentro de `else: # fallback` pode usar tk/ttk

---

## 📋 Backlog Priorizado (Microfases)

### 🔴 FASE 1: Dashboard Principal (Alta Visibilidade)

**Objetivo**: Eliminar widgets tk/ttk do dashboard do Hub, começando com dashboard_center.py

#### Commit 1.1: `dashboard_center.py` - Substituir ScrolledText
**Arquivos**: `src/modules/hub/views/dashboard_center.py`

**Mudanças**:
- [ ] Linha 274: `ScrolledText(` → `ctk.CTkTextbox(`
- [ ] Linha 382-385: Remover função `_build_scrolledtext_widget()` (obsoleta)
- [ ] Linha 1162: `ScrolledText(` → `ctk.CTkTextbox(` (tasks_textbox)
- [ ] Linha 1294: `ScrolledText(` → `ctk.CTkTextbox(` (deadlines_textbox)
- [ ] Atualizar imports: remover `ScrolledText` do `tkinter.scrolledtext`
- [ ] Ajustar parâmetros: `wrap="word"`, `height` → estimativa de linhas

**Testes**:
```bash
pytest tests/modules/hub/ -k dashboard -v
python -m src.ui.ctk_audit --fix | grep dashboard_center
```

#### Commit 1.2: `dashboard_center.py` - Substituir tk.Frame por CTkFrame
**Arquivos**: `src/modules/hub/views/dashboard_center.py`

**Mudanças**:
- [ ] Linha 176: `tk.Frame(parent)` → `ctk.CTkFrame(parent, fg_color="transparent")`
- [ ] Linha 441: `tk.Frame(parent)` → `ctk.CTkFrame(parent, fg_color="transparent")`
- [ ] Linha 681: `tk.Frame(grid_frame)` → `ctk.CTkFrame(grid_frame, fg_color="transparent")`
- [ ] Linha 1349: `tk.Frame(parent)` → `ctk.CTkFrame(parent, fg_color="transparent")`

**Nota**: Use `fg_color="transparent"` para containers lógicos (sem cor de fundo explícita)

#### Commit 1.3: `dashboard_center.py` - Substituir tk.Label por CTkLabel
**Arquivos**: `src/modules/hub/views/dashboard_center.py`

**Mudanças**:
- [ ] Linha 188, 204, 221, 238: Substituir `tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 463, 484: Labels de cards (value_label, text_label)
- [ ] Linha 695, 713: Labels de radar (lbl_name, lbl_counts)
- [ ] Linha 1028, 1046, 1134, 1208, 1230, 1266: Labels de listas
- [ ] Linha 1362, 1382: Labels de erro (lbl_icon, lbl_msg)
- [ ] Remover `foreground=` → usar `text_color=` (linhas 308, 309, 805)

**Impacto**: ~20 substituições de Label

#### Commit 1.4: `hub_dashboard_view.py` - Containers e loading
**Arquivos**: `src/modules/hub/views/hub_dashboard_view.py`

**Mudanças**:
- [ ] Linha 67: `self.center_spacer = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 76: `self.dashboard_scroll = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 115, 143: `tk.Label(` → `ctk.CTkLabel(` (loading e empty)

---

### 🔴 FASE 2: Dialogs e Pop-ups (Alta Visibilidade)

#### Commit 2.1: `hub_dialogs.py` - Dialog de criação de nota
**Arquivos**: `src/modules/hub/views/hub_dialogs.py`

**Mudanças**:
- [ ] Linha 66: `tk.Frame(dialog, padding=10)` → `ctk.CTkFrame(dialog)`
- [ ] Linha 70: `tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 73: `text_frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 79: `tk.Text(` → `ctk.CTkTextbox(`
- [ ] Linha 97: `btn_frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 126, 132: `tk.Button(` → `ctk.CTkButton(`

**Nota**: Testar criação de notas no Hub

#### Commit 2.2: `hub_dialogs.py` - Dialog de histórico de notas
**Arquivos**: `src/modules/hub/views/hub_dialogs.py`

**Mudanças**:
- [ ] Linha 611: `tk.Frame(dialog, padding=10)` → `ctk.CTkFrame(dialog)`
- [ ] Linha 614: `tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 620: `tree_frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 723: `btn_frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 726, 750: `tk.Button(` → `ctk.CTkButton(`

**Nota**: Manter `ttk.Treeview` com container existente

---

### 🟡 FASE 3: Componentes de UI (Média Visibilidade)

#### Commit 3.1: `inputs.py` - Barra de pesquisa
**Arquivos**: `src/ui/components/inputs.py`

**Mudanças**:
- [ ] Linha 142: `tk.Label(frame, text="Pesquisar:")` → `ctk.CTkLabel(`
- [ ] Linha 150: `search_container = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Remover `bg=`, `bd=`, `relief=`, `highlightthickness=` (linhas 152-155)
- [ ] Linha 170: `icon_label = tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 213: `placeholder_label = tk.Label(` → `ctk.CTkLabel(`
- [ ] Remover `background=`, `foreground=` → usar `fg_color=`, `text_color=`

**Impacto**: ~23 ocorrências

#### Commit 3.2: `inputs.py` - Botões de ação
**Arquivos**: `src/ui/components/inputs.py`

**Mudanças**:
- [ ] Linha 262: `search_button = tk.Button(` → `ctk.CTkButton(`
- [ ] Linha 284: `clear_button = tk.Button(` → `ctk.CTkButton(`
- [ ] Linha 294: `tk.Label(frame, text="Ordenar por:")` → `ctk.CTkLabel(`
- [ ] Linha 331: `tk.Label(frame, text="Status:")` → `ctk.CTkLabel(`
- [ ] Linha 384: `obrigacoes_button = tk.Button(` → `ctk.CTkButton(`
- [ ] Linha 403: `lixeira_button = tk.Button(` → `ctk.CTkButton(`
- [ ] Remover `bg=` (linha 407)

#### Commit 3.3: `lists.py` - Configurações de zebra (tag_configure)
**Arquivos**: `src/ui/components/lists.py`

**Mudanças**:
- [ ] Linhas 93-97: Trocar `foreground=` → `text_color=` nas tags
- [ ] Linhas 259-260, 505-509: Atualizar `background=` → `fg_color=` (se aplicável ao ttk)
- [ ] Linha 271: `foreground=` → `text_color=` na tag `has_obs`
- [ ] Linha 359-364: Tooltip label (substituir por CTkLabel)

**Nota**: Tags do ttk.Treeview usam `foreground=` e `background=` - verificar compatibilidade

#### Commit 3.4: `buttons.py` - Botões de ação de clientes
**Arquivos**: `src/ui/components/buttons.py`

**Mudanças**:
- [ ] Linha 58: `frame = tk.Frame(parent)` → `ctk.CTkFrame(parent)`
- [ ] Linha 65-67: Botões Novo/Editar/Arquivos → `ctk.CTkButton(`
- [ ] Linha 82: btn_excluir → `ctk.CTkButton(`
- [ ] Linha 111, 121, 129: Batch operations → `ctk.CTkButton(`
- [ ] Remover `bg=` (linhas 65, 82, 112)

---

### 🟡 FASE 4: Módulos Hub (Média Visibilidade)

#### Commit 4.1: `hub_quick_actions_view.py` - Painel de módulos
**Arquivos**: `src/modules/hub/views/hub_quick_actions_view.py`

**Mudanças**:
- [ ] Linha 102: `self.modules_panel = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 113: `title_label = tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 120: `content_container = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 133, 158, 182: Labels de seções → `ctk.CTkLabel(`
- [ ] Linha 140, 165, 189: Frames de ações → `ctk.CTkFrame(`

**Nota**: Botões criados por `_create_action_button()` (linha 90) - verificar se usa tk.Button

#### Commit 4.2: `modules_panel.py` - Cards de módulos
**Arquivos**: `src/modules/hub/views/modules_panel.py`

**Mudanças**:
- [ ] Linha 45: `label = tk.Label(` → `ctk.CTkLabel(`
- [ ] Remover `background=`, `relief=` (linhas 49-50)
- [ ] Linha 158: `btn = tk.Button(` → `ctk.CTkButton(`

---

### 🟢 FASE 5: Dialogs e Componentes Auxiliares (Baixa Visibilidade)

#### Commit 5.1: `progress_dialog.py` - Dialogs de progresso
**Arquivos**: `src/ui/components/progress_dialog.py`

**Mudanças**:
- [ ] Linha 35: `body = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 41: `self._lbl = tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 176: `body = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 195, 215, 234: Labels → `ctk.CTkLabel(`
- [ ] Linha 261: `self._cancel_button = tk.Button(` → `ctk.CTkButton(`
- [ ] Remover `foreground=`, `bg=` (linhas 221, 240, 262)

#### Commit 5.2: `notifications_popup.py` - Popup de notificações
**Arquivos**: `src/ui/components/notifications/notifications_popup.py`

**Mudanças**:
- [ ] Linha 211, 221, 229, 248: Botões → `ctk.CTkButton(`
- [ ] Remover `bg=` (linhas 215, 233)

#### Commit 5.3: `login_dialog.py` - Tela de login
**Arquivos**: `src/ui/login_dialog.py`

**Mudanças**:
- [ ] Linha 88, 112: Labels (email e senha) → `ctk.CTkLabel(`
- [ ] Linha 100, 124: Entries → `ctk.CTkEntry(`
- [ ] Linha 161: `buttons_frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 173, 189: Botões Exit/Login → `ctk.CTkButton(`
- [ ] Remover `bg=` (linhas 177, 193)

#### Commit 5.4: `splash.py` - Tela de splash
**Arquivos**: `src/ui/splash.py`

**Mudanças**:
- [ ] Linha 142: `content = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 172: `logo_label = tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 191: `title = tk.Label(` → `ctk.CTkLabel(`
- [ ] Linha 198: `sep = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 201: `msg = tk.Label(` → `ctk.CTkLabel(`
- [ ] Remover `bg=` (linha 198)

#### Commit 5.5: `placeholders.py` - Telas de placeholder
**Arquivos**: `src/ui/placeholders.py`

**Mudanças**:
- [ ] Linha 38-39: Frames top/center → `ctk.CTkFrame(`
- [ ] Linha 49-50: Labels header/desc → `ctk.CTkLabel(`
- [ ] Linha 51: `btn = tk.Button(` → `ctk.CTkButton(`
- [ ] Linha 106: `container = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 108: `title = tk.Label(` → `ctk.CTkLabel(`

---

### 🟢 FASE 6: Widgets Especializados (Baixa Prioridade)

#### Commit 6.1: `misc.py` - Contador de status
**Arquivos**: `src/ui/components/misc.py`

**Mudanças**:
- [ ] Linha 108: `frame = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 118, 125, 132: Labels → `ctk.CTkLabel(`
- [ ] Linha 119: `right_box = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Linha 197: Icon label → `ctk.CTkLabel(`

#### Commit 6.2: `topbar.py` e `topbar_nav.py` - Barras superiores
**Arquivos**:
- `src/ui/topbar.py`
- `src/ui/components/topbar_nav.py`

**Mudanças**:
- [ ] `topbar.py` linha 146: `container = tk.Frame(` → `ctk.CTkFrame(`
- [ ] Remover `bg=` (linhas 129, 146)
- [ ] `topbar_nav.py` linha 78: Remover `bg=`

#### Commit 6.3: `custom_dialogs.py` e `feedback.py` - Utilitários
**Arquivos**:
- `src/ui/custom_dialogs.py`
- `src/ui/feedback.py`

**Mudanças**:
- [ ] `custom_dialogs.py` linha 50: `icon_label = tk.Label(` → `ctk.CTkLabel(`
- [ ] `feedback.py` linha 321-323: Frame e Label do toast → CTk
- [ ] Remover `bg=` (linhas 321, 328)

---

### 🔵 FASE 7: Widgets Canvas e Especializados (Avaliar Necessidade)

**Arquivos**:
- `src/ui/progress/pdf_batch_progress.py` (tk.Canvas)
- `src/ui/status_footer.py` (tk.Canvas para dot)
- `src/ui/widgets/scrollable_frame.py` (tk.Canvas + tk.Frame)
- `src/ui/widgets/busy.py` (bg= config)
- `src/ui/widgets/autocomplete_entry.py` (tk.Frame)

**Estratégia**:
- **Canvas**: Avaliar se pode ser substituído por CTkFrame com desenhos customizados ou manter tk.Canvas
- **scrollable_frame**: Considerar usar `CTkScrollableFrame` (widget nativo do CTk)
- **Prioridade baixa**: Impacto visual mínimo, funcionam bem com tema atual

---

## 🧪 Validação e Testes

### Checklist por Commit

Após cada commit, executar:

```bash
# 1. Validar política TTK
python scripts/validate_ttk_policy.py --ci

# 2. Testes CI da política
pytest tests/ci/test_ttk_policy.py -q

# 3. Audit CTK (verificar redução de ocorrências)
python -m src.ui.ctk_audit | tail -20

# 4. Testes específicos do módulo
pytest tests/modules/<módulo>/ -v

# 5. Teste visual manual
# - Abrir app
# - Alternar Light/Dark mode (F11)
# - Verificar componente modificado
```

### Critérios de Aceite Global

- [ ] `validate_ttk_policy.py --ci` continua passando
- [ ] Todos os testes em `tests/ci/test_ttk_policy.py` passam
- [ ] Ocorrências do CTK audit reduzidas de 227 para < 50
- [ ] App abre sem erros em Light e Dark mode
- [ ] Treeviews mantêm zebra correta em ambos os temas
- [ ] Nenhum flash branco perceptível em dialogs/janelas
- [ ] Todas as telas são navegáveis e funcionais

---

## 📈 Métricas de Progresso

### Objetivo

| Métrica | Inicial | Meta | Status |
|---------|---------|------|--------|
| Ocorrências CTK Audit | 227 | < 50 | 🔴 0% |
| Arquivos com problemas | 28 | < 8 | 🔴 0% |
| Coverage de CTk | ~40% | > 85% | 🔴 40% |
| Testes CI passando | 16/16 | 16/16 | ✅ 100% |

### Redução Esperada por Fase

| Fase | Ocorrências Resolvidas | % Total |
|------|------------------------|---------|
| FASE 1 | ~60 | 26.4% |
| FASE 2 | ~25 | 11.0% |
| FASE 3 | ~60 | 26.4% |
| FASE 4 | ~20 | 8.8% |
| FASE 5 | ~35 | 15.4% |
| **Total (F1-F5)** | **~200** | **88%** |
| FASE 6 | ~15 | 6.6% |
| FASE 7 | ~12 | 5.3% |

---

## 🚀 Execução

### Ordem de Implementação

1. **FASE 1** (dashboard_center.py) - 4 commits
2. **FASE 2** (hub_dialogs.py) - 2 commits
3. **Validação intermediária** - Testar Hub completo
4. **FASE 3** (components/inputs.py, lists.py, buttons.py) - 4 commits
5. **FASE 4** (módulos Hub) - 2 commits
6. **Validação intermediária** - Testar módulos
7. **FASE 5** (dialogs/placeholders) - 5 commits
8. **FASE 6** (widgets especializados) - 3 commits
9. **FASE 7** (opcional, avaliar necessidade)
10. **Validação final** - Smoke test completo

### Estimativa de Tempo

- **FASE 1-2**: 2-3 horas (alta prioridade)
- **FASE 3-4**: 2-3 horas (média prioridade)
- **FASE 5-6**: 2-3 horas (baixa prioridade)
- **FASE 7**: 1-2 horas (opcional)
- **Testes e validações**: 1-2 horas
- **Total estimado**: 8-14 horas

---

## 📝 Notas Importantes

### Política TTK (Manter)

- **`ttk.Treeview`**: Continuar usando com `CTkTreeviewContainer` e `TtkTreeviewManager`
- **Zebra stripes**: Aplicar via `apply_zebra()` após popular tree
- **Theme sync**: Manager já aplica tema automaticamente

### Type Hints

- Não alterar anotações de tipo (ex: `parent: tk.Frame`)
- Pyright/mypy aceitam tanto `tk.Frame` quanto `ctk.CTkFrame` como tipos válidos
- Apenas alterar instanciação em runtime

### Fallbacks

- Código dentro de `else: # fallback` pode usar tk/ttk (política permite)
- Ex: `if HAS_CUSTOMTKINTER: ... else: # fallback tk.Frame(...)`

### Atributos Removidos em CTk

| Atributo | Substituir por | Comportamento |
|----------|----------------|---------------|
| `relief=` | _remover_ | CTk usa flat sempre |
| `bd=` | `border_width=` | Apenas para CTkFrame |
| `highlightthickness=` | _remover_ | Não suportado |
| `padx=`, `pady=` | _usar pack/grid_ | Passar para layout manager |

### Cores

- CTk gerencia cores automaticamente (light/dark)
- Evitar hardcode de cores (ex: `#ffffff`)
- Usar `fg_color="transparent"` para containers lógicos
- Para cores específicas, consultar `src/ui/colors.py` ou tema CTk

---

## 🐛 Bugs Corrigidos (Pré-requisitos)

### ✅ Bug 1: Lista de clientes não muda para dark mode
**Arquivo**: `src/modules/clientes/ui/view.py`
**Linha**: 420-439 (`_on_theme_changed`)

**Problema**: Usava cache `self._tree_colors` com cores antigas do tema Light.

**Solução**: Chamar `self._sync_tree_theme_and_zebra()` para obter cores atualizadas.

```python
# ANTES
if self.tree_widget and self._tree_colors:
    apply_zebra(self.tree_widget, self._tree_colors)

# DEPOIS
if self.tree_widget:
    self._sync_tree_theme_and_zebra()
```

### ✅ Bug 2: Flash branco ao abrir UploadsBrowser
**Arquivo**: `src/modules/uploads/views/browser.py`
**Linhas**: 32-34 (imports), 122-160 (__init__)

**Problema**: Janela usava `withdraw()` + `show_centered()` padrão, causando flash branco.

**Solução**:
1. Usar `prepare_hidden_window(self)` logo após `super().__init__(parent)`
2. Aplicar `set_win_dark_titlebar(self)` antes de mostrar (Windows)
3. Substituir `show_centered(self)` por `show_centered_no_flash(self, parent, width=1000, height=620)`

```python
# Imports atualizados
from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash
from src.ui.dark_window_helper import set_win_dark_titlebar

# __init__ atualizado
super().__init__(parent)
prepare_hidden_window(self)  # Em vez de self.withdraw()
# ... build UI ...
set_win_dark_titlebar(self)
show_centered_no_flash(self, parent, width=1000, height=620)
```

---

## 📚 Referências

- **Política TTK**: `scripts/validate_ttk_policy.py`
- **Testes CI**: `tests/ci/test_ttk_policy.py`
- **CTk Audit**: `src/ui/ctk_audit.py`
- **CTk Config**: `src/ui/ctk_config.py`
- **Treeview Manager**: `src/ui/ttk_treeview_manager.py`
- **Window Utils**: `src/ui/window_utils.py`
- **Dark Helper**: `src/ui/dark_window_helper.py`

---

**Status**: ✅ Plano aprovado - Pronto para execução  
**Próximo passo**: Iniciar FASE 1 - Commit 1.1 (dashboard_center.py - ScrolledText)
