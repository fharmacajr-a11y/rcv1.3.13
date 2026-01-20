# Plano de Migração Completa para CustomTkinter

**Data:** 2026-01-16  
**Versão:** v1.5.42  
**Objetivo:** Eliminar bugs visuais e completar migração do ttkbootstrap para CustomTkinter

---

## 📊 Executive Summary

### Estado Atual
- **67 arquivos** com imports de ttkbootstrap
- **100+ widgets** ttkbootstrap em uso (Button, Frame, Label, Entry, Combobox, etc.)
- **100+ ocorrências** do parâmetro `bootstyle` (incompatível com CTk)
- **Microfase 24 parcialmente implementada:** CustomTkinter ativo para formulário de clientes
- **Bugs visuais identificados:** Inconsistências de tema, crashes com imagens, estilos misturados

### Escopo da Migração
- **41 módulos principais** para migrar
- **26 arquivos de testes** para atualizar
- **10+ tipos de widgets** para substituir
- **3 sistemas de tema** para consolidar (ttkbootstrap, ttk, CustomTkinter)

### Benefícios Esperados
- ✅ Interface moderna e consistente
- ✅ Eliminação de bugs visuais
- ✅ Tema light/dark funcionando 100%
- ✅ Código mais limpo e manutenível
- ✅ Melhor experiência do usuário

---

## 🗺️ Arquitetura Alvo

### Política de Widgets (SSoT)

```python
# ✅ PERMITIDO: CustomTkinter via SSoT
from src.ui.ctk_config import ctk, HAS_CUSTOMTKINTER

# ✅ PERMITIDO: ttk apenas para widgets sem equivalente CTk
from tkinter import ttk  # Apenas para Treeview, Separator

# ❌ PROIBIDO: Import direto de customtkinter
import customtkinter  # VIOLAÇÃO!

# ❌ PROIBIDO: ttkbootstrap
import ttkbootstrap as tb  # LEGACY - REMOVER!
```

### Mapeamento de Widgets

| ttkbootstrap | CustomTkinter | ttk (fallback) | Status |
|-------------|---------------|----------------|--------|
| `tb.Button` | `ctk.CTkButton` | - | ⚠️ Migrar |
| `tb.Frame` | `ctk.CTkFrame` | - | ⚠️ Migrar |
| `tb.Label` | `ctk.CTkLabel` | - | ⚠️ Migrar |
| `tb.Entry` | `ctk.CTkEntry` | - | ⚠️ Migrar |
| `tb.Text` | `ctk.CTkTextbox` | - | ⚠️ Migrar |
| `tb.Checkbutton` | `ctk.CTkCheckBox` | - | ⚠️ Migrar |
| `tb.Radiobutton` | `ctk.CTkRadioButton` | - | ⚠️ Migrar |
| `tb.Combobox` | `ctk.CTkOptionMenu` | - | ⚠️ Migrar |
| `tb.Progressbar` | `ctk.CTkProgressBar` | - | ⚠️ Migrar |
| `tb.Scrollbar` | `ctk.CTkScrollbar` | - | ⚠️ Migrar |
| `tb.Labelframe` | `ctk.CTkFrame` + `CTkLabel` | - | ⚠️ Migrar |
| `tb.Toplevel` | `ctk.CTkToplevel` | - | ⚠️ Migrar |
| `tb.DateEntry` | **N/A** | `ttk.DateEntry` ou custom | ⚠️ Substituir |
| (Treeview) | **N/A** | `ttk.Treeview` | ✅ Mantém ttk |
| (Separator) | **N/A** | `ttk.Separator` | ✅ Mantém ttk |

### Sistema de Cores

```python
# CustomTkinter - 2 modos + 3 temas de cor
ctk.set_appearance_mode("light" | "dark")
ctk.set_default_color_theme("blue" | "dark-blue" | "green")

# ❌ Remover: ttkbootstrap bootstyle
bootstyle="primary" | "secondary" | "success" | "danger" | "warning" | "info"
```

---

## 📋 Inventário Completo

### Módulos Principais (src/)

#### 🔴 Prioridade CRÍTICA (crashes ou funcionalidades principais)

1. **src/ui/splash.py** (19 linhas com tb)
   - Widgets: `tb.Toplevel`, `tb.Frame`, `tb.Label`, `tb.Progressbar`
   - Bootstyle: `INFO`
   - Impacto: Primeira tela do app
   - Estimativa: 2-3 horas

2. **src/ui/login_dialog.py** (7 linhas com tb)
   - Widgets: `tb.Entry`, `tb.Button`
   - Bootstyle: `INFO`, `DANGER`
   - Impacto: Autenticação
   - Estimativa: 1-2 horas

3. **src/ui/topbar.py** (1 linha com tb)
   - Widgets: `tb.Frame` (container principal)
   - Impacto: Navegação global
   - Estimativa: 30 min

4. **src/modules/main_window/views/main_window_actions.py** (1 linha com tb)
   - Widgets: `tb.Button` em ações
   - Impacto: Ações principais
   - Estimativa: 1 hora

#### 🟠 Prioridade ALTA (módulos visíveis)

5. **src/modules/hub/** (8 arquivos, ~50 linhas)
   - `hub_screen.py`, `hub_dashboard_view.py`, `hub_notes_view.py`
   - `hub_quick_actions_view.py`, `hub_dialogs.py`
   - `dashboard_center.py`, `modules_panel.py`, `notes_panel_view.py`
   - Widgets: `tb.Frame`, `tb.Label`, `tb.Button`, `tb.Labelframe`
   - Bootstyle: múltiplos (`primary`, `secondary`, `info`, `warning`, `danger`)
   - Impacto: Dashboard principal
   - Estimativa: 8-12 horas

6. **src/modules/clientes/** (3 arquivos)
   - `client_obligations_window.py`, `client_obligations_frame.py`, `obligation_dialog.py`
   - Widgets: `tb.Frame`, `tb.Label`, `tb.Button`, `tb.DateEntry`, `tb.Combobox`
   - Bootstyle: `primary`, `danger`
   - Impacto: Gestão de obrigações (funcionalidade crítica)
   - Estimativa: 4-6 horas

7. **src/modules/clientes/forms/** (3 arquivos)
   - `client_picker.py`, `client_subfolders_dialog.py`, `client_subfolder_prompt.py`
   - Widgets: `tb.Frame`, `tb.Entry`, `tb.Button`
   - Impacto: Diálogos de seleção
   - Estimativa: 2-3 horas

8. **src/modules/tasks/views/task_dialog.py** (16 linhas)
   - Widgets: `tb.Toplevel`, `tb.Frame`, `tb.Label`, `tb.Entry`, `tb.Button`, `tb.DateEntry`
   - Bootstyle: `primary`, `secondary`
   - Impacto: Gestão de tarefas
   - Estimativa: 3-4 horas

9. **src/modules/passwords/views/** (3 arquivos)
   - `passwords_screen.py`, `password_dialog.py`, `client_passwords_dialog.py`
   - Widgets: múltiplos
   - Impacto: Gestão de senhas
   - Estimativa: 4-5 horas

10. **src/modules/anvisa/views/** (3 arquivos)
    - `anvisa_screen.py`, `anvisa_footer.py`, `_anvisa_history_popup_mixin.py`
    - Widgets: `ttk.Frame`, `ttk.Label`, `ttk.Button`, `ttk.DateEntry`
    - Bootstyle: múltiplos
    - Impacto: Módulo Anvisa
    - Estimativa: 6-8 horas

#### 🟡 Prioridade MÉDIA (componentes compartilhados)

11. **src/ui/components/** (6 arquivos)
    - `progress_dialog.py`, `misc.py`, `notifications_popup.py`
    - `lists.py`, `inputs.py`, `buttons.py`
    - Widgets: todos os tipos
    - Bootstyle: todos os estilos
    - Impacto: Componentes reutilizáveis
    - Estimativa: 10-15 horas

12. **src/ui/widgets/scrollable_frame.py** (1 arquivo)
    - Widgets: `tb.Frame`, `tb.Scrollbar`
    - Impacto: Scrolling em múltiplos módulos
    - Estimativa: 2-3 horas

13. **src/ui/placeholders.py** (1 arquivo)
    - Widgets: `tb.Frame`, `tb.Label`, `tb.Button`
    - Bootstyle: `secondary`
    - Impacto: Placeholders vazios
    - Estimativa: 1 hora

#### 🟢 Prioridade BAIXA (módulos menos usados)

14. **src/modules/lixeira/views/lixeira.py** (1 arquivo)
    - Widgets: múltiplos
    - Impacto: Lixeira
    - Estimativa: 2-3 horas

15. **src/modules/cashflow/views/fluxo_caixa_frame.py** (1 arquivo)
    - Widgets: múltiplos
    - Impacto: Fluxo de caixa
    - Estimativa: 2-3 horas

#### 🔵 Prioridade OPCIONAL (arquivos legacy/deprecated)

16. **src/ui/theme.py** (1 linha)
    - Import: `from ttkbootstrap import Style`
    - Status: Já possui fallback para ttk.Style
    - Ação: Marcar DEPRECATED

17. **src/utils/themes.py** (7 linhas com bootstyle)
    - Status: **JÁ MARCADO DEPRECATED**
    - Ação: Nenhuma (manter compatibilidade)

18. **src/utils/theme_manager.py**
    - Status: **JÁ MARCADO DEPRECATED**
    - Ação: Nenhuma (manter compatibilidade)

19. **src/modules/main_window/views/theme_setup.py** (2 linhas)
    - Import: `ttkbootstrap.style.Colors`, `ThemeDefinition`
    - Status: Legacy theme system
    - Ação: Deprecar se não usado

---

### Testes (tests/)

#### Testes Unitários para Atualizar (26 arquivos)

- `tests/unit/ui/test_splash_style.py`
- `tests/unit/utils/test_themes_combobox_style.py`
- `tests/unit/modules/tasks/views/test_task_dialog.py`
- `tests/unit/modules/hub/**` (11 arquivos)
- `tests/unit/modules/clientes/views/test_client_obligations_frame.py`

**Estratégia:**
- Atualizar mocks para CTk
- Substituir asserções de `tb.Button` → `ctk.CTkButton`
- Remover testes de `bootstyle` (não aplicável)
- Adicionar testes de appearance_mode

**Estimativa:** 15-20 horas

---

### Scripts (scripts/)

- `scripts/perf_clients_treeview.py` (1 arquivo)
  - Ação: Atualizar ou marcar como tool script (low priority)

---

## 🎯 Plano de Execução em Fases

### **FASE 1: Fundação e Componentes Críticos** ⭐⭐⭐
**Duração:** 2-3 dias  
**Prioridade:** CRÍTICA

#### Objetivos:
- App inicia sem crashes
- Login e splash funcionais
- Navegação principal operacional

#### Tarefas:
1. ✅ [CONCLUÍDO] Migrar `topbar_nav.py` e `notifications_button.py`
2. ⬜ Migrar `src/ui/splash.py`
   - Substituir `tb.Toplevel` → `ctk.CTkToplevel`
   - Substituir `tb.Progressbar` → `ctk.CTkProgressBar`
   - Remover `bootstyle=INFO`
   - Adicionar `fg_color`, `progress_color` baseados em appearance_mode
3. ⬜ Migrar `src/ui/login_dialog.py`
   - Substituir `tb.Entry` → `ctk.CTkEntry`
   - Substituir `tb.Button` → `ctk.CTkButton`
   - Remover `bootstyle` parameters
   - Implementar cores dinâmicas (light/dark)
4. ⬜ Migrar `src/ui/topbar.py`
   - Substituir `tb.Frame` → `ctk.CTkFrame`
   - Verificar integração com TopbarNav/TopbarActions
5. ⬜ Migrar `src/modules/main_window/views/main_window_actions.py`
   - Substituir botões em ações principais

#### Validação:
```bash
# Testar startup
python main.py

# Validar SSoT
python scripts/validate_ctk_policy.py

# Testes unitários
python -m pytest tests/unit/ui/test_splash_style.py -v
```

---

### **FASE 2: Dashboard e Hub** ⭐⭐⭐
**Duração:** 3-5 dias  
**Prioridade:** ALTA

#### Objetivos:
- Dashboard principal funcional
- Cards e indicadores visuais consistentes
- Painel de notas e ações rápidas operacional

#### Tarefas:
1. ⬜ Migrar `src/modules/hub/views/hub_screen.py`
   - Substituir `tb.Frame` → `ctk.CTkFrame`
   - Integrar com GlobalThemeManager
2. ⬜ Migrar `src/modules/hub/views/hub_dashboard_view.py`
   - Migrar cards e indicadores
   - Implementar cores dinâmicas para success/danger/warning
3. ⬜ Migrar `src/modules/hub/views/dashboard_center.py`
   - Função `_build_indicator_card`: CTkFrame com cores
   - Remover todos os `bootstyle`
4. ⬜ Migrar `src/modules/hub/views/modules_panel.py`
   - Substituir `tb.Labelframe` → `ctk.CTkFrame` com `CTkLabel` superior
   - Migrar botões de módulos
5. ⬜ Migrar `src/modules/hub/views/notes_panel_view.py`
   - Migrar lista de notas
   - Botão "Adicionar Nota"
6. ⬜ Migrar `src/modules/hub/views/hub_quick_actions_view.py`
   - Ações rápidas com CTkButton
7. ⬜ Migrar `src/modules/hub/views/hub_dialogs.py`
   - Diálogos de criação/edição de notas

#### Validação:
```bash
# Testar dashboard
python main.py
# Navegar para Hub e testar todas as funcionalidades

# Testes
python -m pytest tests/unit/modules/hub/ -v -k "not mf59 and not mf60 and not mf62"
```

---

### **FASE 3: Módulo Clientes** ⭐⭐
**Duração:** 2-3 dias  
**Prioridade:** ALTA

#### Objetivos:
- Obrigações regulatórias funcionais
- Diálogos de picker e subpastas operacionais
- Formulário principal já migrado (Microfase 5)

#### Tarefas:
1. ⬜ Migrar `src/modules/clientes/views/client_obligations_window.py`
   - Substituir `tb.Frame` → `ctk.CTkFrame`
2. ⬜ Migrar `src/modules/clientes/views/client_obligations_frame.py`
   - Tabela de obrigações
   - Botões de ação
3. ⬜ Migrar `src/modules/clientes/views/obligation_dialog.py`
   - **CRÍTICO:** `tb.DateEntry` não tem equivalente CTk
   - **Solução:** Manter `ttk.DateEntry` ou criar custom widget
   - Migrar demais widgets
4. ⬜ Migrar `src/modules/clientes/forms/client_picker.py`
   - Diálogo de seleção de cliente
5. ⬜ Migrar `src/modules/clientes/forms/client_subfolders_dialog.py`
   - Diálogo de subpastas
6. ⬜ Migrar `src/modules/clientes/forms/client_subfolder_prompt.py`
   - Prompt de nome de subpasta

#### Validação:
```bash
# Testar módulo clientes
python main.py
# Navegar para Clientes → Obrigações → CRUD completo

python -m pytest tests/unit/modules/clientes/ -v
```

---

### **FASE 4: Componentes Compartilhados** ⭐⭐
**Duração:** 4-6 dias  
**Prioridade:** ALTA

#### Objetivos:
- Inputs, buttons, listas padronizados
- Diálogos de progresso funcionais
- Notificações operacionais

#### Tarefas:
1. ⬜ Migrar `src/ui/components/inputs.py` (arquivo grande!)
   - `create_search_controls`: migrar toolbar de busca
   - Substituir `tb.Entry`, `tb.Combobox`, `tb.Button`
   - Manter `ttk.Combobox` se necessário (styled)
   - **Desafio:** Placeholder e ícones de busca
2. ⬜ Migrar `src/ui/components/buttons.py`
   - Funções de criação de botões padrão
   - Remover todos os `bootstyle`
3. ⬜ Migrar `src/ui/components/lists.py`
   - Componentes de lista
4. ⬜ Migrar `src/ui/components/progress_dialog.py`
   - `tb.Progressbar` → `ctk.CTkProgressBar`
   - Botão cancelar
5. ⬜ Migrar `src/ui/components/notifications_popup.py`
   - Popup de notificações
   - Múltiplos bootstyles para estados
6. ⬜ Migrar `src/ui/components/misc.py`
   - Componentes diversos (status, etc.)
7. ⬜ Migrar `src/ui/widgets/scrollable_frame.py`
   - Frame scrollable reutilizável

#### Validação:
```bash
# Testar em múltiplos módulos que usam esses componentes
python -m pytest tests/unit/ui/components/ -v
```

---

### **FASE 5: Módulos Secundários** ⭐
**Duração:** 3-4 dias  
**Prioridade:** MÉDIA

#### Objetivos:
- Tasks, Passwords, Anvisa funcionais
- Módulos menos usados estáveis

#### Tarefas:
1. ⬜ Migrar `src/modules/tasks/views/task_dialog.py`
   - **CRÍTICO:** `tb.DateEntry` → solução custom ou ttk
   - Demais widgets
2. ⬜ Migrar `src/modules/passwords/views/`
   - `passwords_screen.py`
   - `password_dialog.py`
   - `client_passwords_dialog.py`
3. ⬜ Migrar `src/modules/anvisa/views/`
   - `anvisa_screen.py` (grande e complexo!)
   - `anvisa_footer.py`
   - `_anvisa_history_popup_mixin.py`
   - **CRÍTICO:** Múltiplos `DateEntry` widgets
4. ⬜ Migrar `src/modules/lixeira/views/lixeira.py`
5. ⬜ Migrar `src/modules/cashflow/views/fluxo_caixa_frame.py`

#### Validação:
```bash
python -m pytest tests/modules/lixeira/ -v
python -m pytest tests/unit/modules/tasks/ -v
```

---

### **FASE 6: Placeholders e Utilitários** ⭐
**Duração:** 1-2 dias  
**Prioridade:** BAIXA

#### Tarefas:
1. ⬜ Migrar `src/ui/placeholders.py`
2. ⬜ Migrar `src/ui/subpastas_dialog.py` (se usar tb)
3. ⬜ Deprecar `src/ui/theme.py`
4. ⬜ Deprecar `src/modules/main_window/views/theme_setup.py`
5. ⬜ Atualizar `src/ui/custom_dialogs.py` (se necessário)
6. ⬜ Atualizar `src/ui/feedback.py` (se necessário)

---

### **FASE 7: Testes e QA** ⭐⭐⭐
**Duração:** 3-5 dias  
**Prioridade:** CRÍTICA

#### Objetivos:
- Todos os testes passando
- Cobertura mantida/melhorada
- App estável em light/dark

#### Tarefas:
1. ⬜ Atualizar testes unitários de UI
   - `tests/unit/ui/` (3 arquivos)
2. ⬜ Atualizar testes de Hub
   - `tests/unit/modules/hub/` (11 arquivos)
3. ⬜ Atualizar testes de Clientes
   - `tests/unit/modules/clientes/` (1 arquivo)
4. ⬜ Atualizar testes de Tasks
   - `tests/unit/modules/tasks/` (1 arquivo)
5. ⬜ Atualizar testes de utils
   - `tests/unit/utils/` (1 arquivo)
6. ⬜ Executar QA manual completo
   - Testar todos os módulos
   - Toggle light/dark em cada tela
   - Verificar responsividade
7. ⬜ Executar validações
   ```bash
   python scripts/validate_ctk_policy.py
   python -m pytest -c pytest_cov.ini --cov
   python -m pre-commit run --all-files
   ```

---

### **FASE 8: Limpeza Final** ⭐
**Duração:** 1-2 dias  
**Prioridade:** BAIXA

#### Tarefas:
1. ⬜ Remover imports não usados de ttkbootstrap
2. ⬜ Remover `bootstyle` parameters de code comments
3. ⬜ Atualizar documentação
4. ⬜ Gerar CHANGELOG entry
5. ⬜ Remover `ttkbootstrap` do requirements.txt
6. ⬜ Atualizar README com screenshots

---

## 🛠️ Padrões de Migração

### Template: Migração de Button

```python
# ❌ ANTES (ttkbootstrap)
import ttkbootstrap as tb
btn = tb.Button(
    parent,
    text="Salvar",
    command=self._handle_save,
    bootstyle="primary",
    width=10
)

# ✅ DEPOIS (CustomTkinter)
from src.ui.ctk_config import ctk
btn = ctk.CTkButton(
    parent,
    text="Salvar",
    command=self._handle_save,
    width=80,  # pixels, não caracteres!
    height=28,
    # Cores automáticas baseadas no appearance_mode
)
```

### Template: Migração de Entry

```python
# ❌ ANTES
import ttkbootstrap as tb
entry = tb.Entry(
    parent,
    textvariable=var,
    width=30,
    bootstyle="info"
)

# ✅ DEPOIS
from src.ui.ctk_config import ctk
entry = ctk.CTkEntry(
    parent,
    textvariable=var,
    width=300,  # pixels
    # fg_color, text_color, border_color automáticos
)
```

### Template: Migração de Frame

```python
# ❌ ANTES
import ttkbootstrap as tb
frame = tb.Frame(parent, padding=10, bootstyle="dark")

# ✅ DEPOIS
from src.ui.ctk_config import ctk
frame = ctk.CTkFrame(parent)
# padding via grid/pack
```

### Template: Migração de Labelframe

```python
# ❌ ANTES
import ttkbootstrap as tb
lf = tb.Labelframe(parent, text="Detalhes", padding=10)

# ✅ DEPOIS
from src.ui.ctk_config import ctk
# Solução 1: Frame + Label superior
frame = ctk.CTkFrame(parent)
label = ctk.CTkLabel(frame, text="Detalhes", anchor="w")
label.pack(side="top", fill="x", padx=10, pady=(5, 0))
# conteúdo
content_frame = ctk.CTkFrame(frame)
content_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Solução 2: Apenas Frame com fg_color diferenciado
frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"))
```

### Template: Migração de Combobox

```python
# ❌ ANTES
import ttkbootstrap as tb
combo = tb.Combobox(
    parent,
    textvariable=var,
    values=["Opção 1", "Opção 2"],
    state="readonly",
    width=20
)

# ✅ DEPOIS - Opção 1: CTkOptionMenu (dropdown simples)
from src.ui.ctk_config import ctk
menu = ctk.CTkOptionMenu(
    parent,
    variable=var,
    values=["Opção 1", "Opção 2"],
    width=200
)

# ✅ DEPOIS - Opção 2: Manter ttk.Combobox (se precisa autocompletar)
from tkinter import ttk
combo = ttk.Combobox(
    parent,
    textvariable=var,
    values=["Opção 1", "Opção 2"],
    state="readonly",
    width=20
)
# Aplicar estilo via ttk_compat
```

### Template: DateEntry (SEM EQUIVALENTE CTk!)

```python
# ❌ ANTES
from ttkbootstrap.widgets import DateEntry
date_entry = DateEntry(parent, dateformat="%d/%m/%Y")

# ✅ DEPOIS - Opção 1: Usar ttk diretamente (se disponível)
from tkinter import ttk
try:
    from ttkbootstrap.widgets import DateEntry as TtkDateEntry
    date_entry = TtkDateEntry(parent, dateformat="%d/%m/%Y")
except:
    # Fallback para Entry simples
    date_entry = ttk.Entry(parent, width=15)
    # Validação manual de data

# ✅ DEPOIS - Opção 2: Custom widget com CTkEntry + calendar popup
from src.ui.ctk_config import ctk
# TODO: Implementar CTkDatePicker custom widget
```

### Template: Progressbar

```python
# ❌ ANTES
import ttkbootstrap as tb
progress = tb.Progressbar(
    parent,
    mode="determinate",
    maximum=100,
    length=400,
    bootstyle="info-striped"
)

# ✅ DEPOIS
from src.ui.ctk_config import ctk
progress = ctk.CTkProgressBar(
    parent,
    width=400,
    height=20,
    mode="determinate",
    # progress_color automático baseado no tema
)
progress.set(0)  # valor inicial (0.0 a 1.0)
```

### Template: Cores Dinâmicas

```python
# Para mapear bootstyles para cores CTk
from src.ui.theme_manager import theme_manager

def get_button_color(style: str) -> tuple[str, str]:
    """Retorna (cor_light, cor_dark) baseado no bootstyle legacy."""
    mode = theme_manager.get_current_mode()
    
    colors = {
        "primary": ("#1f77b4", "#1f77b4"),     # azul
        "secondary": ("#6c757d", "#6c757d"),   # cinza
        "success": ("#28a745", "#28a745"),     # verde
        "danger": ("#dc3545", "#dc3545"),      # vermelho
        "warning": ("#ffc107", "#ffc107"),     # amarelo
        "info": ("#17a2b8", "#17a2b8"),        # ciano
    }
    
    return colors.get(style, colors["primary"])

# Uso:
fg_color = get_button_color("success")
btn = ctk.CTkButton(parent, text="OK", fg_color=fg_color)
```

---

## ⚠️ Desafios e Soluções

### 1. DateEntry Widget

**Problema:** CustomTkinter não possui widget de calendário  
**Impacto:** 6+ arquivos (anvisa_screen, task_dialog, obligation_dialog, cashflow)

**Soluções:**
- ✅ **Curto prazo:** Manter ttkbootstrap.DateEntry isoladamente
- ✅ **Médio prazo:** Criar CTkDatePicker custom widget
- ⚠️ **Longo prazo:** Integrar biblioteca third-party (tkintercalendar)

**Implementação:**
```python
# src/ui/widgets/ctk_date_picker.py (TO CREATE)
from src.ui.ctk_config import ctk
import tkinter as tk
from tkinter import ttk
from datetime import date

class CTkDatePicker(ctk.CTkFrame):
    """Custom date picker widget for CustomTkinter."""
    def __init__(self, master, dateformat="%d/%m/%Y", **kwargs):
        super().__init__(master, **kwargs)
        # CTkEntry para display
        # CTkButton para abrir calendar popup
        # ttk.Calendar no popup (third-party ou custom)
```

### 2. Labelframe

**Problema:** CustomTkinter não possui Labelframe nativo  
**Impacto:** ~15 arquivos

**Solução:** Frame + Label superior
```python
def create_ctk_labelframe(parent, text: str) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent)
    label = ctk.CTkLabel(frame, text=text, anchor="w")
    label.pack(side="top", fill="x", padx=10, pady=(5, 0))
    return frame
```

### 3. Bootstyle Colors

**Problema:** Mapeamento de 6 bootstyles para CTk colors  
**Impacto:** 100+ ocorrências

**Solução:** Helper function + theme manager integration
```python
# src/ui/ctk_colors.py (TO CREATE)
BOOTSTYLE_COLORS = {
    "primary": {"light": "#007bff", "dark": "#0056b3"},
    "secondary": {"light": "#6c757d", "dark": "#545b62"},
    "success": {"light": "#28a745", "dark": "#1e7e34"},
    "danger": {"light": "#dc3545", "dark": "#bd2130"},
    "warning": {"light": "#ffc107", "dark": "#e0a800"},
    "info": {"light": "#17a2b8", "dark": "#117a8b"},
}

def get_ctk_color(bootstyle: str, mode: str = None) -> str:
    if mode is None:
        from src.ui.theme_manager import theme_manager
        mode = theme_manager.get_current_mode()
    return BOOTSTYLE_COLORS.get(bootstyle, BOOTSTYLE_COLORS["primary"])[mode]
```

### 4. Combobox vs OptionMenu

**Problema:** OptionMenu não permite autocompletar/typed input  
**Impacto:** Filtros e buscas

**Solução:** Manter ttk.Combobox para casos complexos, aplicar styling via ttk_compat

### 5. Treeview

**Problema:** Já usa ttk.Treeview (sem equivalente CTk)  
**Solução:** ✅ Manter ttk.Treeview, já styled via ttk_compat.py

### 6. Ícones e Imagens

**Problema:** CTkImage tem comportamento diferente de PhotoImage  
**Impacto:** Topbar, botões com ícones

**Solução:**
```python
from src.ui.ctk_config import ctk
from PIL import Image

# Carregar ícone
img = Image.open("assets/icon.png")
ctk_image = ctk.CTkImage(
    light_image=img,
    dark_image=img,  # ou versão dark
    size=(20, 20)
)
btn = ctk.CTkButton(parent, image=ctk_image, text="")
```

---

## 📊 Estimativas de Tempo

| Fase | Duração | Complexidade | Prioridade |
|------|---------|--------------|------------|
| FASE 1: Fundação | 2-3 dias | Alta | CRÍTICA |
| FASE 2: Hub | 3-5 dias | Alta | ALTA |
| FASE 3: Clientes | 2-3 dias | Média | ALTA |
| FASE 4: Componentes | 4-6 dias | Alta | ALTA |
| FASE 5: Módulos Secundários | 3-4 dias | Média | MÉDIA |
| FASE 6: Placeholders | 1-2 dias | Baixa | BAIXA |
| FASE 7: Testes e QA | 3-5 dias | Alta | CRÍTICA |
| FASE 8: Limpeza | 1-2 dias | Baixa | BAIXA |
| **TOTAL** | **19-30 dias** | - | - |

**Estimativa conservadora:** 4-6 semanas de desenvolvimento full-time

---

## ✅ Critérios de Sucesso

### Técnicos
- [ ] 0 imports de ttkbootstrap em código de produção (exceto DateEntry isolado)
- [ ] 0 violações da política SSoT CustomTkinter
- [ ] 0 ocorrências de `bootstyle=` em código ativo
- [ ] Todos os testes unitários passando
- [ ] Cobertura de código mantida (>80%)
- [ ] Pre-commit hooks passando
- [ ] App inicia sem erros ou warnings de deprecation

### Funcionais
- [ ] Toggle light/dark funciona em todas as telas
- [ ] Todos os módulos principais operacionais
- [ ] Formulários e diálogos responsivos
- [ ] Ícones e imagens carregando corretamente
- [ ] Performance mantida/melhorada
- [ ] Sem bugs visuais reportados

### Experiência do Usuário
- [ ] Interface consistente em todo o app
- [ ] Cores e contrastes adequados (light e dark)
- [ ] Feedback visual claro em interações
- [ ] Animações suaves (quando aplicável)
- [ ] Sem elementos visuais quebrados

---

## 📝 Checklist de Migração por Arquivo

### Template de Checklist

Para cada arquivo a migrar:
- [ ] Remover `import ttkbootstrap as tb`
- [ ] Adicionar `from src.ui.ctk_config import ctk, HAS_CUSTOMTKINTER`
- [ ] Substituir todos os `tb.Widget` → `ctk.CTkWidget`
- [ ] Remover todos os `bootstyle=` parameters
- [ ] Ajustar `width`/`height` (chars → pixels)
- [ ] Substituir `.state()` por `.configure(state=...)`
- [ ] Testar em light e dark mode
- [ ] Atualizar testes correspondentes
- [ ] Executar validações

---

## 🔍 Validação e Monitoramento

### Comandos de Validação

```bash
# 1. Política SSoT
python scripts/validate_ctk_policy.py

# 2. Buscar imports remanescentes
grep -r "import ttkbootstrap" src/

# 3. Buscar bootstyle remanescente
grep -r "bootstyle=" src/

# 4. Testes unitários
python -m pytest -c pytest_cov.ini --cov

# 5. Pre-commit
python -m pre-commit run --all-files

# 6. Startup test
python main.py
```

### Métricas de Progresso

Criar script para monitorar progresso:
```bash
# scripts/migration_progress.py
import subprocess

def count_ttkbootstrap_imports():
    result = subprocess.run(
        ["grep", "-r", "import ttkbootstrap", "src/"],
        capture_output=True, text=True
    )
    return len(result.stdout.splitlines())

def count_bootstyle_usages():
    result = subprocess.run(
        ["grep", "-r", "bootstyle=", "src/"],
        capture_output=True, text=True
    )
    return len(result.stdout.splitlines())

print(f"ttkbootstrap imports: {count_ttkbootstrap_imports()}")
print(f"bootstyle usages: {count_bootstyle_usages()}")
```

---

## 📚 Recursos e Referências

### Documentação
- [CustomTkinter Docs](https://github.com/TomSchimansky/CustomTkinter/wiki)
- [CustomTkinter Widget Examples](https://github.com/TomSchimansky/CustomTkinter/wiki/Examples)
- [Microfase 24 Doc](MICROFASE_24_CTK_TEMA_PRINCIPAL.md)
- [CTK Policy Doc](CTK_IMPORT_POLICY.md)

### Código de Referência
- `src/modules/clientes/forms/client_form_view_ctk.py` (exemplo completo migrado)
- `src/ui/ctk_config.py` (SSoT)
- `src/ui/theme_manager.py` (GlobalThemeManager)
- `src/ui/ttk_compat.py` (styling para ttk widgets)

### Ferramentas
- `scripts/validate_ctk_policy.py` - Validador SSoT
- `src/ui/ctk_config.py` - Single source of truth
- Pre-commit hooks - Validação automática

---

## 🚀 Começando

### Setup Inicial

1. **Backup do código atual:**
   ```bash
   git checkout -b backup-pre-ctk-migration
   git push origin backup-pre-ctk-migration
   ```

2. **Criar branch de desenvolvimento:**
   ```bash
   git checkout -b feature/ctk-migration-phase-1
   ```

3. **Configurar ambiente:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Executar validações iniciais:**
   ```bash
   python scripts/validate_ctk_policy.py
   python -m pytest -c pytest_cov.ini --no-cov -q
   ```

### Workflow por Fase

1. Começar pela FASE 1
2. Para cada arquivo:
   - Criar branch feature específica (opcional)
   - Migrar código
   - Testar manualmente
   - Executar testes automatizados
   - Commit
3. Ao final da fase:
   - QA completo da fase
   - Merge para develop/main
   - Tag de versão (ex: v1.5.42-ctk-phase1)
4. Repetir para próxima fase

---

## 📞 Suporte e Escalação

### Problemas Conhecidos
- **Crash de imagem:** Usar emoji fallback ou desabilitar temporariamente
- **DateEntry:** Usar ttkbootstrap isoladamente até custom widget
- **Combobox complexo:** Manter ttk.Combobox com styling

### Quando Escalar
- Bugs críticos bloqueando múltiplas fases
- Performance degradada significativamente
- Incompatibilidades arquiteturais descobertas

---

## 📅 Cronograma Sugerido

```
Semana 1: FASE 1 + FASE 2 (início)
Semana 2: FASE 2 (fim) + FASE 3
Semana 3: FASE 4
Semana 4: FASE 5 + FASE 6
Semana 5: FASE 7 (QA intensivo)
Semana 6: FASE 8 + buffer/ajustes
```

---

## 🎉 Conclusão

Esta migração eliminará bugs visuais, modernizará a interface e consolidará o sistema de temas. Seguir este plano em fases garante progresso incremental e minimiza riscos.

**Próximos passos:**
1. Revisar e aprovar este plano
2. Começar FASE 1 imediatamente
3. Monitorar progresso semanalmente
4. Ajustar cronograma conforme necessário

---

**Documento criado em:** 2026-01-16  
**Autor:** GitHub Copilot  
**Versão:** 1.0  
**Status:** APROVADO PARA EXECUÇÃO
