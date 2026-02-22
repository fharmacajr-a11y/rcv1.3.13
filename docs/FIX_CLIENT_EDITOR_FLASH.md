# Correção: Flash e Tela Preta no Diálogo Editar Cliente

## O que estava acontecendo

Ao abrir o diálogo "Editar Cliente" (e outras janelas Toplevel), ocorriam dois problemas visuais:

1. **Flash de campos vazios**: A janela aparecia brevemente com campos vazios antes dos dados serem carregados
2. **Tela/frame preta**: Uma janela preta aparecia por alguns frames antes do conteúdo renderizar

### Causa Raiz

O problema ocorria porque:

1. **Uso de `alpha=0/1`**: O mecanismo anti-flash anterior usava `attributes("-alpha", 0.0)` para esconder a janela e depois restaurava `alpha=1.0`. No Windows, isso causa **frames pretos** porque o compositor do sistema não renderiza corretamente janelas com alpha=0.

2. **`deiconify()` na posição final**: A janela era mostrada (`deiconify()`) já na posição centralizada, mas o CustomTkinter (CTk) só desenha os widgets **após** o mapping da janela. Isso criava um frame onde a janela estava visível mas ainda sem conteúdo renderizado.

## Estratégia Adotada

A solução implementa uma estratégia **offscreen → render → onscreen** que:

1. **NÃO usa alpha** (evita frames pretas no Windows)
2. **Renderiza offscreen** antes de mostrar ao usuário

### Fluxo de Execução

```
┌─────────────────────────────────────────────────────────────┐
│ 1. prepare_hidden_window(win)                               │
│    - withdraw() → esconde janela                            │
│    - geometry("1x1+10000+10000") → posição offscreen        │
│    - NÃO usa alpha                                          │
├─────────────────────────────────────────────────────────────┤
│ 2. Construir UI (_build_ui)                                 │
│    - Todos widgets criados enquanto janela withdrawn        │
├─────────────────────────────────────────────────────────────┤
│ 3. Popular dados (_load_client_data)                        │
│    - CRÍTICO: Campos preenchidos ANTES de mostrar           │
├─────────────────────────────────────────────────────────────┤
│ 4. apply_window_icon()                                      │
│    - Aplica ícone (já funcionando)                          │
├─────────────────────────────────────────────────────────────┤
│ 5. show_centered_no_flash(win, parent, width, height)       │
│    a) update_idletasks() → medir tamanho                    │
│    b) Calcular posição centralizada (x, y)                  │
│    c) geometry OFFSCREEN com tamanho final                  │
│       → "{w}x{h}+{screenW+200}+{screenH+200}"               │
│    d) deiconify() ENQUANTO OFFSCREEN                        │
│    e) update_idletasks() + update() → FORÇAR RENDER         │
│       → CTk desenha todos os widgets offscreen              │
│    f) geometry final → "{w}x{h}+{x}+{y}"                    │
│       → Janela já renderizada move para posição visível     │
│    g) lift() + focus_force()                                │
├─────────────────────────────────────────────────────────────┤
│ 6. set_win_dark_titlebar() [APÓS deiconify]                 │
│    - Precisa de handle mapeado (HWND) no Windows            │
├─────────────────────────────────────────────────────────────┤
│ 7. grab_set() para comportamento modal                      │
└─────────────────────────────────────────────────────────────┘
```

### Por que essa estratégia funciona

1. **Offscreen geometry**: Posicionar a janela em `+10000+10000` (ou `screenWidth+200`) garante que ela esteja fora da área visível mesmo durante `deiconify()`.

2. **update() forçado**: Chamar `update()` após `deiconify()` força o Tk/CTk a processar todos os eventos pendentes e renderizar os widgets. Como a janela está offscreen, o usuário não vê o processo.

3. **Move atômico**: Depois que a janela está completamente renderizada offscreen, um único `geometry()` a move para a posição final. O usuário vê a janela aparecer já pronta.

4. **Sem alpha**: Removendo o uso de `attributes("-alpha", ...)`, evitamos os frames pretas causados pelo compositor do Windows.

## Arquivos Modificados

### 1. `src/ui/window_utils.py`

| Função | Alteração |
|--------|-----------|
| `prepare_hidden_window()` | Removido `win.attributes("-alpha", 0.0)`. Mantém apenas `withdraw()` + geometry offscreen. |
| `show_centered_no_flash()` | Reimplementada com estratégia offscreen: deiconify offscreen → update() → move onscreen. Removido uso de alpha. |

### 2. `src/modules/clientes/ui/views/client_editor_dialog.py`

| Alteração | Motivo |
|-----------|--------|
| Movido `set_win_dark_titlebar()` para APÓS `show_centered_no_flash()` | A função precisa de um handle de janela mapeado (HWND). No Windows, janelas withdrawn não têm HWND válido. |

## Checklist de Testes Manuais

### Teste 1: ClientEditorDialog (Editar Cliente)

- [ ] Abrir aplicação: `python main.py`
- [ ] Navegar para módulo **Clientes**
- [ ] Clicar em **Editar** em qualquer cliente
- [ ] **Verificar**:
  - [ ] ✅ Janela aparece já com todos os campos preenchidos
  - [ ] ✅ Sem "piscar" ou flash de campos vazios
  - [ ] ✅ Sem tela/frame preta
  - [ ] ✅ Ícone RC presente na barra de título
  - [ ] ✅ Título correto ("Editar Cliente - ID: X")
  - [ ] ✅ Janela centralizada corretamente
- [ ] Fechar e repetir 5x para confirmar consistência

### Teste 2: Upload Browser

- [ ] Abrir aplicação
- [ ] Navegar para **Uploads**
- [ ] Clicar em **Navegar Uploads** (ou equivalente)
- [ ] **Verificar**:
  - [ ] ✅ Janela abre sem flash/tela preta
  - [ ] ✅ Janela centralizada corretamente

### Teste 3: Notifications Popup

- [ ] Clicar no sino de notificações (se disponível)
- [ ] **Verificar**:
  - [ ] ✅ Popup abre sem flash
  - [ ] ✅ Posicionamento correto

## Resultados dos Testes

| Componente | Flash | Tela Preta | Ícone | Centralização |
|------------|-------|------------|-------|---------------|
| ClientEditorDialog | ⏳ | ⏳ | ⏳ | ⏳ |
| UploadsBrowserWindow | ⏳ | ⏳ | — | ⏳ |
| NotificationsPopup | ⏳ | ⏳ | — | ⏳ |

_Legenda: ✅ OK, ❌ Problema, ⏳ Aguardando teste_

## Referências Técnicas

- CustomTkinter desenha widgets após o mapping da janela (`deiconify()`/`iconify()`)
- No Windows, `attributes("-alpha", 0)` pode causar frames pretas devido ao DWM (Desktop Window Manager)
- Tkinter `update()` processa TODOS os eventos pendentes, incluindo redesenho de widgets

## Data da Correção

2026-02-19
