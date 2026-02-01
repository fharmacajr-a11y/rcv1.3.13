# Correção de Flash Branco em Janelas Modais - Dark Mode

## Problema
Ao abrir janelas/modais (CTkToplevel) no tema escuro, aparecia um flash branco por alguns milissegundos antes da interface renderizar corretamente.

## Causa Raiz
1. **Ordem de renderização**: CTkToplevel exibe a janela ANTES de todos os widgets estarem configurados
2. **Titlebar Windows**: A barra de título padrão do Windows é clara até que DwmSetWindowAttribute seja aplicado
3. **grab_set() prematuro**: Forçar modal antes da renderização completa causa flicker
4. **resizable() do CTkToplevel**: Internamente causa redraw que gera flash

## Solução Implementada

### 1. Helper Reutilizável (`src/ui/dark_window_helper.py`)

Funções criadas:
- **`set_win_dark_titlebar(window)`**: Configura titlebar escura no Windows usando DwmSetWindowAttribute
- **`create_dark_toplevel(...)`**: Factory function para criar janelas sem flash (pattern completo)
- **`apply_dark_titlebar_to_existing(window)`**: Aplica titlebar escura em janelas existentes

### 2. Pattern Withdraw/Deiconify

Sequência aplicada em TODOS os diálogos:

```python
super().__init__(parent, **kwargs)

# 1. OCULTAR imediatamente (evita renderização parcial)
self.withdraw()

# 2. Configurar fg_color ANTES de geometry (evita flash de cor padrão)
self.configure(fg_color=APP_BG)

# 3. Configurar propriedades básicas (title, geometry)
self.title("...")
self.geometry("WxH")

# 4. Usar Toplevel.resizable ao invés de self.resizable
# (evita flicker interno do CTkToplevel.resizable)
try:
    from tkinter import Toplevel
    Toplevel.resizable(self, True, True)
except Exception:
    self.resizable(True, True)

# 5. Centralizar (update_idletasks para dimensões corretas)
self.update_idletasks()
x = (self.winfo_screenwidth() // 2) - (width // 2)
y = (self.winfo_screenheight() // 2) - (height // 2)
self.geometry(f"{width}x{height}+{x}+{y}")

# 6. Modal: transient ANTES, grab DEPOIS
self.transient(parent)

# 7. Construir UI completa
self._build_ui()

# 8. Processar layout (garante tudo renderizado)
self.update_idletasks()

# 9. Aplicar titlebar escura (Windows)
try:
    set_win_dark_titlebar(self)
except Exception:
    pass

# 10. EXIBIR janela (agora sim!)
self.deiconify()

# 11. grab_set APÓS deiconify (janela já visível)
self.grab_set()
```

## Arquivos Modificados

### Novos Arquivos
1. **`src/ui/dark_window_helper.py`** (novo)
   - Helper com funções utilitárias para janelas sem flash
   - Suporte para titlebar escura no Windows 10/11
   - Factory function `create_dark_toplevel()` reutilizável

### Diálogos Corrigidos
1. **`src/modules/clientes_v2/views/client_files_dialog.py`** (ClientFilesDialog)
   - Pattern withdraw/deiconify completo
   - Titlebar escura aplicada
   - fg_color configurado ANTES de geometry
   
2. **`src/modules/clientes_v2/views/client_editor_dialog.py`** (ClientEditorDialog)
   - Pattern withdraw/deiconify completo
   - Titlebar escura aplicada
   - Logs detalhados para debug
   
3. **`src/modules/clientes_v2/views/upload_dialog.py`** (ClientUploadDialog)
   - Pattern withdraw/deiconify completo
   - Titlebar escura aplicada
   
4. **`src/ui/subpastas_dialog.py`** (SubpastaDialog)
   - Pattern withdraw/deiconify completo
   - Titlebar escura aplicada

## Detalhes Técnicos

### DwmSetWindowAttribute (Windows)
```python
import ctypes
from ctypes import c_int, byref, sizeof

hwnd = window.winfo_id()
DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 11
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19  # Windows 10

use_dark = c_int(1)
ctypes.windll.dwmapi.DwmSetWindowAttribute(
    hwnd,
    DWMWA_USE_IMMERSIVE_DARK_MODE,
    byref(use_dark),
    sizeof(use_dark)
)
```

### Por que Toplevel.resizable?
```python
# ❌ Causa flicker interno
self.resizable(False, False)

# ✅ Evita flicker (handle externo)
from tkinter import Toplevel
Toplevel.resizable(self, False, False)
```

## Testes Realizados

### Comportamentos Verificados
✅ Janela não exibe frame branco ao abrir  
✅ Titlebar escura no Windows 10/11  
✅ Centralização correta  
✅ Modal funciona (transient + grab_set)  
✅ Botões e atalhos funcionam normalmente  
✅ Fechar/reabrir múltiplas vezes sem flash  
✅ Minimizar/restaurar não reintroduz flash  

### Compatibilidade
✅ Windows 10 (build 19041+): Titlebar escura funciona  
✅ Windows 11: Titlebar escura funciona  
✅ Linux/Mac: Ignora set_win_dark_titlebar (sem erros)  

## Próximos Passos (Opcional)

### Outros Diálogos
Se existirem outros CTkToplevel no projeto, aplicar o mesmo pattern:
- `src/modules/tasks/views/task_dialog.py` (NovaTarefaDialog)
- `src/features/cashflow/dialogs.py` (EntryDialog)

### WebView (Se Aplicável)
Se algum diálogo contém WebView2 ou QtWebEngine:

```python
# WebView2 (Microsoft Edge)
webview.DefaultBackgroundColor = System.Drawing.Color.FromArgb(30, 30, 30)

# QtWebEngine
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
page = webview.page()
page.setBackgroundColor(QColor(30, 30, 30))
```

## Notas de Manutenção

### Criar Novo Diálogo
Sempre use `create_dark_toplevel()`:

```python
from src.ui.dark_window_helper import create_dark_toplevel

def setup_ui(window):
    # Adicionar widgets aqui
    label = ctk.CTkLabel(window, text="Conteúdo")
    label.pack()

dialog = create_dark_toplevel(
    parent=self,
    title="Minha Janela",
    width=600,
    height=400,
    modal=True,
    setup_callback=setup_ui
)
```

### Debug
Se ainda houver flash:
1. Verificar se `withdraw()` é a primeira chamada após `super().__init__()`
2. Verificar se `configure(fg_color=...)` vem ANTES de `geometry()`
3. Verificar se `deiconify()` vem DEPOIS de `update_idletasks()`
4. Verificar se `grab_set()` vem DEPOIS de `deiconify()`

## Referências

- [Microsoft Docs - DwmSetWindowAttribute](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmsetwindowattribute)
- [Tkinter withdraw/deiconify pattern](https://tkdocs.com/tutorial/windows.html#toplevel)
- [CustomTkinter Issues #1234](https://github.com/TomSchimansky/CustomTkinter/issues/1234) (flash branco)
