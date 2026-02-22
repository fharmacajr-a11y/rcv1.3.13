# Correção: Flash e Ícone no Diálogo Editar Cliente

## Descrição do Problema

Ao abrir o diálogo "Editar Cliente", foram identificados dois problemas:

1. **Flash visual**: A janela aparecia brevemente com campos vazios antes de popular os dados
2. **Ícone ausente**: O ícone do aplicativo (rc.ico) não era exibido na barra de título do diálogo

## Causa Raiz

### Flash Visual
O Tkinter/CustomTkinter renderiza a janela imediatamente após `deiconify()`, mesmo que os dados ainda não tenham sido carregados nos campos. Isso criava:
- Uma janela visível mas vazia por alguns frames
- Um "piscar" perceptível ao carregar dados nos campos

### Ícone Ausente  
O `CTkToplevel` do CustomTkinter sobrescreve o ícone da janela aproximadamente 200ms após a criação, anulando qualquer `iconbitmap()` ou `iconphoto()` aplicado anteriormente.

## Solução Implementada

### Arquivos Modificados

#### 1. `src/ui/window_utils.py`
Função `apply_window_icon()` melhorada:
- Cache de `PhotoImage` em nível de módulo (previne garbage collection)
- Busca automática de `rc.ico` ou `rc.png` em `assets/`
- Usa `iconphoto(False, photo)` para Toplevels (não propaga para filhos)
- Reaplica o ícone após 250ms via `after()` (derrota o override do CTkToplevel)

#### 2. `src/modules/clientes/ui/views/client_editor_dialog.py`
Refatoração do `__init__` usando helpers centralizados:

```python
# ANTES (código complexo e duplicado)
self.withdraw()
self.attributes("-alpha", 0.0)
# ... 50+ linhas de lógica manual ...

# DEPOIS (usando helpers)
prepare_hidden_window(self)      # withdraw + alpha=0 + offscreen
self._build_ui()                 # construir UI enquanto invisível
self._load_client_data()         # popular dados ANTES de mostrar
apply_window_icon(self)          # ícone com reapply automático
show_centered_no_flash(...)      # mostrar já centralizado
```

### Fluxo Anti-Flash

```
┌─────────────────────────────────────────────────────────────┐
│ 1. prepare_hidden_window()                                  │
│    - withdraw() → esconde janela                            │
│    - alpha=0 → transparente (proteção extra Windows)        │
│    - geometry offscreen → evita flash mesmo se aparecer     │
├─────────────────────────────────────────────────────────────┤
│ 2. Construir UI (_build_ui)                                 │
│    - Todos widgets criados enquanto janela invisível        │
├─────────────────────────────────────────────────────────────┤
│ 3. Popular dados (_load_client_data)                        │
│    - CRÍTICO: Campos preenchidos ANTES de mostrar           │
├─────────────────────────────────────────────────────────────┤
│ 4. apply_window_icon()                                      │
│    - Aplica ícone imediatamente                             │
│    - Agenda reapply em 250ms (derrota CTkToplevel)          │
├─────────────────────────────────────────────────────────────┤
│ 5. show_centered_no_flash()                                 │
│    - Calcula posição centralizada                           │
│    - deiconify() → torna visível                            │
│    - alpha=1.0 → opaco                                      │
│    - lift() + focus_force()                                 │
└─────────────────────────────────────────────────────────────┘
```

### Cache de Ícone

```python
# Módulo window_utils.py
_icon_photo_cache: dict[str, tk.PhotoImage] = {}  # Previne GC

def _get_cached_photo(window: tk.Misc) -> tk.PhotoImage | None:
    """Cria ou retorna PhotoImage cacheado."""
    if "icon" in _icon_photo_cache:
        return _icon_photo_cache["icon"]

    photo = tk.PhotoImage(master=window, file=_icon_png_path)
    _icon_photo_cache["icon"] = photo  # Mantém referência viva
    return photo
```

## Passos para Verificação

1. Abrir a aplicação
2. Navegar para módulo Clientes
3. Clicar em "Editar" em qualquer cliente
4. **Verificar**:
   - ✅ Janela aparece já com todos os campos preenchidos
   - ✅ Sem "piscar" ou flash de campos vazios
   - ✅ Ícone RC aparece na barra de título
   - ✅ Ícone permanece após 1-2 segundos (não é sobrescrito)

## Referências Técnicas

- [CustomTkinter Issue #2521](https://github.com/TomSchimansky/CustomTkinter/issues/2521) - CTkToplevel sobrescreve ícone
- [Tkinter iconphoto documentation](https://www.tcl.tk/man/tcl8.6/TkCmd/wm.htm#M51) - Diferença entre default=True/False
- [PhotoImage garbage collection](https://effbot.org/tkinterbook/photoimage.htm) - Por que manter referência

## Data da Correção

2025-01-XX (veja git log)
