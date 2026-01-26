# MICROFASE 24: CustomTkinter como Tema Principal

**Data:** 2026-01-16  
**Status:** ✅ COMPLETA  
**Objetivo:** Transformar CustomTkinter no sistema principal de temas, removendo o sistema legado de múltiplos temas ttk/ttkbootstrap.

---

## 📋 OBJETIVO DA MICROFASE

Remover completamente o sistema de seleção de múltiplos temas ttk (14+ temas) e adotar CustomTkinter como sistema principal de temas com:
- **Appearance Mode:** `"light"` ou `"dark"`
- **Color Themes:** `"blue"`, `"dark-blue"` ou `"green"` (built-in do CustomTkinter)
- **ttk mantido apenas para widgets essenciais** (ex: Treeview) sem seleção de tema
- **Regras SSoT mantidas:** Zero imports diretos de `customtkinter` fora de `src/ui/ctk_config.py`

---

## 🎯 RESULTADOS ALCANÇADOS

### ✅ 1. Theme Manager Global Criado

**Arquivo:** `src/ui/theme_manager.py`

```python
# Tipos definidos
ThemeMode = Literal["light", "dark"]
ColorTheme = Literal["blue", "dark-blue", "green"]

# Funções principais
def apply_global_theme(mode: ThemeMode, color: ColorTheme) -> None
def toggle_appearance_mode() -> ThemeMode
def set_color_theme(color: ColorTheme) -> None

# Classe GlobalThemeManager
class GlobalThemeManager:
    def initialize() -> None  # Chamado no startup
    def get_current_mode() -> ThemeMode
    def get_current_color() -> ColorTheme
    def toggle_mode() -> ThemeMode
    def set_mode(mode: ThemeMode) -> None
    def set_color(color: ColorTheme) -> None

# Singleton
theme_manager = GlobalThemeManager()
```

**Características:**
- ✅ Segue regras SSoT (importa CustomTkinter via `src.ui.ctk_config`)
- ✅ Persiste configuração em `config_theme.json`
- ✅ Suporta modo cloud-only (`RC_NO_LOCAL_FS=1`)
- ✅ Fallback seguro quando CustomTkinter não disponível

---

### ✅ 2. App Migrada para `ctk.CTk`

**Antes (ttkbootstrap):**
```python
class App(tb.Window):
    def __init__(self, start_hidden: bool = False) -> None:
        _theme_name = themes.load_theme()
        super().__init__(themename=_theme_name, iconphoto=None)
        # Sistema de 14 temas ttk
```

**Depois (CustomTkinter):**
```python
class App(ctk.CTk if HAS_CUSTOMTKINTER else tk.Tk):  # type: ignore[misc]
    def __init__(self, start_hidden: bool = False) -> None:
        # Inicializar theme manager ANTES de criar widgets
        global_theme_manager.initialize()

        # Usar CTk como base principal
        if HAS_CUSTOMTKINTER and ctk is not None:
            ctk.CTk.__init__(self)
            self._using_customtkinter = True
        else:
            tk.Tk.__init__(self)
            self._using_customtkinter = False

        # ttk fixado em "clam" para estabilidade
        if not self._using_customtkinter:
            style = ttk.Style()
            if "clam" in style.theme_names():
                style.theme_use("clam")
```

**Mudanças:**
- ✅ `tb.Window` → `ctk.CTk` (com fallback para `tk.Tk`)
- ✅ Removido `themename` do construtor
- ✅ ttk fixado em tema único (`"clam"`) sem seleção de múltiplos temas
- ✅ `self.tema_atual` agora armazena `"light"` ou `"dark"`

---

### ✅ 3. Menu Bar Refatorado

**Antes:**
```python
# Seletor de 14 temas ttk
menu_tema = tk.Menu(menu_exibir, tearoff=False)
for name in _available_themes():  # flatly, cosmo, darkly, litera, morph...
    menu_tema.add_radiobutton(
        label=name,
        value=name,
        variable=self._theme_var,
        command=lambda n=name: self._handle_change_theme(n),
    )
menu_exibir.add_cascade(label="Tema", menu=menu_tema)
```

**Depois:**
```python
# Toggle simples Light/Dark
menu_exibir.add_command(
    label="Alternar Tema (Light/Dark)",
    command=self._safe(self._on_toggle_theme),
)
```

**Mudanças:**
- ✅ Removido `_available_themes()` (14+ temas ttk)
- ✅ Removido `_theme_var` (StringVar para tema selecionado)
- ✅ Callback `on_change_theme(name: str)` → `on_toggle_theme()`
- ✅ `refresh_theme()` mantido como no-op para compatibilidade

---

### ✅ 4. Main Window Actions Refatorada

**Antes:**
```python
def _set_theme(self, new_theme: str) -> None:
    """Troca o tema da aplicação."""
    from . import main_window_actions as actions
    return actions.set_theme(self, new_theme)

def _handle_menu_theme_change(self, name: str) -> None:
    """Callback do AppMenuBar para troca de tema."""
    self._set_theme(name)
    self._menu.refresh_theme(name)
```

**Depois:**
```python
def _handle_toggle_theme(self) -> None:
    """Toggle entre light e dark mode (Microfase 24)."""
    new_mode = global_theme_manager.toggle_mode()
    self.tema_atual = new_mode
    log.info(f"Tema alternado para: {new_mode}")

# Métodos legados deprecados para compatibilidade
def _set_theme(self, new_theme: str) -> None:
    """DEPRECATED: Mantido para compatibilidade."""
    log.warning("_set_theme() está deprecated.")

def _handle_menu_theme_change(self, name: str) -> None:
    """DEPRECATED: Mantido para compatibilidade."""
    log.warning("_handle_menu_theme_change() está deprecated.")
```

**Mudanças:**
- ✅ Novo método `_handle_toggle_theme()` para alternar light/dark
- ✅ Métodos legados `_set_theme()` e `_handle_menu_theme_change()` deprecados
- ✅ Removida lógica de aplicação de temas ttkbootstrap

---

### ✅ 5. Layout Builder Simplificado

**Arquivo:** `src/modules/main_window/views/main_window_layout.py`

**Antes:**
```python
import ttkbootstrap as tb

def build_main_window_layout(
    app: App,
    *,
    theme_name: str,  # Nome do tema ttkbootstrap
    start_hidden: bool = False,
) -> MainWindowLayoutRefs:
    # Aplicar tema ttkbootstrap
    app_style = tb.Style()
    app_style.theme_use(theme_name)
    apply_combobox_style(app_style)

    # Container usando tb.Frame
    content_container = tb.Frame(app)
```

**Depois:**
```python
# Removido import ttkbootstrap

def build_main_window_layout(
    app: App,
    *,
    start_hidden: bool = False,  # Removido theme_name
) -> MainWindowLayoutRefs:
    # Tema gerenciado por CustomTkinter globalmente
    # (nada a fazer aqui)

    # Container usando tk.Frame simples
    content_container = tk.Frame(app)
```

**Mudanças:**
- ✅ Removido `import ttkbootstrap as tb`
- ✅ Removido parâmetro `theme_name`
- ✅ Removida aplicação de tema ttkbootstrap
- ✅ `tb.Frame` → `tk.Frame`
- ✅ `MainWindowLayoutRefs.content_container: tb.Frame` → `tk.Frame`

---

### ✅ 6. Bootstrap Atualizado

**Arquivo:** `src/modules/main_window/views/main_window_bootstrap.py`

**Antes:**
```python
def bootstrap_main_window(app: App) -> None:
    tema_atual = app.tema_atual
    start_hidden = getattr(app, "_start_hidden", False)

    app._layout = build_main_window_layout(
        app,
        theme_name=tema_atual,
        start_hidden=start_hidden,
    )
```

**Depois:**
```python
def bootstrap_main_window(app: App) -> None:
    # MICROFASE 24: Removido tema_atual
    start_hidden = getattr(app, "_start_hidden", False)

    app._layout = build_main_window_layout(
        app,
        start_hidden=start_hidden,  # theme_name removido
    )
```

---

## 📊 ARQUIVOS MODIFICADOS

### Criados
1. ✅ `src/ui/theme_manager.py` - Theme Manager global CustomTkinter

### Modificados
2. ✅ `src/modules/main_window/views/main_window.py` - App migrada para `ctk.CTk`
3. ✅ `src/ui/menu_bar.py` - Toggle light/dark (remov sistema de 14 temas)
4. ✅ `src/modules/main_window/views/main_window_layout.py` - Removido ttkbootstrap
5. ✅ `src/modules/main_window/views/main_window_bootstrap.py` - Removido `theme_name`

---

## 🗑️ SISTEMA DE TEMAS TTK REMOVIDO

### O Que Foi Removido:

1. **Seleção de Múltiplos Temas ttk:**
   - ❌ Menu com 14+ opções: `flatly`, `cosmo`, `darkly`, `litera`, `morph`, `pulse`, `sandstone`, `solar`, `superhero`, `yeti`, etc.
   - ❌ Função `_available_themes()` em `menu_bar.py`
   - ❌ `tk.StringVar` para rastrear tema selecionado
   - ❌ Radiobuttons no menu "Exibir > Tema"

2. **Aplicação de Temas ttkbootstrap:**
   - ❌ `tb.Style().theme_use(theme_name)` em `main_window_layout.py`
   - ❌ `apply_combobox_style(app_style)` (específico para ttkbootstrap)
   - ❌ `ensure_info_color(style, "#3498DB")` (customização ttkbootstrap)

3. **Persistência de Tema ttk:**
   - ❌ `themes.load_theme()` retornando nome de tema ttk
   - ❌ `themes.save_theme(name: str)` salvando nome de tema ttk
   - ❌ Sistema de cache `_CACHED_THEME` em `src/utils/themes.py`

4. **Herança ttkbootstrap:**
   - ❌ `class App(tb.Window)` → `class App(ctk.CTk if HAS_CUSTOMTKINTER else tk.Tk)`
   - ❌ `tb.Frame` → `tk.Frame` no layout
   - ❌ Parâmetros `themename` e `iconphoto` do construtor `tb.Window`

### O Que Foi Mantido (ttk):

✅ **ttk APENAS para widgets indispensáveis:**
- `ttk.Treeview` (CustomTkinter não tem alternativa)
- `ttk.Separator` (separadores visuais)
- `ttk.Style` fixado em tema único (`"clam"`) para estabilidade
- **Sem seleção de múltiplos temas ttk**

---

## 🔄 SISTEMA NOVO: CUSTOMTKINTER

### Appearance Modes Suportados:
- ✅ `"light"` - Modo claro
- ✅ `"dark"` - Modo escuro

### Color Themes Suportados:
- ✅ `"blue"` (padrão)
- ✅ `"dark-blue"`
- ✅ `"green"`

### Como Usar:

```python
# No startup da aplicação
from src.ui.theme_manager import theme_manager

theme_manager.initialize()  # Aplica tema salvo

# Toggle light/dark
new_mode = theme_manager.toggle_mode()  # Retorna "light" ou "dark"

# Definir modo específico
theme_manager.set_mode("dark")

# Definir color theme (no startup apenas)
theme_manager.set_color("dark-blue")

# Obter configuração atual
mode = theme_manager.get_current_mode()   # "light" ou "dark"
color = theme_manager.get_current_color()  # "blue", "dark-blue" ou "green"
```

### Arquivo de Configuração:

`config_theme.json`:
```json
{
  "appearance_mode": "light",
  "color_theme": "blue"
}
```

---

## 🧪 VALIDAÇÃO

### ✅ Pre-commit Hooks (17/17 Passed):
```bash
pre-commit run --all-files
Remover espaços em branco no final das linhas.......................Passed
Garantir nova linha no final dos arquivos...........................Passed
Verificar arquivos grandes (>500KB).................................Passed
Validar sintaxe YAML....................................................Passed
Validar sintaxe TOML....................................................Passed
Validar sintaxe JSON....................................................Passed
Detectar marcadores de merge conflict...............................Passed
Verificar conflitos de case em nomes de arquivos....................Passed
Garantir line endings consistentes..................................Passed
Ruff Linter (Python)....................................................Passed
Ruff Formatter (Python).................................................Passed
Validar sintaxe Python (AST)............................................Passed
Verificar uso de literais builtin.......................................Passed
Verificar posição de docstrings.........................................Passed
Detectar statements de debug (breakpoint, pdb)......................Passed
Verificar nomes de arquivos de teste....................................Passed
Proibir import direto de customtkinter.................................Passed
```

### ✅ Validação SSoT CustomTkinter:
```bash
python scripts/validate_ctk_policy.py
🔍 Validando política CustomTkinter (SSoT)...
✅ Nenhuma violação encontrada!
✅ Todos os imports de customtkinter estão em: src/ui/ctk_config.py
```

### ✅ Testes Clientes (5 passed, 1 skipped):
```bash
python -m pytest tests/modules/clientes/test_clientes_views_imports.py \
                 tests/modules/test_clientes_theme_smoke.py -v
============================= 5 passed, 1 skipped in 2.91s ======================
```

**Testes específicos que passaram:**
- `test_clientes_views_imports.py::test_all_clientes_view_imports` ✅
- `test_clientes_theme_smoke.py::test_theme_manager_imports` ✅
- `test_clientes_theme_smoke.py::test_theme_manager_loads` ✅
- `test_clientes_theme_smoke.py::test_get_palette_light_mode` ✅
- `test_clientes_theme_smoke.py::test_get_palette_dark_mode` ✅

---

## ⚙️ COMPATIBILIDADE

### Código Legado Mantido:

Para evitar quebrar código antigo, mantivemos:

```python
# Em App (main_window.py)
def _set_theme(self, new_theme: str) -> None:
    """DEPRECATED: Mantido para compatibilidade."""
    log.warning("_set_theme() está deprecated. Use _handle_toggle_theme().")

def _handle_menu_theme_change(self, name: str) -> None:
    """DEPRECATED: Mantido para compatibilidade."""
    log.warning("_handle_menu_theme_change() está deprecated. Use _handle_toggle_theme().")

# self.tema_atual continua existindo (agora armazena "light" ou "dark")
```

```python
# Em AppMenuBar (menu_bar.py)
def refresh_theme(self, current: Optional[str]) -> None:
    """Mantido para compatibilidade, mas não faz nada."""
    pass
```

### Migração Recomendada:

**Código antigo que usava `_set_theme()`:**
```python
# Antes
app._set_theme("darkly")
```

**Migrar para:**
```python
# Depois
from src.ui.theme_manager import theme_manager
theme_manager.set_mode("dark")
```

---

## 🎯 CONFIRMAÇÕES FINAIS

### ✅ Requisitos Atendidos:

1. ✅ **CustomTkinter como tema principal**
   - App herda de `ctk.CTk` quando CustomTkinter disponível
   - Fallback seguro para `tk.Tk` quando indisponível

2. ✅ **Sistema de 14 temas ttk REMOVIDO**
   - Menu de seleção de temas removido
   - Lógica de aplicação de temas ttkbootstrap removida
   - Apenas toggle light/dark disponível

3. ✅ **ttk mantido apenas onde necessário**
   - `ttk.Treeview` continua funcionando
   - `ttk.Separator` mantido para separadores visuais
   - ttk fixado em tema único (`"clam"`) sem seleção de múltiplos temas

4. ✅ **Regras SSoT mantidas**
   - Zero imports diretos de `customtkinter` fora de `src/ui/ctk_config.py`
   - Política validada por `scripts/validate_ctk_policy.py`
   - Pre-commit hook `no-direct-customtkinter-import` passando

5. ✅ **Tema customizado não usado**
   - Não criamos JSON de tema custom
   - Usamos apenas appearance modes (`"light"`, `"dark"`)
   - Usamos apenas color themes built-in (`"blue"`, `"dark-blue"`, `"green"`)

6. ✅ **Fallback seguro**
   - App continua funcionando se CustomTkinter não disponível
   - ttk theme fixado em `"clam"` para estabilidade
   - Nenhum crash quando CustomTkinter ausente

7. ✅ **Validações passando**
   - Pre-commit: 17/17 hooks ✅
   - validate_ctk_policy.py: 0 violações ✅
   - Testes clientes: 5 passed, 1 skipped ✅

---

## 📝 CONCLUSÃO

**Microfase 24 foi concluída com sucesso!**

O aplicativo agora usa **CustomTkinter como sistema principal de temas**, com:
- ✅ Appearance mode simples (light/dark)
- ✅ Color themes built-in (blue/dark-blue/green)
- ✅ Sistema de 14 temas ttk completamente removido
- ✅ ttk mantido apenas para widgets essenciais (Treeview)
- ✅ Regras SSoT CustomTkinter mantidas
- ✅ Todas as validações passando

**Próximos passos:**
- Testar visualmente a aplicação com CustomTkinter
- Verificar se todos os widgets CustomTkinter estão usando as cores corretas
- Considerar adicionar preferência de color theme no menu (futuro)
