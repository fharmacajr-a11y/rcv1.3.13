# Devlog – Fase PDF FINAL

## Resumo
- Ampliei a cobertura de `PdfViewerWin` com dummies headless, garantindo que zoom, toggle de texto e downloads realmente delegam ao `PdfPreviewController`/services e que os botões de download refletem o helper `calculate_button_states`.
- Criei uma suíte de widgets (`PdfToolbar`, `PdfPageView`, `PdfTextPanel`) que valida callbacks, bindings e fluxos de texto/zoom totalmente sem Tk real complexo (skip automático via `require_tk`).
- Adicionei smoke-tests para o bridge `src/ui/pdf_preview_native.open_pdf_viewer`, cobrindo reutilização do singleton, reaproveitamento de janela existente e reset seguro no evento `<Destroy>`.

## QA executado
- `python -m pytest tests/unit/modules/pdf_preview -v --no-cov`
- `python -m pytest tests/unit/ui/test_pdf_preview_native_fasePDF_final.py -v --no-cov`
- `ruff check src/modules/pdf_preview src/ui/pdf_preview_native.py tests/unit/modules/pdf_preview tests/unit/ui/test_pdf_preview_native_fasePDF_final.py`
- `pyright src/modules/pdf_preview src/ui/pdf_preview_native.py tests/unit/modules/pdf_preview tests/unit/ui/test_pdf_preview_native_fasePDF_final.py`
- `bandit -q -r src/modules/pdf_preview src/utils/pdf_reader.py src/ui/pdf_preview_native.py`

## Arquivos principais
- `tests/unit/modules/pdf_preview/views/conftest.py`
- `tests/unit/modules/pdf_preview/views/test_view_main_window_contract_fasePDF_final.py`
- `tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py`
- `tests/unit/ui/test_pdf_preview_native_fasePDF_final.py`
- `oks/devlog/devlog_pdf_preview_fase14_final.md`

## Observações
- Os testes headless dependem de `require_tk`; em ambientes sem Tk, ficam marcados como `skipped` com mensagem clara e não travam o CI.
- O comportamento visual continua o mesmo (incluindo a piscada ao carregar); o foco aqui foi travar o contrato entre view/controller/serviços.
