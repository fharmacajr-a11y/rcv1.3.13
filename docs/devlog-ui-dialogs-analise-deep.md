# UI-DIALOGS-ANALISE-DEEP: Análise Profunda com Logs de Runtime

**Microfase**: UI-DIALOGS-ANALISE-DEEP  
**Tipo**: Análise (instrumentação temporária para debug)  
**Data**: 02/12/2025  
**Versão**: v1.3.44

---

## 📋 Objetivo

Instrumentar `ChatGPTWindow` e `ClientForm` com logs de debug para coletar evidências em runtime sobre:
- Qual é o `master` (parent) real de cada janela
- Tamanho e posição antes e depois de `show_centered()`
- Se `center_on_parent()` ou `center_on_screen()` está sendo usado
- Se o tamanho/posição muda após a janela ser exibida

**Regras**:
- ✅ Apenas instrumentação (logs temporários)
- ❌ Sem alterar lógica de negócio
- ❌ Sem refatoração nesta fase

---

## 🔍 Análise Estática (Reconfirmação)

### ChatGPTWindow (`src/modules/chatgpt/views/chatgpt_window.py`)

**Assinatura**:
```python
class ChatGPTWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        send_fn: Callable[[list[dict[str, str]]], str] | None = None,
        on_close_callback: Callable[[], None] | None = None,
    ) -> None:
```

**Construção e Centralização**:
```python
# Linha 23-26: Obtém toplevel do parent
try:
    master = parent.winfo_toplevel()
except Exception:
    master = parent
super().__init__(master)

# Linha 50-54: Build UI
self._build_ui()
self._build_custom_header()

# Linha 56-57: Define tamanho e centraliza
width = 700
height = 500
self.minsize(width, height)
show_centered(self)
```

**Observações**:
- ✅ Usa `parent.winfo_toplevel()` para obter janela principal
- ✅ Usa `minsize()` ao invés de `geometry()`
- ✅ Chama `show_centered()` após toda configuração UI
- ⚠️ **Possível problema**: UI é construída antes, tamanho pode mudar após pack/grid

---

### ClientForm (`src/modules/clientes/forms/client_form.py`)

**Assinatura**:
```python
def form_cliente(self: tk.Misc, row: ClientRow | None = None, preset: FormPreset | None = None) -> None:
```

**Construção e Centralização**:
```python
# Linha 132-136: Obtém toplevel do parent
try:
    parent_window: tk.Misc = self.winfo_toplevel()  # type: ignore[assignment]
except Exception:
    parent_window = self

# Linha 137-145: Cria Toplevel
win = tk.Toplevel(parent_window)
apply_rc_icon(win)
win.withdraw()
try:
    win.transient(parent_window)
except Exception:
    win.transient(self)
win.resizable(False, False)
win.minsize(940, 520)

# Linha 147-730: Construção massiva de UI (600+ linhas)
main_frame = ttk.Frame(win, padding=(8, 8, 8, 2))
# ... muitos widgets ...

# Linha 738: Centraliza e mostra
show_centered(win)
_update_title()
win.grab_set()
win.focus_force()
```

**Observações**:
- ✅ Usa `self.winfo_toplevel()` para obter janela principal
- ✅ Usa `withdraw()` antes de construir UI (bom pattern)
- ✅ Usa `minsize()` ao invés de `geometry()`
- ✅ Chama `show_centered()` após toda configuração UI
- ⚠️ **Possível problema**: 600+ linhas de widgets, tamanho calculado pode demorar

---

### Chamadas no Main Window

**ChatGPT** (`src/modules/main_window/views/main_window.py` linha 912-928):
```python
def open_chatgpt_window(self) -> None:
    # ...
    try:
        parent_window = self.winfo_toplevel()
    except Exception:
        parent_window = self
    window = ChatGPTWindow(parent_window, on_close_callback=self._on_chatgpt_close)
```

**ClientForm** (chamado via `form_cliente(self, ...)`):
- `self` é a instância de `App` (main_window)
- Dentro de `form_cliente`, faz `self.winfo_toplevel()` novamente

---

## 🛠️ Instrumentação Implementada

### 1. `window_utils.py`

**Adicionado**:
```python
import logging

log = logging.getLogger(__name__)
```

**Logs em `center_on_parent()`**:
```python
if parent is None:
    log.debug("CENTER DEBUG: %r has no parent -> fallback screen", window)
    return False

if not callable(winfo_ismapped) or not winfo_ismapped():
    log.debug(
        "CENTER DEBUG: parent %r not mapped (%r) -> fallback screen",
        parent,
        winfo_ismapped,
    )
    return False

log.debug(
    "CENTER DEBUG (parent): win=%r parent=%r "
    "parent_size=(%s,%s) parent_pos=(%s,%s) "
    "win_size=(%s,%s) -> pos=(%s,%s)",
    window, parent, pw, ph, px, py, ww, wh, x, y,
)
```

**Logs em `center_on_screen()`**:
```python
log.debug(
    "CENTER DEBUG (screen): win=%r screen_size=(%s,%s) win_size=(%s,%s) -> pos=(%s,%s)",
    window, sw, sh, ww, wh, x, y,
)
```

**Logs em `show_centered()`**:
```python
if not center_on_parent(window):
    log.debug("CENTER DEBUG: fallback to screen for %r", window)
    center_on_screen(window)

if callable(withdraw) and callable(deiconify):
    log.debug("CENTER DEBUG: withdraw+center+deiconify for %r", window)
else:
    log.debug("CENTER DEBUG: center only for %r", window)
```

---

### 2. `chatgpt_window.py`

**Adicionado antes de `show_centered()`**:
```python
log.debug(
    "CHATGPT DEBUG: before show_centered -> "
    "master=%r size=(%s,%s) pos=(%s,%s)",
    self.master,
    self.winfo_width(),
    self.winfo_height(),
    self.winfo_rootx() if self.winfo_ismapped() else None,
    self.winfo_rooty() if self.winfo_ismapped() else None,
)
show_centered(self)
self.after(
    200,
    lambda: log.debug(
        "CHATGPT DEBUG: after 200ms -> size=(%s,%s) pos=(%s,%s)",
        self.winfo_width(),
        self.winfo_height(),
        self.winfo_rootx(),
        self.winfo_rooty(),
    ),
)
```

---

### 3. `client_form.py`

**Adicionado antes de `show_centered()`**:
```python
logger.debug(
    "CLIENTFORM DEBUG: before show_centered -> master=%r size=(%s,%s)",
    win.master,
    win.winfo_width(),
    win.winfo_height(),
)
show_centered(win)
win.after(
    200,
    lambda: logger.debug(
        "CLIENTFORM DEBUG: after 200ms -> size=(%s,%s) pos=(%s,%s)",
        win.winfo_width(),
        win.winfo_height(),
        win.winfo_rootx(),
        win.winfo_rooty(),
    ),
)
```

---

## 📊 Como Coletar Logs

### Configuração de Logging (ATUALIZADO - 02/12/2025)

**Problema identificado e corrigido**: O sistema tinha **dois lugares** configurando logging, causando conflito:
- `src/core/logger.py` - Lia `RC_LOG_LEVEL` corretamente
- `src/core/bootstrap.py` - **Sobrescrevia** com nível fixo `INFO`

**Correção aplicada**:
- `bootstrap.py` agora respeita `RC_LOG_LEVEL`
- Adicionado log de startup mostrando nível ativo
- Formato padronizado: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`

### Passo 0: Configurar nível DEBUG

**Windows PowerShell**:
```powershell
$env:RC_LOG_LEVEL = "DEBUG"
python -m src.app_gui
```

**Linux/Mac**:
```bash
RC_LOG_LEVEL=DEBUG python -m src.app_gui
```

**Confirmar no startup**: Você deve ver esta linha no início:
```
INFO | startup | Logging level ativo: DEBUG
```

### Passo 1: Rodar o app

```powershell
(.venv) python -m src.app_gui
```

### Passo 2: Roteiro de testes

1. **Login** no sistema
2. **Abrir Novo Cliente** → Fechar
3. **Abrir Editar Cliente** (qualquer cliente) → Fechar
4. **Abrir ChatGPT** → Fechar
5. **Repetir** se necessário para ver padrões

### Passo 3: Filtrar logs

Procurar no console/arquivo de log por linhas contendo:
- `CENTER DEBUG`
- `CHATGPT DEBUG`
- `CLIENTFORM DEBUG`

### Passo 4: Colar logs neste arquivo

Na seção **"Logs Coletados"** abaixo.

---

## 🔬 O que Analisar nos Logs

### Para ChatGPT:
1. **master**: Deve ser `.!app` ou similar (toplevel da main window)
2. **size antes**: `winfo_width/height` - pode ser 1x1 se UI ainda não calculou
3. **center_on_parent vs center_on_screen**: Qual foi usado?
4. **size depois (200ms)**: Mudou? Se sim, posição ficou desatualizada?
5. **pos depois (200ms)**: Está centralizado ou no canto?

### Para ClientForm:
1. **master**: Deve ser `.!app` ou similar (toplevel da main window)
2. **size antes**: Deve ser ~940x520 ou maior (por causa dos widgets)
3. **center_on_parent vs center_on_screen**: Qual foi usado?
4. **size depois (200ms)**: Mudou? Se sim, posição ficou desatualizada?
5. **pos depois (200ms)**: Está centralizado ou no canto?

### Questões-chave:
- ✅ **Se `center_on_parent` for usado**: Parent está mapeado? Tamanho correto?
- ❌ **Se `center_on_screen` for usado**: Por quê? Parent não mapeado? Parent é None?
- ⚠️ **Se tamanho mudar após 200ms**: Precisa `after(0, show_centered)` ou `after(100, geometry)`?

---

## 🔧 Correção de Logging (02/12/2025)

### Problema Encontrado

Os logs `DEBUG` não apareciam mesmo usando `$env:RC_LOG_LEVEL = "DEBUG"` porque:

1. **Conflito de configuração**: Dois lugares configuravam logging:
   - `src/core/logger.py`: Lia `RC_LOG_LEVEL` ✅
   - `src/core/bootstrap.py`: Sobrescrevia com nível fixo `INFO` ❌

2. **Ordem de execução**: `bootstrap.configure_logging()` executava depois e anulava a configuração correta

### Solução Implementada

**Arquivo modificado**: `src/core/bootstrap.py`

**Mudanças**:
```python
# ANTES (linha 38-41):
logging.basicConfig(
    level=logging.INFO,  # ❌ Fixo em INFO
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# DEPOIS:
import os
_level_name = os.getenv("RC_LOG_LEVEL", "INFO").upper()
_level_val = getattr(logging, _level_name, logging.INFO)

if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=_level_val,  # ✅ Usa RC_LOG_LEVEL
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
else:
    logging.getLogger().setLevel(_level_val)

# ADICIONADO: Log informativo no startup
logger.info("Logging level ativo: %s", logging.getLevelName(logging.getLogger().level))
```

### Resultados

- ✅ `RC_LOG_LEVEL=DEBUG` agora funciona corretamente
- ✅ Nível padrão permanece `INFO` (comportamento normal)
- ✅ Log de startup mostra nível ativo para confirmação
- ✅ Formato padronizado em todo o app
- ✅ Sem quebra de funcionalidade

### Como Usar

**Windows PowerShell**:
```powershell
$env:RC_LOG_LEVEL = "DEBUG"
python -m src.app_gui
```

**Voltar ao normal**:
```powershell
Remove-Item Env:\RC_LOG_LEVEL
python -m src.app_gui
```

### Verificação

Ao rodar com `DEBUG`, você verá no console:
```
INFO | startup | Logging level ativo: DEBUG
DEBUG | window_utils | CENTER DEBUG: ...
DEBUG | chatgpt_window | CHATGPT DEBUG: ...
DEBUG | clientes.forms.client_form | CLIENTFORM DEBUG: ...
```

---

## 📝 Logs Coletados

### Instruções:
Cole aqui as linhas do console que começam com:
- `CENTER DEBUG`
- `CHATGPT DEBUG`
- `CLIENTFORM DEBUG`

**Formato esperado**:
```text
DEBUG | window_utils | CENTER DEBUG: withdraw+center+deiconify for .!toplevel
DEBUG | window_utils | CENTER DEBUG (parent): win=.!toplevel parent=.!app parent_size=(1920,1080) parent_pos=(0,0) win_size=(700,500) -> pos=(610,290)
DEBUG | chatgpt_window | CHATGPT DEBUG: before show_centered -> master=.!app size=(1,1) pos=(None,None)
DEBUG | chatgpt_window | CHATGPT DEBUG: after 200ms -> size=(700,500) pos=(610,290)
```

---

### Logs - Sessão 1 (Novo Cliente)

```text
[AGUARDANDO COLETA]
```

---

### Logs - Sessão 2 (Editar Cliente)

```text
[AGUARDANDO COLETA]
```

---

### Logs - Sessão 3 (ChatGPT)

```text
[AGUARDANDO COLETA]
```

---

## ✅ QA

### Pyright
```
✅ 0 errors, 0 warnings, 0 informations
```

### Ruff
```
✅ All checks passed!
```

---

## 🎯 Próximos Passos

1. **Rodar o app** e coletar logs conforme roteiro acima
2. **Colar logs** na seção "Logs Coletados"
3. **Analisar evidências**:
   - Por que ChatGPT pode não centralizar?
   - Por que ClientForm pode não centralizar?
   - Tamanho muda após show? Precisa `after(0, show_centered)`?
   - Parent está correto? Está mapeado?

4. **Enviar este relatório** para análise
5. **Aguardar microfase UI-DIALOGS-FIX-XXX** com correções baseadas em evidências

---

## 📌 Localização dos Logs

### Onde os logs aparecem:
- **Console**: Ao rodar `python -m src.app_gui`
- **Arquivo de log**: Se configurado em `logging` (verificar `src/infra/settings.py`)

### Formato de mensagem:
```
DEBUG | <módulo> | <mensagem>
```

### Exemplos de busca no console:
```powershell
# PowerShell
python -m src.app_gui 2>&1 | Select-String "CENTER DEBUG|CHATGPT DEBUG|CLIENTFORM DEBUG"
```

---

**Status**: ✅ Instrumentação completa  
**Aguardando**: Coleta de logs em runtime  
**Arquivos modificados** (temporário):
- `src/ui/window_utils.py`
- `src/modules/chatgpt/views/chatgpt_window.py`
- `src/modules/clientes/forms/client_form.py`
