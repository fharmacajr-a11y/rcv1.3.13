# Patch: Correção Duplo Clique + Flash - ClientesV2

**Data**: 26 de janeiro de 2026  
**Módulo**: `src/modules/clientes_v2/`  
**Arquivos alterados**: 2

---

## 📋 Problemas Resolvidos

### ✅ Tarefa A - Duplo clique abrindo duas vezes
- **Sintoma**: Ao dar duplo clique rápido na lista, duas janelas do editor abriam simultaneamente
- **Causa**: Sem debounce nem referência do diálogo aberto

### ✅ Tarefa B - Flash ao abrir editor
- **Sintoma**: Janela do editor "piscava" branco antes de renderizar o conteúdo
- **Causa**: Janela estava visível durante construção do layout

### ✅ Tarefa C - Borda branca externa
- **Sintoma**: Janela do editor tinha borda branca ao redor do conteúdo
- **Causa**: `padding=20` no container principal e `corner_radius=12`

---

## 🔧 Correções Implementadas

### 1. **view.py** - ClientesV2Frame

#### 1.1 Adicionados campos para guard de duplo clique

**Localização**: Linhas 50-56 (dentro de `__init__`)

```python
# TAREFA A: Guard para duplo clique (evitar duplicação)
self._editor_dialog: Optional[Any] = None  # Referência ao diálogo aberto
self._last_doubleclick_time: float = 0.0  # Timestamp do último duplo clique
```

**Motivo**: Permite detectar duplo clique duplicado e verificar se diálogo já está aberto.

---

#### 1.2 Unbind antes de cada bind (prevenir múltiplos binds)

**Localização**: Linhas 187-207 (dentro de `_create_main_tree`)

**ANTES**:
```python
# Binds para seleção e atalhos
self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

# FASE 3.4: Em pick_mode, duplo clique seleciona; caso contrário, edita
if self._pick_mode:
    self.tree.bind("<Double-Button-1>", lambda e: self._on_pick_confirm())
else:
    self.tree.bind("<Double-Button-1>", lambda e: self._on_edit_client(e))
    self.tree.bind("<Return>", lambda e: self._on_edit_client(e))
    self.tree.bind("<Button-3>", self._on_tree_right_click)
    self.tree.bind("<Button-1>", self._on_tree_click)
```

**DEPOIS**:
```python
# Binds para seleção e atalhos
# TAREFA A: Unbind antes de bind para evitar duplicação
self.tree.unbind("<<TreeviewSelect>>")
self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

# FASE 3.4: Em pick_mode, duplo clique seleciona; caso contrário, edita
if self._pick_mode:
    self.tree.unbind("<Double-Button-1>")
    self.tree.bind("<Double-Button-1>", lambda e: self._on_pick_confirm())
else:
    # TAREFA A: Unbind antes de cada bind
    self.tree.unbind("<Double-Button-1>")
    self.tree.unbind("<Return>")
    self.tree.unbind("<Button-3>")
    self.tree.unbind("<Button-1>")

    self.tree.bind("<Double-Button-1>", lambda e: self._on_edit_client(e))
    self.tree.bind("<Return>", lambda e: self._on_edit_client(e))
    self.tree.bind("<Button-3>", self._on_tree_right_click)
    self.tree.bind("<Button-1>", self._on_tree_click)
```

**Motivo**: Se `_create_main_tree` for chamado mais de uma vez (ex.: mudança de tema), os binds se acumulam. Unbind antes garante apenas 1 handler por evento.

---

#### 1.3 Guard com debounce + referência do diálogo

**Localização**: Linhas 962-1043 (método `_on_edit_client`)

**ANTES**:
```python
def _on_edit_client(self, event: Any = None) -> str | None:
    """Handler para botão Editar Cliente."""
    if not self.app:
        # ... erro
        return "break" if event else None

    if not self._selected_client_id:
        # ... aviso
        return

    # Abrir diálogo
    dialog = ClientEditorDialog(
        parent=self.winfo_toplevel(),
        client_id=self._selected_client_id,
        on_save=on_saved,
    )
    dialog.focus()
```

**DEPOIS**:
```python
def _on_edit_client(self, event: Any = None) -> str | None:
    """Handler para botão Editar Cliente.

    TAREFA A: Guard com debounce e referência para evitar duplo clique duplicado.
    """
    # TAREFA A: Guard - debounce de 250ms
    import time
    current_time = time.time()
    if current_time - self._last_doubleclick_time < 0.250:
        log.debug("[ClientesV2] Duplo clique ignorado (debounce)")
        return "break" if event else None
    self._last_doubleclick_time = current_time

    # TAREFA A: Guard - se diálogo já existe e está visível, apenas dar foco
    if self._editor_dialog is not None:
        try:
            if self._editor_dialog.winfo_exists():
                log.debug("[ClientesV2] Diálogo já aberto, dando foco")
                self._editor_dialog.lift()
                self._editor_dialog.focus_force()
                return "break" if event else None
        except Exception:
            # Diálogo foi destruído mas referência não foi limpa
            self._editor_dialog = None

    # ... validações ...

    def on_closed() -> None:
        """Callback quando diálogo é fechado."""
        self._editor_dialog = None

    # TAREFA A: Abrir diálogo modal e guardar referência
    self._editor_dialog = ClientEditorDialog(
        parent=self.winfo_toplevel(),
        client_id=self._selected_client_id,
        on_save=on_saved,
        on_close=on_closed,  # NOVO
    )
    self._editor_dialog.focus()
```

**Motivo**:
- **Debounce (250ms)**: Se usuário clicar 2x muito rápido, apenas o primeiro abre
- **Referência do diálogo**: Se diálogo já está aberto, apenas dá foco (não abre outro)
- **Callback on_close**: Limpa referência quando diálogo é fechado

**Retorna `"break"`**: Evita propagação do evento (previne handlers adicionais)

---

### 2. **client_editor_dialog.py** - ClientEditorDialog

#### 2.1 Adiciona parâmetro `on_close` e padrão withdraw/deiconify

**Localização**: Linhas 29-72 (método `__init__`)

**ANTES**:
```python
def __init__(
    self,
    parent: Any,
    client_id: Optional[int] = None,
    on_save: Optional[Callable[[dict], None]] = None,
    **kwargs: Any,
):
    super().__init__(parent, **kwargs)

    self.client_id = client_id
    self.on_save = on_save
    self._client_data: Optional[dict] = None

    # Configurar janela
    self._set_window_title()
    self.geometry("940x600")
    # ... centralização ...

    # Tornar modal
    self.transient(parent)
    self.grab_set()  # ❌ Causa flicker

    self._build_ui()

    if client_id is not None:
        self.after(100, self._load_client_data)
```

**DEPOIS**:
```python
def __init__(
    self,
    parent: Any,
    client_id: Optional[int] = None,
    on_save: Optional[Callable[[dict], None]] = None,
    on_close: Optional[Callable[[], None]] = None,  # NOVO
    **kwargs: Any,
):
    super().__init__(parent, **kwargs)

    self.client_id = client_id
    self.on_save = on_save
    self.on_close = on_close  # NOVO
    self._client_data: Optional[dict] = None

    # TAREFA B: Ocultar janela inicialmente para evitar flash
    self.withdraw()

    # Configurar janela
    self._set_window_title()
    self.geometry("940x600")
    # ... centralização ...

    # Tornar modal
    self.transient(parent)

    self._build_ui()

    if client_id is not None:
        self.after(100, self._load_client_data)

    # TAREFA B: Mostrar janela após construir (elimina flash)
    self.update_idletasks()
    self.deiconify()

    # TAREFA B: grab_set após mostrar (evita flicker)
    self.after(0, self.grab_set)

    # TAREFA A: Registrar callback de fechamento
    self.protocol("WM_DELETE_WINDOW", self._on_window_close)
```

**Motivo**:
- **`withdraw()` no início**: Janela fica invisível durante construção do layout
- **`deiconify()` após build**: Janela aparece apenas quando layout está completo
- **`update_idletasks()`**: Força renderização completa antes de mostrar
- **`self.after(0, self.grab_set)`**: Grab modal depois da janela ser exibida (evita flicker em alguns sistemas)
- **`protocol("WM_DELETE_WINDOW", ...)`**: Intercepta botão X para chamar `on_close`

---

#### 2.2 Remove borda branca externa

**Localização**: Linhas 78-89 (método `_build_ui`)

**ANTES**:
```python
def _build_ui(self) -> None:
    # Usar cores do Hub
    self.configure(fg_color=APP_BG)

    # Container principal
    main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=12)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)  # ❌ Padding cria borda branca
```

**DEPOIS**:
```python
def _build_ui(self) -> None:
    # TAREFA C: Background cinza claro (sem borda branca)
    self.configure(fg_color=APP_BG)

    # TAREFA C: Container principal - sem padding externo (remove borda branca)
    main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=0)
    main_frame.pack(fill="both", expand=True, padx=0, pady=0)  # ✅ Sem padding
```

**Motivo**:
- **`padx=20, pady=20`** → **`padx=0, pady=0`**: Remove espaço branco ao redor
- **`corner_radius=12`** → **`corner_radius=0`**: Borda quadrada (sem arredondamento que deixa branco nos cantos)

**Visual**: Agora o frame escuro preenche 100% da janela, sem margens brancas.

---

#### 2.3 Adiciona método `_on_window_close`

**Localização**: Linhas 68-76 (novo método após `_set_window_title`)

```python
def _on_window_close(self) -> None:
    """Handler quando usuário fecha a janela (X).

    TAREFA A: Notifica parent que diálogo foi fechado.
    """
    if self.on_close:
        self.on_close()
    self.destroy()
```

**Motivo**: Quando usuário fecha janela pelo X, chama `on_close()` para limpar referência em `ClientesV2Frame`.

---

## 🎯 Fluxo Completo (Tarefa A)

### Cenário 1: Duplo clique rápido (< 250ms)

1. **Primeiro clique**:
   - `_on_edit_client` executado
   - `_last_doubleclick_time` = agora
   - Diálogo abre normalmente
   - `self._editor_dialog` guarda referência

2. **Segundo clique (imediato)**:
   - `_on_edit_client` executado novamente
   - **Guard 1**: `agora - _last_doubleclick_time < 0.250` ✅
   - **Resultado**: Retorna "break" imediatamente (nada acontece)

### Cenário 2: Diálogo já aberto

1. **Primeiro clique**:
   - Diálogo abre
   - `self._editor_dialog` != None

2. **Segundo clique (com diálogo aberto)**:
   - **Guard 2**: `self._editor_dialog.winfo_exists()` ✅
   - **Resultado**: `lift()` + `focus_force()` (apenas foco)

### Cenário 3: Usuário fecha diálogo

1. **Usuário clica X**:
   - `protocol("WM_DELETE_WINDOW")` chama `_on_window_close()`
   - `on_close()` callback executado
   - `self._editor_dialog = None` (referência limpa)

2. **Próximo duplo clique**:
   - Debounce reseta (> 250ms)
   - `self._editor_dialog == None`
   - Novo diálogo abre normalmente

---

## 🎯 Fluxo Completo (Tarefa B)

### Sem correção (antes)
```
1. CTkToplevel.__init__()        → Janela VISÍVEL (branco)
2. geometry("940x600")           → Resize (flash)
3. _build_ui()                   → Widgets sendo criados (flash)
4. grab_set()                    → Modal (pode causar flicker)
   ↓
   Usuário vê: Flash branco → Flash cinza → Conteúdo final
```

### Com correção (depois)
```
1. CTkToplevel.__init__()        → Janela VISÍVEL
2. withdraw()                    → Janela INVISÍVEL (imediato)
3. geometry("940x600")           → Resize (invisível)
4. _build_ui()                   → Widgets criados (invisível)
5. update_idletasks()            → Renderização completa (invisível)
6. deiconify()                   → Janela VISÍVEL (pronta)
7. after(0, grab_set)            → Modal após render
   ↓
   Usuário vê: Diálogo aparece instantaneamente completo
```

**Diferença crítica**: Janela só fica visível APÓS estar 100% construída.

---

## 🎯 Fluxo Completo (Tarefa C)

### Estrutura de padding (antes)
```
┌─────────────────────────────────────────┐ ← CTkToplevel (fg_color=APP_BG)
│  [20px branco]                          │
│  ┌─────────────────────────────────┐   │
│  │ main_frame (SURFACE_DARK)       │   │ ← corner_radius=12 (cantos arredondados)
│  │                                 │   │
│  │  [conteúdo]                     │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
│  [20px branco]                          │
└─────────────────────────────────────────┘
```

### Estrutura de padding (depois)
```
┌─────────────────────────────────────────┐ ← CTkToplevel (fg_color=APP_BG)
│ main_frame (SURFACE_DARK)               │ ← corner_radius=0 (quadrado)
│                                         │
│  [conteúdo]                             │
│                                         │
└─────────────────────────────────────────┘
```

**Resultado**: Apenas cinza escuro, sem bordas brancas.

---

## ✅ Checklist de Validação

Execute o app e teste:

### Duplo Clique (Tarefa A)
```
□ Duplo clique normal abre 1 diálogo (não 2)
□ Duplo clique rápido (< 250ms) abre apenas 1
□ Com diálogo aberto, duplo clique apenas dá foco (não abre outro)
□ Fechar diálogo e abrir novamente funciona
□ Logs mostram "Duplo clique ignorado (debounce)" quando necessário
□ Logs mostram "Diálogo já aberto, dando foco" quando necessário
```

### Flash (Tarefa B)
```
□ Diálogo aparece instantaneamente sem "piscar"
□ Não há flash branco antes do conteúdo
□ Janela está completamente renderizada ao aparecer
□ Modal funciona corretamente (bloqueia janela pai)
```

### Borda Branca (Tarefa C)
```
□ Sem borda branca ao redor do diálogo
□ Frame escuro preenche 100% da janela
□ Sem espaços vazios nos cantos
□ Visual consistente com resto do app
```

---

## 📝 Notas Técnicas

### Por que `unbind()` antes de `bind()`?

Tkinter/ttk **acumula** handlers quando você chama `bind()` múltiplas vezes no mesmo evento. Se `_create_main_tree` for chamado 2x (ex.: mudança de tema), você terá 2 handlers para `<Double-Button-1>`, e ambos executarão.

**Exemplo**:
```python
# Primeira chamada
tree.bind("<Double-Button-1>", handler)  # 1 handler

# Segunda chamada (sem unbind)
tree.bind("<Double-Button-1>", handler)  # 2 handlers (duplicado!)

# Ao dar duplo clique: handler executa 2 vezes
```

**Solução**:
```python
# Sempre unbind antes de bind
tree.unbind("<Double-Button-1>")
tree.bind("<Double-Button-1>", handler)  # Sempre 1 handler
```

---

### Por que `time.time()` e não contador?

`time.time()` retorna timestamp absoluto (segundos desde epoch), permitindo calcular intervalo exato entre cliques. Um contador simples não detectaria se os cliques foram há 10ms ou 10 segundos.

**Exemplo**:
```python
# Clique 1: time.time() = 1000.000
self._last_doubleclick_time = 1000.000

# Clique 2: time.time() = 1000.100 (100ms depois)
if 1000.100 - 1000.000 < 0.250:  # 0.100 < 0.250 ✅
    return "break"  # Ignorar (muito rápido)
```

---

### Por que `"break"` no return?

Em Tkinter, retornar `"break"` de um handler **impede propagação** do evento para outros handlers. Isso garante que, se houver múltiplos binds acidentais, apenas o primeiro execute.

```python
def _on_edit_client(self, event: Any = None) -> str | None:
    # ... lógica ...
    return "break" if event else None
```

- **Com `event` (duplo clique/Enter)**: Retorna "break" → Evento não propaga
- **Sem `event` (botão Editar)**: Retorna None → Comportamento padrão

---

### Por que `winfo_exists()`?

`winfo_exists()` verifica se o widget ainda existe na memória. Se usuário fechou o diálogo mas `self._editor_dialog` ainda tem referência, `winfo_exists()` retorna `False`.

```python
if self._editor_dialog is not None:
    try:
        if self._editor_dialog.winfo_exists():  # Widget ainda existe?
            self._editor_dialog.lift()         # Sim: dar foco
        else:
            self._editor_dialog = None         # Não: limpar referência
    except Exception:
        self._editor_dialog = None             # Erro: limpar referência
```

---

## 📊 Impacto

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Duplo clique duplicado** | 2 diálogos abrem | 1 diálogo (guard) |
| **Flash ao abrir** | Flash branco visível | Aparece instantaneamente |
| **Borda branca** | 20px ao redor | 0px (preenche 100%) |
| **Handlers acumulados** | Possível duplicação | Sempre 1 handler |
| **Performance** | Debounce 0ms | Debounce 250ms |

---

## 🔍 Diff Resumido

### view.py (3 alterações)
1. **Linha 50**: `+ self._editor_dialog = None` e `+ self._last_doubleclick_time = 0.0`
2. **Linha 187-207**: `+ self.tree.unbind(...)` antes de cada `bind()`
3. **Linha 962-1043**: `+ debounce guard` + `+ dialog reference guard` + `+ on_close callback`

### client_editor_dialog.py (3 alterações)
1. **Linha 29-72**: `+ on_close parameter` + `+ withdraw/deiconify pattern` + `+ protocol WM_DELETE_WINDOW`
2. **Linha 68-76**: `+ _on_window_close method`
3. **Linha 78-89**: `- padx=20, pady=20` + `- corner_radius=12`

---

## ✅ Restrições Atendidas

✅ **Não remover funcionalidades**: Todas as funcionalidades existentes mantidas  
✅ **Não deixar código quebrado**: Código backward-compatible (on_close é opcional)  
✅ **Preferir CTk**: Apenas CustomTkinter usado (nenhum `tk.Label` adicionado)  
✅ **Patch mínimo**: Apenas 6 alterações pontuais, sem refatoração desnecessária  

---

**Implementado em**: 26 de janeiro de 2026  
**Status**: ✅ Testável
