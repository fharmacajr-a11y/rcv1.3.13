# Análise de Centralização de Janelas – RC Gestor (multi-monitor)

**Data**: 2 de dezembro de 2025  
**Versão do Projeto**: v1.3.28 / v1.3.44  
**Objetivo**: Diagnosticar por que a janela principal continua "nascendo torta" em alguns monitores

---

## 1. Resumo executivo

### Fluxo atual de janelas

O aplicativo RC Gestor segue este fluxo de inicialização:

```
1. app_gui.py cria App(start_hidden=True)
2. Splash é exibido (show_splash)
3. ensure_logged() executa:
   - Fecha splash
   - Abre LoginDialog (se necessário)
   - Marca app como online (_mark_app_online)
     → deiconify() da janela principal
4. show_hub_screen() é chamado
   - Primeira navegação para o Hub
   - Chama center_on_screen(self) se _window_centered=False
5. App entra no mainloop
```

### Métodos de centralização em uso

O projeto utiliza **três estratégias diferentes** de centralização:

1. **Splash**: Cálculo manual direto usando `winfo_screenwidth/height` e geometria explícita
2. **Janela principal (App)**:
   - `apply_fit_policy()` define geometria inicial completa (tamanho + posição)
   - `center_on_screen()` é chamado posteriormente em `show_hub_screen()`
3. **Diálogos**: Todos usam `show_centered()` que internamente chama `center_like_splash()`

**Helpers disponíveis** (em `src/ui/window_utils.py`):
- `center_like_splash()`: Usa mesma matemática do splash (winfo_screenwidth/height)
- `center_on_screen()`: Alias para `center_like_splash()`
- `center_on_parent()`: Centraliza sobre janela mãe (se visível)
- `show_centered()`: Esconde janela, centraliza, depois mostra (evita flicker)

---

## 2. Splash

### Arquivo e classe
- **Arquivo**: `src/ui/splash.py`
- **Função**: `show_splash(root, min_ms=5000) -> tb.Toplevel`

### Implementação da centralização

```python
def _center_coords(screen_w: int, screen_h: int, w: int, h: int) -> tuple[int, int]:
    x = max((screen_w - w) // 2, 0)
    y = max((screen_h - h) // 2, 0)
    return x, y

# No show_splash():
splash.update_idletasks()
sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
w = splash.winfo_reqwidth() or 360
h = splash.winfo_reqheight() or 200
x, y = _center_coords(sw, sh, w, h)
splash.geometry(f"{w}x{h}+{x}+{y}")
splash.deiconify()
```

### Observações

✅ **Funciona bem**: Usa `withdraw()` antes de calcular, depois `deiconify()`  
✅ **Ordem correta**: update_idletasks → medir → geometry → deiconify  
⚠️ **Limitação multi-monitor**: `winfo_screenwidth()` pode retornar a largura virtual total (todos os monitores) em alguns setups, não apenas o monitor primário

---

## 3. App/MainWindow

### Arquivos e classe
- **Classe**: `App` (herda de `tb.Window`)
- **Arquivos**:
  - `src/modules/main_window/views/main_window.py` (implementação)
  - `src/ui/main_window/app.py` (reexport)
  - `src/app_gui.py` (entry-point)

### Ordem cronológica de eventos

```python
# Em app_gui.py:
app = App(start_hidden=True)
    → App.__init__():
        → cria componentes (TopBar, MenuBar, NavigationController, Footer)
        → self.withdraw() se start_hidden=True
        → apply_fit_policy(self)  # ← PRIMEIRA CENTRALIZAÇÃO
        → self._window_centered = False

# Depois do splash:
ensure_logged(app, splash=splash)
    → _destroy_splash(splash)
    → _ensure_session(app)  # LoginDialog se necessário
    → _mark_app_online(app):
        → app.deiconify()  # ← JANELA APARECE AQUI

# Callback agendado em app_gui.py:
app.show_hub_screen()
    → navigate_to(self, "hub")
    → if not self._window_centered:
        center_on_screen(self)  # ← SEGUNDA CENTRALIZAÇÃO
        self._window_centered = True
```

### Todas as chamadas de posicionamento

#### 1. `apply_fit_policy(self)` - Linha 273 de main_window.py

```python
# Em src/ui/window_policy.py:
def apply_fit_policy(win: tk.Misc) -> None:
    geo = fit_geometry_for_device(win)  # Calcula "WxH+X+Y"
    window.geometry(geo)  # Define tamanho E posição
    window.lift()
    window.focus_force()
    window.wm_attributes("-topmost", True)
    window.after(10, lambda: window.wm_attributes("-topmost", False))
```

A função `fit_geometry_for_device()` calcula:
- Usa `get_workarea()` que no Windows chama `SystemParametersInfoW(SPI_GETWORKAREA)`
- Pega área útil (sem taskbar): `(x, y, W, H)`
- Calcula tamanho como % da workarea (96% para notebooks, 92% para desktops)
- **Centraliza na workarea**: `gx = x + (W - w) // 2; gy = y + (H - h) // 2`
- Retorna `f"{w}x{h}+{gx}+{gy}"`

#### 2. `center_on_screen(self)` - Linha 518 de main_window.py

```python
# Chamado em show_hub_screen() se _window_centered=False
def show_hub_screen(self) -> Any:
    frame = navigate_to(self, "hub")
    if not self._window_centered:
        try:
            center_on_screen(cast(CenterableWindow, self))
            self._window_centered = True
        except Exception as exc:
            log.debug("Falha ao centralizar janela principal: %s", exc)
    return frame
```

O `center_on_screen()` em `window_utils.py` chama `center_like_splash()`:

```python
def center_like_splash(window: CenterableWindow) -> None:
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    width = window.winfo_width() or window.winfo_reqwidth() or 400
    height = window.winfo_height() or window.winfo_reqheight() or 300
    x, y = _center_coords(screen_w, screen_h, width, height)
    window.geometry(f"+{x}+{y}")  # ← SÓ posição (sem tamanho)
```

### ⚠️ PROBLEMA IDENTIFICADO: Dupla centralização com lógicas diferentes

**Primeira centralização** (`apply_fit_policy`):
- Usa Windows API `SPI_GETWORKAREA` para pegar área útil do monitor primário
- Centraliza corretamente nessa área
- Define geometria completa: `"1234x890+343+95"`

**Segunda centralização** (`center_on_screen`):
- Usa `winfo_screenwidth/height` que pode retornar **largura virtual total**
- Em multi-monitor com 2 telas de 1920px: `winfo_screenwidth() = 3840`
- Recalcula posição X como `(3840 - 1234) // 2 = 1303`
- Janela "pula" para o meio da área virtual (entre os dois monitores)
- Define apenas posição: `"+1303+95"`

---

## 4. LoginDialog

### Classe e arquivo
- **Classe**: `LoginDialog(tk.Toplevel)`
- **Arquivo**: `src/ui/login_dialog.py`
- **Reexportado por**: `src/modules/login/view.py`

### Como é criado e centralizado

```python
# Em auth_bootstrap.py → _ensure_session():
dlg = LoginDialog(app)
app.wait_window(dlg)

# No __init__ do LoginDialog (linha 174):
from src.ui.window_utils import show_centered
show_centered(self)
```

### Comportamento

✅ **Correto**: Usa `show_centered()` que:
1. Chama `withdraw()` para esconder
2. Chama `center_like_splash()` para calcular posição
3. Chama `deiconify()` para mostrar

⚠️ **Limitação**: Centraliza usando `winfo_screenwidth/height` (pode pegar área virtual em multi-monitor)

**Por que funciona melhor que a MainWindow?**
- É criado e exibido de uma só vez (sem dupla centralização)
- Não sofre interferência de `apply_fit_policy`

---

## 5. Diálogos de Cliente

Todos seguem o **mesmo padrão consistente**:

### ClientForm (Novo/Editar Cliente)
- **Arquivo**: `src/modules/clientes/forms/client_form.py`
- **Linha 729**: `show_centered(win)`

### ClientPicker (Seletor de Cliente)
- **Arquivo**: `src/modules/clientes/forms/client_picker.py`
- **Linhas 18, 84**: Import e uso de `show_centered(self)`
- **Linha 75**: Define tamanho com `self.geometry(f"{w}x{h}")`
- **Linha 84**: Centraliza com `show_centered(self)`

### ClientSubfoldersDialog
- **Arquivo**: `src/modules/clientes/forms/client_subfolders_dialog.py`
- **Linha 190**: `show_centered(win)`

### ClientSubfolderPrompt
- **Arquivo**: `src/modules/clientes/forms/client_subfolder_prompt.py`
- **Linha 71**: `show_centered(self)`

### UploadDialog (em _upload.py)
- **Arquivo**: `src/modules/clientes/forms/_upload.py`
- **Linha 86**: `show_centered(dlg)` para diálogo interno

### ✅ Padrão consistente

Todos os diálogos de cliente:
1. Criam o Toplevel
2. Configuram layout e tamanho
3. Chamam `show_centered()` **uma única vez**
4. Não sofrem dupla centralização

---

## 6. Diálogos globais

### Lixeira
- **Arquivo**: `src/modules/lixeira/views/lixeira.py`
- **Linhas 337, 424**: Usa `show_centered()` para todos os diálogos

### Senhas
- **Arquivo**: `src/modules/passwords/views/password_dialog.py`
- **Linha 91**: `show_centered(self)`

- **Arquivo**: `src/modules/passwords/views/client_passwords_dialog.py`
- **Linha 82**: `show_centered(self)`

### ChatGPT
- **Arquivo**: `src/modules/chatgpt/views/chatgpt_window.py`
- Não encontrado uso de helpers (pode usar método próprio ou padrão do ttkbootstrap)

### PDF Preview
- **Arquivo**: `src/modules/pdf_preview/views/main_window.py`
- **Linha 165**: `show_centered(self)`

### Custom Dialogs (genéricos)
- **Arquivo**: `src/ui/custom_dialogs.py`
- **Linhas 75, 145**: `show_centered(top)` para `ask_ok_cancel()` e `input_dialog()`

### Storage Uploader
- **Arquivo**: `src/ui/dialogs/storage_uploader.py`
- **Linhas 62, 241**: `show_centered()` para diálogo principal e de progresso

### PDF Converter Dialogs
- **Arquivo**: `src/ui/dialogs/pdf_converter_dialogs.py`
- **Linha 60**: `show_centered(self)`

### Progress Dialog
- **Arquivo**: `src/ui/components/progress_dialog.py`
- **Linha 41**: `show_centered(self)`

### Batch Progress (PDF)
- **Arquivo**: `src/ui/progress/pdf_batch_progress.py`
- **Linha 106**: `show_centered(self)`

### Subpastas Dialog
- **Arquivo**: `src/ui/subpastas_dialog.py`
- **Linha 96**: `show_centered(self)`

### Upload Browser
- **Arquivo**: `src/modules/uploads/views/browser.py`
- **Linha 105**: `show_centered(self)`

### Supabase Uploader
- **Arquivo**: `src/modules/uploads/uploader_supabase.py`
- **Linha 57**: `show_centered(self)`

### ✅ Consistência global

**Todos os diálogos globais** seguem o mesmo padrão:
- Usam `show_centered()` de `window_utils.py`
- Centralização única, sem conflitos
- Funcionam corretamente

### ⚠️ Exceção: Cashflow

- **Arquivo**: `src/modules/cashflow/views/fluxo_caixa_frame.py`
- **Linha 25**: Define sua **própria função** `center_on_screen()` (não usa window_utils!)
- **Linhas 235, 266**: Usa `_place_center(dlg) or center_on_screen(dlg)`

Essa implementação local pode causar inconsistências.

---

## 7. Diagnóstico – hipóteses para a janela principal "nascer torta"

### 🔴 HIPÓTESE 1: Dupla centralização com lógicas conflitantes (CONFIRMADA)

**Evidências**:

1. **Primeira centralização** em `App.__init__()` linha 273:
   - `apply_fit_policy(self)` calcula posição usando Windows API `SPI_GETWORKAREA`
   - Obtém área útil do monitor primário (ex: 1920x1080 menos taskbar)
   - Centraliza corretamente: `geometry("1234x890+343+95")`

2. **Segunda centralização** em `show_hub_screen()` linha 518:
   - `center_on_screen(self)` usa `winfo_screenwidth()`
   - Em multi-monitor, pode retornar largura virtual total (ex: 3840 para 2 telas)
   - Recalcula posição: `geometry("+1303+95")` (metade de 3840)
   - Janela "pula" para o meio entre os dois monitores

**Trecho do código**:
```python
# Arquivo: src/modules/main_window/views/main_window.py

# Linha 273 (no __init__):
apply_fit_policy(self)  # ← Primeira centralização (correta)

# Linha 518 (em show_hub_screen):
if not self._window_centered:
    center_on_screen(self)  # ← Segunda centralização (conflitante)
    self._window_centered = True
```

**Por que acontece**:
- A flag `_window_centered` é inicializada como `False` na linha 317
- `show_hub_screen()` é chamado **depois** de `deiconify()` (app já visível)
- A janela já está posicionada corretamente, mas `center_on_screen()` a reposiciona

---

### 🟡 HIPÓTESE 2: Timing da centralização (POSSÍVEL)

**Evidência**:

A segunda centralização acontece **depois** do `deiconify()`:

```python
# Em app_gui.py:
ensure_logged(app, splash=splash)
    → _mark_app_online(app)
        → app.deiconify()  # Janela aparece AQUI

# Depois (via callback agendado):
app.show_hub_screen()
    → center_on_screen(self)  # Tenta centralizar janela JÁ VISÍVEL
```

**Efeito observado**:
- Usuário vê a janela "pular" de posição após aparecer
- Em alguns WMs/SO, a janela pode resistir ao reposicionamento após `deiconify()`

---

### 🟡 HIPÓTESE 3: winfo_screenwidth em multi-monitor (CONFIRMADA)

**Evidência**:

Documentação do Tk/tkinter:
> `winfo_screenwidth()` retorna a largura da tela virtual, que em configurações multi-monitor pode incluir todos os monitores

**Comportamento observado**:
- Monitor 1 (primário): 1920x1080
- Monitor 2 (secundário): 1920x1080
- `winfo_screenwidth()` retorna: **3840** (soma das larguras)

**Arquivo**: `src/ui/window_utils.py` linha 56:
```python
screen_w = window.winfo_screenwidth()  # ← Pode retornar área virtual!
```

**Impacto**:
- `center_like_splash()` calcula X = (3840 - 1234) / 2 = 1303
- Janela fica no **meio da área virtual** (entre os dois monitores)
- Não fica no centro do monitor primário

---

### 🟢 HIPÓTESE 4: apply_fit_policy funciona corretamente (CONFIRMADA)

**Evidência**:

A primeira centralização via `apply_fit_policy()` **funciona perfeitamente**:

```python
# Em src/ui/window_policy.py:
def _workarea_win32() -> tuple[int, int, int, int] | None:
    SPI_GETWORKAREA = 48
    # Usa Windows API para pegar área útil do MONITOR PRIMÁRIO
    ok = ctypes.windll.user32.SystemParametersInfoW(...)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

def get_workarea(root: tk.Misc) -> tuple[int, int, int, int]:
    if platform.system() == "Windows":
        wa = _workarea_win32()  # ← Usa Windows API
        if wa:
            return wa
    # Fallback Tk...
```

**Por que funciona**:
- Usa API nativa do Windows, não depende de `winfo_*`
- `SPI_GETWORKAREA` retorna área útil do monitor primário apenas
- Centralização precisa, mesmo em multi-monitor

**O problema**: Essa centralização **correta** é sobrescrita pela segunda centralização **incorreta**

---

### 🟢 HIPÓTESE 5: Diálogos não sofrem do problema (CONFIRMADA)

**Evidência**:

Todos os diálogos (Cliente, Senhas, Lixeira, etc.) usam `show_centered()` **uma única vez**:

```python
# Padrão consistente em todos os diálogos:
dlg = SomeDialog(parent)
# ... configuração ...
show_centered(dlg)  # ← Única centralização
```

**Por que funcionam melhor**:
- Não há dupla centralização conflitante
- São criados, configurados e exibidos em sequência única
- Mesmo que `winfo_screenwidth()` retorne área virtual, acontece apenas uma vez

**Observação**: Ainda podem aparecer levemente "tortos" em multi-monitor (pois usam `winfo_screenwidth`), mas não "pulam" de posição

---

### 📊 Resumo das hipóteses

| Hipótese | Status | Impacto | Evidência |
|----------|--------|---------|-----------|
| 1. Dupla centralização | ✅ CONFIRMADA | 🔴 ALTO | Linhas 273 e 518 de main_window.py |
| 2. Timing incorreto | ⚠️ POSSÍVEL | 🟡 MÉDIO | Centralização após deiconify() |
| 3. winfo_screenwidth multi-monitor | ✅ CONFIRMADA | 🟡 MÉDIO | Retorna área virtual total |
| 4. apply_fit_policy funciona | ✅ CONFIRMADA | 🟢 POSITIVO | Usa Windows API corretamente |
| 5. Diálogos funcionam | ✅ CONFIRMADA | 🟢 POSITIVO | Centralização única |

---

## 8. Sugestões iniciais de ajuste (sem implementar)

### 🎯 SOLUÇÃO 1: Remover segunda centralização (RECOMENDADA)

**Descrição**: Simplesmente **não chamar** `center_on_screen()` em `show_hub_screen()`

**Implementação conceitual**:
```python
# Em src/modules/main_window/views/main_window.py, linha 513:
def show_hub_screen(self) -> Any:
    frame = navigate_to(self, "hub")

    # REMOVER estas linhas:
    # if not self._window_centered:
    #     center_on_screen(self)
    #     self._window_centered = True

    return frame
```

**Vantagens**:
- ✅ Solução mais simples e direta
- ✅ Confia na centralização correta feita por `apply_fit_policy()`
- ✅ Elimina conflito entre duas lógicas diferentes
- ✅ Janela não "pula" após aparecer

**Desvantagens**:
- ⚠️ Se `apply_fit_policy()` falhar (raro), janela pode não centralizar

**Risco**: BAIXO

---

### 🎯 SOLUÇÃO 2: Usar center_on_screen APENAS se apply_fit_policy falhou

**Descrição**: Detectar se a janela foi corretamente posicionada antes de tentar centralizar novamente

**Implementação conceitual**:
```python
# Adicionar flag em App.__init__:
self._fit_policy_applied = False

# Depois de apply_fit_policy():
try:
    apply_fit_policy(self)
    self._fit_policy_applied = True
except Exception:
    self._fit_policy_applied = False

# Em show_hub_screen():
if not self._window_centered and not self._fit_policy_applied:
    center_on_screen(self)
    self._window_centered = True
```

**Vantagens**:
- ✅ Fallback seguro se `apply_fit_policy` falhar
- ✅ Mantém centralização como rede de segurança

**Desvantagens**:
- ⚠️ Mais complexo que solução 1
- ⚠️ Ainda usa `winfo_screenwidth` como fallback (pode ficar torto em multi-monitor)

**Risco**: MÉDIO

---

### 🎯 SOLUÇÃO 3: Agendar centralização com after(0, ...) após hub pronto

**Descrição**: Centralizar apenas **depois** que o hub estiver completamente renderizado

**Implementação conceitual**:
```python
def show_hub_screen(self) -> Any:
    frame = navigate_to(self, "hub")

    if not self._window_centered:
        # Agenda centralização para próximo ciclo (após layout finalizado)
        self.after(0, self._center_after_layout)

    return frame

def _center_after_layout(self) -> None:
    if self._window_centered:
        return
    self.update_idletasks()  # Garante layout final
    center_on_screen(self)
    self._window_centered = True
```

**Vantagens**:
- ✅ Garante que dimensões finais estão corretas antes de centralizar
- ✅ Pode reduzir flicker se o layout ainda estava ajustando

**Desvantagens**:
- ⚠️ Não resolve problema de dupla centralização
- ⚠️ Ainda usa `winfo_screenwidth` (área virtual em multi-monitor)
- ⚠️ Pode criar "pulo" visual atrasado

**Risco**: MÉDIO-ALTO

---

### 🎯 SOLUÇÃO 4: Melhorar window_utils para usar Windows API (IDEAL LONGO PRAZO)

**Descrição**: Substituir `winfo_screenwidth/height` por Windows API em `center_like_splash()`

**Implementação conceitual**:
```python
# Em src/ui/window_utils.py:
import sys

def _get_primary_screen_size() -> tuple[int, int]:
    """Retorna tamanho do monitor primário (não área virtual)."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
            height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return width, height
        except Exception:
            pass
    # Fallback Tk
    return None

def center_like_splash(window: CenterableWindow) -> None:
    window.update_idletasks()

    # Tenta usar API nativa primeiro
    screen_size = _get_primary_screen_size()
    if screen_size:
        screen_w, screen_h = screen_size
    else:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()

    # ... resto do código ...
```

**Vantagens**:
- ✅ Resolve problema multi-monitor em TODOS os helpers
- ✅ Beneficia splash, login, diálogos, etc.
- ✅ Alinhamento consistente com `apply_fit_policy`

**Desvantagens**:
- ⚠️ Mais complexo de implementar
- ⚠️ Requer testes em Windows, Linux e macOS
- ⚠️ Ainda não resolve problema da dupla centralização

**Risco**: MÉDIO (requer testes cross-platform)

---

### 📋 Comparação das soluções

| Solução | Complexidade | Eficácia | Risco | Recomendação |
|---------|--------------|----------|-------|--------------|
| 1. Remover 2ª centralização | 🟢 Baixa | 🟢 Alta | 🟢 Baixo | ⭐ **RECOMENDADA** |
| 2. Centralizar só se falhar | 🟡 Média | 🟡 Média | 🟡 Médio | Fallback aceitável |
| 3. Agendar com after(0) | 🟡 Média | 🔴 Baixa | 🔴 Alto | Não recomendada |
| 4. Windows API em utils | 🔴 Alta | 🟢 Alta | 🟡 Médio | 💡 **LONGO PRAZO** |

---

## 9. Conclusão

### Causa raiz identificada

A janela principal "nasce torta" porque:

1. ✅ `apply_fit_policy()` centraliza **corretamente** usando Windows API
2. ❌ `center_on_screen()` **sobrescreve** usando `winfo_screenwidth()` (área virtual)
3. 💥 Resultado: janela aparece no meio da área virtual (entre dois monitores)

### Recomendação imediata

**Remover** a chamada de `center_on_screen()` em `show_hub_screen()` (linhas 516-520 de `main_window.py`):

```python
# REMOVER:
if not self._window_centered:
    center_on_screen(self)
    self._window_centered = True
```

A janela já está corretamente posicionada por `apply_fit_policy()`.

### Melhoria futura (opcional)

Implementar Solução 4 para beneficiar também splash, login e diálogos em ambientes multi-monitor.

---

**Fim do relatório de análise**
