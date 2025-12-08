# Devlog – Fase PDF Preview

## Resumo
- Reforcei o `PdfPreviewController` com injeção opcional de raster service, clamps de zoom, estado de texto e utilitários `get_render_state`/`get_button_states` para expor o contrato headless.
- A view `PdfViewerWin` agora delega zoom/text updates ao controller (inclusive no debounce de roda e na atualização de labels) e registra logs em vez de `pass` silencioso.
- Criei a suíte `tests/unit/modules/pdf_preview/test_pdf_preview_controller_fasePDF.py` com dummies headless para validar navegação, zoom, texto, estados de botões e integração com pixmaps.

## QA executado
- `python -m pytest tests/unit/modules/pdf_preview -v --no-cov`
- `ruff check src/modules/pdf_preview/controller.py src/modules/pdf_preview/views/main_window.py tests/unit/modules/pdf_preview`
- `pyright src/modules/pdf_preview/controller.py src/modules/pdf_preview/views/main_window.py tests/unit/modules/pdf_preview`
- `bandit -q -r src/modules/pdf_preview src/utils/pdf_reader.py`
- `python -c "import fitz, os, tempfile, tkinter as tk; from src.modules.pdf_preview.views.main_window import PdfViewerWin; ..."`

## Arquivos principais
- `src/modules/pdf_preview/controller.py`
- `src/modules/pdf_preview/views/main_window.py`
- `tests/unit/modules/pdf_preview/test_pdf_preview_controller_fasePDF.py`
- `oks/devlog/devlog_pdf_preview_fase13.md`

## Observações
- Visual segue com piscada inicial (conforme combinado); o foco foi tornar navegação/zoom/texto determinísticos no controller.
- Reuso de janela/singleton permanece igual para ser tratado em fase futura.
