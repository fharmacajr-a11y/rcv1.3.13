# Relatório: Auditoria de Ícones + Progresso ZIP Real

**Data:** 18 de dezembro de 2025  
**Projeto:** RC Gestor v1.4.52 (Tkinter/ttkbootstrap)  
**Módulos:** Sistema de ícones, Diálogos, Progresso de downloads  

---

## 1. Resumo Executivo

### Objetivo
Descobrir onde o ícone foi sobrescrito e corrigir para que as "caixinhas" (saída do app, download concluído, etc.) usem o ícone do app (.ico) de forma consistente — **sem colocar imagem dentro do corpo do diálogo** — e ajustar a janela de progresso do ZIP para um visual "padrão Windows" com progresso real (bytes/percent).

### Problema Identificado
1. **Ícone PNG no corpo do diálogo**: `Label(image=self._icon_img)` colocando rc.png **DENTRO** do conteúdo do diálogo (não apenas na titlebar)
2. **Progresso ZIP indeterminado**: Barra infinita sem mostrar bytes baixados/total
3. **Inconsistência de ícones**: Múltiplos pontos aplicando iconphoto com PNG em vez de só .ico

---

## 2. Auditoria Completa: Pontos que Sobrescrevem Ícone

### 2.1. PROBLEMA CRÍTICO: Imagem PNG no Corpo do Diálogo

**Arquivo:** `src/modules/uploads/views/browser.py`

#### **Ponto #1: Dialog "Download concluído" - LINHA 252**
```python
# ❌ PROBLEMA: Colocando imagem PNG DENTRO do corpo do diálogo
if self._icon_img:
    icon_label = ttk.Label(frm, image=self._icon_img)
    icon_label.grid(row=0, column=0, padx=(0, 12), sticky="n")
```

**Localização:** Linha 252 no método `_show_download_done_dialog()`

**Impacto:**
- Exibe rc.png como imagem grande dentro do dialog
- Não é ícone de janela (titlebar), é imagem no conteúdo
- Visual não-padrão Windows (messagebox padrão usa apenas ícone de janela)

---

### 2.2. Ícone PNG no Construtor do UploadsBrowserWindow

**Arquivo:** `src/modules/uploads/views/browser.py`

#### **Ponto #2: Inicialização - LINHAS 120, 136-137**
```python
self._icon_img: tk.PhotoImage | None = None

# Carregar ícone PNG para usar em Toplevel (Windows respeita melhor)
try:
    self._icon_img = tk.PhotoImage(file=resource_path("rc.png"))
    self.iconphoto(True, self._icon_img)
except Exception as exc:
    _log.debug("Falha ao aplicar iconphoto no UploadsBrowser: %s", exc)
```

**Problema:**
- Carrega PNG e aplica iconphoto (correto para titlebar)
- MAS depois usa `self._icon_img` em Label (linha 252) - ERRADO

---

### 2.3. Dialog de Download (Aguarde ZIP)

**Arquivo:** `src/modules/uploads/views/browser.py`

#### **Ponto #3: Janela "Aguarde..." - LINHAS 376-378**
```python
try:
    wait.iconbitmap(resource_path("rc.ico"))
    if self._icon_img:
        wait.iconphoto(True, self._icon_img)
except Exception as exc:
    _log.debug("Falha ao definir icone em janela de progresso ZIP: %s", exc)
```

**Status:** ✅ Correto para titlebar (não coloca imagem no corpo)

**Problema adicional:**
- Linhas 392-396: Progressbar em modo `indeterminate` (barra infinita)
- Não mostra bytes baixados nem progresso real

---

### 2.4. Main Window (App)

**Arquivo:** `src/modules/main_window/views/main_window.py`

#### **Ponto #4: Inicialização - LINHA 158**
```python
super().__init__(themename=_theme_name)
```

**Problema:**
- `ttkbootstrap.Window` sem `iconphoto=None` pode aplicar iconphoto padrão
- Contamina dialogs filhos (messageboxes)

#### **Ponto #5: Aplicação de ícone - LINHAS 226-233**
```python
try:
    self.iconbitmap(icon_path)
    log.info("iconbitmap aplicado com sucesso: %s", icon_path)
except Exception:
    log.warning("iconbitmap falhou, tentando iconphoto para %s", icon_path, exc_info=True)
    try:
        img = tk.PhotoImage(file=icon_path)  # icon_path = "rc.ico"
        self.iconphoto(True, img)
```

**Problema:**
- `PhotoImage(file="rc.ico")` não funciona bem no Windows
- Deveria usar rc.png quando fallback for necessário

---

### 2.5. Helpers de Ícone Existentes

#### **Helper #1: `apply_rc_icon()` - src/app_gui.py (LINHAS 30-55)**
```python
try:
    window.iconbitmap(icon_path)
    try:
        window.iconbitmap(default=icon_path)
    except Exception:
        logger.debug("Falha ao configurar ícone como default para messageboxes")
except Exception:
    try:
        img = tk.PhotoImage(file=icon_path)  # icon_path pode ser .ico
        window.iconphoto(True, img)
        window._rc_icon_img = img
    except Exception:
        logger.debug("Falha ao carregar ícone PNG como fallback")
```

**Problema:** Fallback tenta carregar .ico como PhotoImage (falha silenciosa)

#### **Helper #2: `_apply_icon()` - src/ui/custom_dialogs.py (LINHAS 15-31)**
```python
try:
    window.iconbitmap(icon_path)
    return
except Exception:
    try:
        img = tk.PhotoImage(file=icon_path)  # icon_path = "rc.ico"
        window.iconphoto(True, img)
    except Exception as inner_exc:
        logger.debug("Falha ao aplicar iconphoto: %s", inner_exc)
```

**Problema:** Fallback tenta carregar .ico como PhotoImage

#### **Helper #3: `apply_app_icon()` - src/ui/dialogs/pdf_converter_dialogs.py (LINHAS 15-40)**
```python
try:
    window.iconbitmap(icon_path)
    return
except Exception:
    try:
        img = tk.PhotoImage(file=icon_path)  # icon_path = APP_ICON_PATH (.ico)
        window.iconphoto(True, img)
        window._rc_icon_img = img
        return
    except Exception as inner_exc:
        logger.debug("Falha ao aplicar iconphoto no dialogo PDF: %s", inner_exc)
```

**Problema:** Fallback tenta carregar .ico como PhotoImage

---

### 2.6. Messagebox "Deseja sair" (Exit Confirmation)

**Arquivo:** `src/modules/main_window/views/main_window.py`

#### **Ponto #6: Dialog de confirmação - LINHAS 641-646**
```python
confirm = messagebox.askokcancel(
    "Sair",
    "Tem certeza de que deseja sair do RC Gestor?",
    parent=self,
    icon="question",
)
```

**Status:** ✅ Usa messagebox padrão (sem imagem no corpo)

**Limitação conhecida:** No Windows, `messagebox.askokcancel` pode não herdar ícone do parent ([Python Bug #33958](https://bugs.python.org/issue33958))

---

## 3. Resumo dos Problemas Encontrados

### A) Imagem PNG no Corpo do Diálogo (CRÍTICO)

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `src/modules/uploads/views/browser.py` | 252 | `Label(image=self._icon_img)` no dialog "Download concluído" |

**Impacto:** Visual não-padrão, imagem grande dentro do dialog (não é ícone de janela)

### B) PhotoImage com .ico (Fallback Incorreto)

| Arquivo | Helper/Método | Problema |
|---------|---------------|----------|
| `src/app_gui.py` | `apply_rc_icon()` | `PhotoImage(file=icon_path)` onde icon_path=.ico |
| `src/ui/custom_dialogs.py` | `_apply_icon()` | `PhotoImage(file="rc.ico")` |
| `src/ui/dialogs/pdf_converter_dialogs.py` | `apply_app_icon()` | `PhotoImage(file=APP_ICON_PATH)` (.ico) |
| `src/modules/main_window/views/main_window.py` | `App.__init__()` | `PhotoImage(file=icon_path)` onde icon_path=.ico |

**Impacto:** Fallback falha silenciosamente, ícone pode não aparecer

### C) Progresso ZIP Indeterminado

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `src/modules/uploads/views/browser.py` | 396 | `Progressbar(mode="indeterminate")` - sem bytes reais |

**Impacto:** Usuário não vê progresso real do download (MB baixados, %)

### D) ttkbootstrap.Window sem iconphoto=None

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `src/modules/main_window/views/main_window.py` | 158 | `super().__init__(themename=_theme_name)` sem desabilitar iconphoto padrão |

**Impacto:** Pode contaminar dialogs filhos com iconphoto padrão (PNG)

---

## 4. Plano de Correção

### 4.1. Remover Imagem PNG do Corpo do Diálogo

**Ação:** Remover `Label(image=self._icon_img)` do dialog "Download concluído"

**Justificativa:**
- Diálogos padrão Windows não exibem imagem grande no corpo
- Ícone deve aparecer apenas na titlebar (via iconbitmap/iconphoto)
- Manter apenas texto + botão OK (estilo messagebox padrão)

### 4.2. Padronizar Helpers de Ícone

**Regra:**
- Windows: `iconbitmap(rc.ico)` APENAS
- Fallback: `iconphoto(PhotoImage(file="rc.png"))` (NÃO .ico)
- Verificar se `rc.png` existe antes de tentar fallback

**Arquivos a corrigir:**
1. `src/app_gui.py` - `apply_rc_icon()`
2. `src/ui/custom_dialogs.py` - `_apply_icon()`
3. `src/ui/dialogs/pdf_converter_dialogs.py` - `apply_app_icon()`
4. `src/modules/main_window/views/main_window.py` - `App.__init__()`

### 4.3. Progresso ZIP com Bytes Reais

**Implementação:**
1. Fazer HEAD request para obter `Content-Length` do ZIP
2. Usar `Progressbar(mode="determinate", maximum=total_bytes)`
3. Atualizar `value` com bytes baixados em tempo real
4. Exibir label: `Baixado: X MB / Y MB (Z%)`

**Fallback:** Se `Content-Length` não estiver disponível, manter `indeterminate` + mostrar "Baixado: X MB"

### 4.4. Main Window com iconphoto=None

**Ação:** Adicionar `iconphoto=None` ao `super().__init__()` do ttkbootstrap.Window

**Justificativa:** Desabilitar iconphoto padrão que contamina dialogs

---

## 5. Limitações Conhecidas

### 5.1. tkinter.messagebox no Windows

**Problema:** `messagebox.askokcancel` pode não usar ícone do parent em algumas versões do Tcl/Tk

**Referência:** [Python Bug Tracker #33958](https://bugs.python.org/issue33958)

**Solução atual:** `iconbitmap(default=icon_path)` melhora herança de ícone

**Plano B (se necessário):** Substituir `messagebox.askokcancel` por Toplevel modal customizado com controle total sobre o ícone

### 5.2. PhotoImage + .ico no Windows

**Problema:** `tk.PhotoImage(file="rc.ico")` não funciona bem no Windows (falha ou aparência errada)

**Solução:** Usar sempre `rc.png` como fonte do PhotoImage quando fallback for necessário

---

## 6. Status da Implementação

### ✅ Auditoria Completa
- [x] Busca global por iconphoto, iconbitmap, PhotoImage, Label(image=)
- [x] Identificação de todos os pontos que criam diálogos/Toplevels
- [x] Listagem de helpers existentes
- [x] Documentação de problemas encontrados

### ⏳ Próximos Passos
- [ ] Remover Label(image=) do dialog "Download concluído"
- [ ] Padronizar helpers (usar rc.png no fallback, não .ico)
- [ ] Implementar progresso ZIP determinate com bytes
- [ ] Adicionar iconphoto=None ao ttkbootstrap.Window
- [ ] Atualizar testes
- [ ] Ruff check + format
- [ ] Relatório final com patches aplicados

---

**Assinatura:**  
GitHub Copilot - Auditoria de Sistema de Ícones  
Data: 18 de dezembro de 2025
