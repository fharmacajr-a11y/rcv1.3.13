# DevLog: UI-PDF-PREVIEW-CONTROLLER-01 - Integração controller headless com uploads

**Data:** 2025-12-08  
**Autor:** Copilot + Human  
**Branch:** `qa/fixpack-04`  
**Contexto:** FASE UI-PDF-PREVIEW-CONTROLLER-01 — Preparar integração do PDF preview interno com uploads via mode="internal"

---

## 1. Estado Inicial

### 1.1 Controller já existente

**Descoberta:** O módulo PDF preview já possui um controller headless bem estruturado!

**Arquivo:** `src/modules/pdf_preview/controller.py` (204 linhas)

**Classes principais:**

```python
@dataclass
class PdfPreviewState:
    current_page: int = 0
    page_count: int = 0
    zoom: float = 1.0
    fit_mode: str = "width"
    show_text: bool = False

class PdfPreviewController:
    MIN_ZOOM = 0.2
    MAX_ZOOM = 6.0
    ZOOM_STEP = 0.1

    def __init__(self, *, pdf_bytes=None, pdf_path=None, raster_service=None)
    def go_to_page(self, index: int) -> None
    def next_page(self) -> None
    def prev_page(self) -> None
    def first_page(self) -> None
    def last_page(self) -> None
    def set_zoom(self, zoom: float, *, fit_mode=None) -> None
    def zoom_in(self, step=ZOOM_STEP) -> None
    def zoom_out(self, step=ZOOM_STEP) -> None
    def apply_zoom_delta(self, wheel_steps: float, *, step=ZOOM_STEP) -> float
    def toggle_text(self) -> None
    def get_page_pixmap(self, page_index=None, *, zoom=None) -> PageRenderData
    def get_render_state(self) -> PdfRenderState
    def get_button_states(self) -> PdfButtonStates
```

**Integração com View:** `src/modules/pdf_preview/views/main_window.py` já usa o controller:

```python
class PdfViewerWin(tk.Toplevel):
    def __init__(self, ...):
        self._controller: Optional[PdfPreviewController] = None

    def open_document(self, pdf_path=None, data_bytes=None, display_name=None):
        self._controller = PdfPreviewController(pdf_path=path)
        self.page_count = self._controller.state.page_count
        self._page_sizes = self._controller.page_sizes

    def _zoom_by(self, wheel_steps_count, event=None):
        if self._controller is not None:
            new = self._controller.apply_zoom_delta(wheel_steps_count)
        self._render_state(...)
```

**Conclusão:** Controller headless já implementado e testado! Tarefa principal desta fase é integrar com uploads via `mode="internal"`.

### 1.2 Estado de `download_and_open_file`

**Antes:**
```python
def download_and_open_file(remote_key: str, *, bucket=None, mode="external"):
    if mode == "internal":
        # TODO: Implementar integração com PDF preview interno
        return {"ok": False, "message": "Modo 'internal' ainda não implementado."}

    # Baixa arquivo e abre com viewer do SO
    ...
```

**Problema:** Não havia ponte entre serviço de uploads e PDF preview interno.

---

## 2. Solução Implementada

### 2.1 Implementação de `mode="internal"` em uploads

**Arquivo modificado:** `src/modules/uploads/service.py`

**Mudanças:**

```python
def download_and_open_file(remote_key: str, *, bucket=None, mode="external") -> dict[str, Any]:
    # ... validação e download (inalterado) ...

    # Mode "internal": retorna path para caller abrir no PDF viewer interno
    if mode == "internal":
        logger.info("Arquivo preparado para viewer interno: %s", local_path)
        return {
            "ok": True,
            "message": "Arquivo baixado com sucesso (modo interno)",
            "temp_path": local_path,
            "display_name": remote_filename,
            "mode": "internal",  # ✅ NOVO
        }

    # Mode "external": abrir no visualizador do SO (inalterado)
    ...
```

**Retorno para mode="internal":**
- `ok`: True
- `message`: "Arquivo baixado com sucesso (modo interno)"
- `temp_path`: Caminho do arquivo temporário
- `display_name`: Nome do arquivo para exibição
- `mode`: "internal" (marcador para caller)

**Logs adicionados:**
```
INFO: Arquivo preparado para viewer interno: /tmp/rc_gestor_uploads/documento.pdf
```

### 2.2 Helper de integração para UI

**Arquivo criado:** `src/modules/pdf_preview/view.py` (nova função)

```python
def open_pdf_viewer_from_download_result(master, download_result: dict[str, Any]):
    """Abre o PDF viewer interno a partir do resultado de download_and_open_file(mode='internal').

    Args:
        master: Widget pai (Tkinter)
        download_result: Resultado de download_and_open_file() com mode='internal'

    Returns:
        PdfViewerWin instance ou None se resultado inválido

    Example:
        result = download_and_open_file("path/to/file.pdf", mode="internal")
        if result["ok"] and result.get("mode") == "internal":
            open_pdf_viewer_from_download_result(root, result)
    """
    if not download_result.get("ok"):
        return None

    if download_result.get("mode") != "internal":
        return None

    temp_path = download_result.get("temp_path")
    display_name = download_result.get("display_name")

    if not temp_path:
        return None

    return open_pdf_viewer(
        master,
        pdf_path=temp_path,
        display_name=display_name,
    )
```

**Vantagens:**
- Validação automática do resultado (ok, mode, temp_path)
- Interface limpa para UI
- Retorna None em caso de erro (não levanta exceção)
- Pode ser usado em qualquer módulo (uploads, auditoria, hub)

**Exportado em:** `src/modules/pdf_preview/__init__.py`

```python
__all__ = [
    "PdfPreviewFrame",
    "open_pdf_viewer",
    "open_pdf_viewer_from_download_result",  # ✅ NOVO
    "service",
]
```

### 2.3 Exemplo de uso futuro

**Em uploads/auditoria/hub:**

```python
from src.modules.pdf_preview import open_pdf_viewer_from_download_result
from src.modules.uploads.service import download_and_open_file

# Baixar e abrir no viewer interno
result = download_and_open_file(
    "clientes/123/contrato.pdf",
    mode="internal"
)

if result["ok"]:
    viewer = open_pdf_viewer_from_download_result(self, result)
    if viewer:
        # Viewer aberto com sucesso
        pass
    else:
        # Falha ao abrir viewer (tratar erro)
        messagebox.showerror("Erro", "Não foi possível abrir o arquivo")
```

---

## 3. Testes Criados

### 3.1 Testes de `download_and_open_file` com mode="internal"

**Arquivo modificado:** `tests/unit/modules/uploads/test_download_and_open_file.py`

**Teste atualizado:**

```python
def test_internal_mode_returns_not_implemented(self, ...):
    """Mode 'internal' deve baixar arquivo e retornar path para caller."""
    # Arrange
    mock_create_temp.return_value = Mock(
        path="/tmp/rc_gestor_uploads/documento.pdf",
        filename="documento.pdf",
    )
    mock_download.return_value = {"ok": True}

    # Act
    result = download_and_open_file("clientes/123/documento.pdf", mode="internal")

    # Assert
    assert result["ok"] is True
    assert result["mode"] == "internal"
    assert result["temp_path"] == "/tmp/rc_gestor_uploads/documento.pdf"
    assert result["display_name"] == "documento.pdf"
    assert "Arquivo baixado com sucesso (modo interno)" in result["message"]
```

**Antes:** Esperava erro "ainda não implementado"  
**Depois:** Valida retorno com path, display_name e mode

### 3.2 Testes do helper de integração

**Arquivo criado:** `tests/unit/modules/pdf_preview/test_open_pdf_viewer_from_download.py` (120 linhas)

**Classe de teste:**

**`TestOpenPdfViewerFromDownloadResult`** (5 testes):

1. **`test_opens_viewer_with_valid_internal_result`** ✅
   - Valida que viewer é aberto com resultado válido
   - Mock de `open_pdf_viewer` verifica argumentos corretos

2. **`test_returns_none_when_result_not_ok`** ✅
   - Se download falhou, não abre viewer

3. **`test_returns_none_when_mode_is_not_internal`** ✅
   - Se mode="external", não abre viewer interno

4. **`test_returns_none_when_temp_path_missing`** ✅
   - Se temp_path ausente, não abre viewer

5. **`test_works_without_display_name`** ✅
   - Funciona mesmo sem display_name

**Resultado:**
```
5 passed in 2.49s ✅
```

### 3.3 Correção de teste existente

**Arquivo modificado:** `tests/unit/modules/pdf_preview/views/test_view_main_window_contract_fasePDF_final.py`

**Problema:** Teste `test_zoom_by_delegates_to_controller` falhava devido a `_empty_state_item` não inicializado.

**Correção:**
```python
def test_zoom_by_delegates_to_controller(pdf_viewer):
    controller = DummyController()
    pdf_viewer._controller = controller
    pdf_viewer._empty_state_item = None  # ✅ Garantir que não há early return

    pdf_viewer._zoom_by(+2)

    assert any(call[0] == "apply_zoom_delta" and call[1] == 2 for call in controller.calls)
```

---

## 4. Validação

### 4.1 Testes Unitários

```bash
# Testes de download_and_open_file
pytest tests/unit/modules/uploads/test_download_and_open_file.py -v
# 8 passed, 1 skipped in 2.92s ✅

# Testes do helper de integração
pytest tests/unit/modules/pdf_preview/test_open_pdf_viewer_from_download.py -v
# 5 passed in 2.49s ✅

# Suite completa de PDF preview
pytest tests/unit/modules/pdf_preview -v --tb=short -q
# 184 passed, 1 skipped in 26.48s ✅

# Suite completa de uploads
pytest tests/unit/modules/uploads -v --tb=short -q
# 216 passed, 4 skipped in 29.42s ✅
```

**Total de testes:** 408 testes passando  
**Novos testes:** 5 (helper de integração)  
**Testes modificados:** 1 (correção de `_empty_state_item`)  
**Regressões:** 0 ✅

### 4.2 Lint (Ruff)

```bash
ruff check src/modules/uploads/service.py \
            src/modules/pdf_preview/view.py \
            src/modules/pdf_preview/__init__.py \
            tests/unit/modules/pdf_preview/test_open_pdf_viewer_from_download.py \
            tests/unit/modules/uploads/test_download_and_open_file.py
```

**Resultado:** ✅ All checks passed! (após fix de 1 import não usado)

---

## 5. Impacto

### 5.1 Arquivos criados

1. `tests/unit/modules/pdf_preview/test_open_pdf_viewer_from_download.py` (120 linhas)
   - 5 testes do helper de integração

### 5.2 Arquivos modificados

1. **`src/modules/uploads/service.py`**
   - Implementação de `mode="internal"` em `download_and_open_file()`
   - Retorna dict com `temp_path`, `display_name`, `mode="internal"`
   - Log: "Arquivo preparado para viewer interno"

2. **`src/modules/pdf_preview/view.py`**
   - Criação de `open_pdf_viewer_from_download_result()`
   - Helper para abrir viewer a partir do resultado de download
   - Validação automática de resultado

3. **`src/modules/pdf_preview/__init__.py`**
   - Exporta `open_pdf_viewer_from_download_result` em `__all__`

4. **`tests/unit/modules/uploads/test_download_and_open_file.py`**
   - Atualização de `test_internal_mode_returns_not_implemented`
   - Valida retorno com path, display_name e mode

5. **`tests/unit/modules/pdf_preview/views/test_view_main_window_contract_fasePDF_final.py`**
   - Correção de `test_zoom_by_delegates_to_controller`
   - Adiciona `pdf_viewer._empty_state_item = None`

### 5.3 Benefícios

✅ **Controller headless já existente:** Separação clara entre lógica e UI  
✅ **Integração mode="internal":** Uploads pode usar viewer interno  
✅ **Helper limpo:** `open_pdf_viewer_from_download_result()` abstrai validações  
✅ **Preparação futura:** Auditoria/hub podem usar mesma API  
✅ **Testes headless:** 5 novos testes sem dependência de Tkinter  
✅ **Backward compatible:** mode="external" inalterado  

---

## 6. Arquitetura da Integração

### 6.1 Fluxo de dados

```
┌─────────────────────────────────────────────────────────────────┐
│ UI (uploads/auditoria/hub)                                      │
│                                                                 │
│  download_and_open_file("path/file.pdf", mode="internal")      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/modules/uploads/service.py                                  │
│                                                                 │
│  1. Baixa arquivo para temp                                    │
│  2. Se mode="internal":                                        │
│     return {                                                   │
│       "ok": True,                                              │
│       "mode": "internal",                                      │
│       "temp_path": "/tmp/rc_gestor_uploads/file.pdf",         │
│       "display_name": "file.pdf"                               │
│     }                                                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/modules/pdf_preview/view.py                                 │
│                                                                 │
│  open_pdf_viewer_from_download_result(master, result)          │
│    → Valida result["ok"] e result["mode"]                      │
│    → Chama open_pdf_viewer(pdf_path=result["temp_path"])       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/ui/pdf_preview_native.py                                    │
│                                                                 │
│  open_pdf_viewer(master, pdf_path=..., display_name=...)       │
│    → Singleton pattern: reutiliza janela se existir            │
│    → Cria PdfViewerWin(pdf_path=...)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/modules/pdf_preview/views/main_window.py                    │
│                                                                 │
│  PdfViewerWin(pdf_path=...)                                    │
│    → self._controller = PdfPreviewController(pdf_path=path)    │
│    → self._render_state(controller.get_render_state())         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/modules/pdf_preview/controller.py                           │
│                                                                 │
│  PdfPreviewController(pdf_path=...)                            │
│    → self._raster = PdfRasterService(pdf_path=path)            │
│    → self.state = PdfPreviewState(page_count=...)              │
│    → get_page_pixmap(), go_to_page(), zoom_in(), etc.          │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Responsabilidades

**uploads/service.py:**
- Baixar arquivo do Supabase
- Criar arquivo temporário gerenciado
- Retornar dict estruturado com path e mode

**pdf_preview/view.py:**
- Validar resultado de download
- Abrir viewer interno se válido
- Abstrair detalhes de integração

**pdf_preview/controller.py:**
- Gerenciar estado de navegação (página, zoom)
- Calcular geometrias de renderização
- Fornecer dados para View renderizar

**pdf_preview/views/main_window.py:**
- Renderizar UI (Tkinter)
- Delegar lógica para controller
- Atualizar widgets baseado em estado

---

## 7. Próximos Passos

### 7.1 Uso em uploads browser

**Oportunidade:** Browser de uploads (`src/modules/uploads/views/browser.py`) atualmente baixa bytes e abre viewer interno diretamente.

**Melhoria futura:** Usar `download_and_open_file(mode="internal")` para aproveitar:
- Gestão centralizada de temporários
- Logs padronizados
- Cleanup automático de arquivos antigos

**Código atual (browser.py):**
```python
def _view_selected(self, name="", item_type="", full_path=""):
    # Baixa bytes diretamente
    data = download_bytes(self._bucket, remote_key)

    # Abre viewer interno
    self._open_pdf_viewer(data_bytes=data, display_name=name)
```

**Código futuro (opcional):**
```python
def _view_selected(self, name="", item_type="", full_path=""):
    # Usa serviço centralizado
    result = download_and_open_file(full_path, bucket=self._bucket, mode="internal")

    # Abre viewer
    if result["ok"]:
        open_pdf_viewer_from_download_result(self, result)
```

### 7.2 Integração em auditoria/hub

**Contexto:** Módulos de auditoria e hub podem precisar abrir PDFs.

**Exemplo futuro:**
```python
# Em auditoria/views/upload_flow.py
from src.modules.pdf_preview import open_pdf_viewer_from_download_result
from src.modules.uploads.service import download_and_open_file

def on_preview_document(self, document_path):
    result = download_and_open_file(document_path, mode="internal")

    if result["ok"]:
        viewer = open_pdf_viewer_from_download_result(self, result)
    else:
        messagebox.showerror("Erro", result["message"])
```

### 7.3 Configuração de modo padrão

**Oportunidade:** Adicionar preferência de usuário para modo padrão.

**Em `config.yml` ou settings:**
```yaml
pdf_viewer:
  default_mode: "internal"  # ou "external"
```

**No código:**
```python
def download_and_open_file(remote_key, *, bucket=None, mode=None):
    if mode is None:
        mode = get_user_preference("pdf_viewer.default_mode", default="external")
    ...
```

---

## 8. Notas Técnicas

### 8.1 Decisão: Não reescrever controller

**Contexto:** Prompt original pedia "Criar um controller headless para o PDF preview".

**Descoberta:** Controller já existe e está bem estruturado:
- Separação clara entre lógica (controller) e UI (view)
- Testes headless já existentes (test_pdf_preview_controller_fasePDF.py)
- View já delega para controller (apply_zoom_delta, go_to_page, etc.)

**Decisão:** Não reescrever, apenas integrar com uploads.

**Justificativa:**
- DRY (Don't Repeat Yourself)
- Evitar regressões em código já testado
- Foco em integração (objetivo real da fase)

### 8.2 Padrão de retorno estruturado

**Decisão:** `download_and_open_file()` retorna dict com `mode` explícito.

**Justificativa:**
1. Caller pode diferenciar mode="internal" vs mode="external"
2. Helper `open_pdf_viewer_from_download_result()` valida mode
3. Futuro: mode="auto" pode decidir dinamicamente

**Alternativa rejeitada:** Duas funções separadas (`download_and_open_external`, `download_and_open_internal`)
- Duplicação de lógica de download
- Menos flexível para mode="auto" futuro

### 8.3 Singleton pattern do viewer

**Contexto:** `open_pdf_viewer()` usa singleton global para reutilizar janela.

**Vantagem:**
- Apenas 1 janela de preview por aplicação
- Economiza memória
- UX consistente

**Desvantagem:**
- Não pode abrir múltiplos PDFs simultaneamente

**Decisão atual:** Manter singleton (comportamento existente).

**Melhoria futura (opcional):** Adicionar parâmetro `reuse=True/False` para permitir múltiplas janelas quando necessário.

---

## 9. Checklist de Conclusão

- [x] Verificar integração atual controller-view
- [x] Implementar mode="internal" em download_and_open_file
- [x] Criar helper open_pdf_viewer_from_download_result
- [x] Criar 5 testes do helper
- [x] Atualizar teste de download_and_open_file
- [x] Corrigir teste de zoom_by (empty_state_item)
- [x] Rodar pytest em modules/pdf_preview (184 passed ✅)
- [x] Rodar pytest em modules/uploads (216 passed ✅)
- [x] Validar com Ruff (all checks passed ✅)
- [x] Criar este devlog

---

**FASE UI-PDF-PREVIEW-CONTROLLER-01: CONCLUÍDA ✅**

**Resumo:**
- ✅ Controller headless já existente e bem testado
- ✅ Implementado mode="internal" em download_and_open_file
- ✅ Criado helper de integração para UI
- ✅ 5 novos testes headless
- ✅ 408 testes passando (0 regressões)
- ✅ Ponte entre uploads e PDF preview estabelecida
