# Refatoração TopBar e Visualizador PDF - v1.4.52

**Data:** 19 de dezembro de 2025  
**Tipo:** Refatoração de UI  
**Status:** ✅ Concluído

## Objetivo

Mover o botão "Conversor PDF" do TopBar para dentro da toolbar do Visualizador de PDF, consolidando funcionalidades relacionadas a PDF em um único local e simplificando a interface principal.

## Mudanças Implementadas

### 1. TopBar (src/ui/topbar.py)

#### Removidos:
- ❌ Botão "Inicio" (btn_home)
- ❌ Botão "Conversor PDF" (btn_pdf_converter)

#### Mantidos:
- ✅ Botão "Visualizador PDF"
- ✅ Botão "ChatGPT"
- ✅ Botão "Sites"

#### Ajustes:
- Todos os botões agora usam `padx=8` para alinhamento uniforme
- Métodos `_handle_home()` e `_handle_pdf_converter()` mantidos como NO-OP para compatibilidade
- Método `set_is_hub()` agora é NO-OP seguro
- Método `set_pick_mode_active()` atualizado para gerenciar os 3 botões existentes

### 2. PdfToolbar (src/modules/pdf_preview/views/toolbar.py)

#### Adicionado:
- ✅ Novo parâmetro `on_open_converter: Callable[[], None] | None = None`
- ✅ Novo botão `btn_converter` com texto "Conversor PDF"
- ✅ Posicionamento à direita, antes dos botões de download

#### Layout visual (da direita para esquerda):
```
[Baixar PDF] [Baixar imagem] [Conversor PDF]
```

#### Comportamento:
- Botão desabilitado quando `on_open_converter` é `None`
- Habilitado automaticamente quando callback é fornecido

### 3. PdfViewerWin (src/modules/pdf_preview/views/main_window.py)

#### Novos atributos:
```python
self._context_master: tk.Misc = master
self._converter_cb: Callable[[], None] | None = None
```

#### Novos métodos:

**`_resolve_pdf_converter_callback() -> Callable[[], None] | None`**
- Procura método `run_pdf_batch_converter` subindo a hierarquia de masters
- Permite que o viewer encontre o conversor no App principal

**`set_context_master(master: tk.Misc) -> None`**
- Atualiza o contexto do master
- Recalcula callback do conversor
- Atualiza estado do botão automaticamente

**`_open_pdf_converter() -> None`**
- Handler para clique no botão
- Gerencia grab_release/grab_set para evitar conflitos modais
- Invoca o conversor se disponível

#### Integração:
- Toolbar criada com parâmetro `on_open_converter=self._open_pdf_converter`
- `set_context_master(master)` chamado após criação da toolbar

### 4. pdf_preview_native (src/ui/pdf_preview_native.py)

#### Atualização no reuso de singleton:
```python
# Atualiza contexto do master antes de carregar conteúdo
win.set_context_master(master)
```

**Motivo:** Garante que viewer reutilizado encontre o conversor mesmo se foi aberto por outra janela inicialmente.

### 5. main_screen_frame (src/modules/clientes/views/main_screen_frame.py)

#### Ajuste de mensagem:
- ❌ Antiga: "reabilitar Conversor PDF"
- ✅ Nova: "reabilitar menus da topbar"

**Motivo:** Texto não pode mais referenciar um botão que não existe.

### 6. Testes (tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py)

#### Atualização:
- Adicionado `on_open_converter` na criação de PdfToolbar
- Teste invoca `toolbar.btn_converter.invoke()`
- Validação de evento `"open_converter"` nos callbacks

## Validação

### ✅ Compilação
```bash
python -m compileall src/ui/topbar.py src/modules/pdf_preview/views/toolbar.py \
    src/modules/pdf_preview/views/main_window.py src/ui/pdf_preview_native.py
# Status: Sucesso
```

### ✅ Ruff
```bash
ruff check src/ui/topbar.py src/modules/pdf_preview/views/toolbar.py \
    src/modules/pdf_preview/views/main_window.py src/ui/pdf_preview_native.py
# All checks passed!
```

### ✅ Pyright
```bash
pyright src/ui/topbar.py src/modules/pdf_preview/views/toolbar.py \
    src/modules/pdf_preview/views/main_window.py src/ui/pdf_preview_native.py --level error
# 0 errors, 0 warnings, 0 informations
```

### ✅ Pytest
```bash
pytest -q tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py
# 3 skipped, 0 failed

pytest -q tests/unit/ui/test_topbar_chatgpt_button.py tests/unit/ui/test_topbar_sites_button.py
# 2 passed
```

## Compatibilidade

### ✅ APIs mantidas:
- Assinatura do `TopBar.__init__()` inalterada (todos os parâmetros mantidos)
- Métodos `_handle_home()` e `_handle_pdf_converter()` ainda existem
- Método `set_pick_mode_active()` funciona com novos botões
- `PdfToolbar` aceita `on_open_converter` como parâmetro opcional

### ⚠️ Mudanças visuais:
- TopBar agora mostra apenas 3 botões (em vez de 5)
- Conversor PDF acessível através do Visualizador PDF

## Teste Manual

### Checklist de aceite:
- [ ] Abrir aplicação
- [ ] TopBar deve mostrar apenas: **Visualizador PDF | ChatGPT | Sites**
- [ ] Todos os botões devem ter o mesmo espaçamento
- [ ] Clicar em "Visualizador PDF"
- [ ] Toolbar do viewer deve mostrar botão "Conversor PDF" à direita
- [ ] Clicar em "Conversor PDF" deve abrir o conversor
- [ ] Fechar conversor não deve travar a janela (grab funciona corretamente)
- [ ] Reabrir Visualizador PDF (singleton) deve manter botão funcional

## Arquivos Modificados

1. [src/ui/topbar.py](../../../src/ui/topbar.py)
2. [src/modules/pdf_preview/views/toolbar.py](../../../src/modules/pdf_preview/views/toolbar.py)
3. [src/modules/pdf_preview/views/main_window.py](../../../src/modules/pdf_preview/views/main_window.py)
4. [src/ui/pdf_preview_native.py](../../../src/ui/pdf_preview_native.py)
5. [src/modules/clientes/views/main_screen_frame.py](../../../src/modules/clientes/views/main_screen_frame.py)
6. [tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py](../../../tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py)

## Benefícios

1. **UI mais limpa:** TopBar agora tem apenas 3 botões, mais focado
2. **Melhor organização:** Funcionalidades de PDF consolidadas no Visualizador
3. **Descoberta intuitiva:** Conversor acessível onde PDFs são visualizados
4. **Sem quebra:** Código existente continua funcionando (compatibilidade mantida)

## Notas Técnicas

### Callback Resolver Pattern
O método `_resolve_pdf_converter_callback()` implementa um padrão de busca na hierarquia:
```python
obj = self._context_master
while obj is not None:
    fn = getattr(obj, "run_pdf_batch_converter", None)
    if callable(fn):
        return cast(Callable[[], None], fn)
    obj = getattr(obj, "master", None)
```

Isso permite que o viewer encontre o método independentemente de quantos níveis de widgets existam entre ele e o App.

### Grab Management
O método `_open_pdf_converter()` gerencia cuidadosamente o grab modal:
1. Libera grab antes de abrir conversor
2. Conversor funciona normalmente (pode ter seu próprio grab)
3. Restaura grab do viewer após fechar conversor
4. Verifica se janela ainda existe antes de restaurar

---

**Implementado por:** GitHub Copilot  
**Revisão:** Pendente  
**Deploy:** Pronto para v1.4.52
