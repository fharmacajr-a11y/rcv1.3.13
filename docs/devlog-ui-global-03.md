# UI-GLOBAL-03 – Centralização de diálogos globais

## Escopo
- Centralizar os diálogos “globais” do app (Config/Storage, Sobre/Ajuda, utilitários e módulos auxiliares) com `show_centered`.
- Classes/diálogos ajustados:
  - Lixeira (`abrir_lixeira` e diálogo de espera de purge)
  - Diálogos genéricos (`custom_dialogs.show_info` / `ask_ok_cancel`)
  - Storage Destination & progresso de upload (`StorageDestinationDialog`, loader em `storage_uploader.py`)
  - Conversor PDF (`PDFDeleteImagesConfirmDialog`, `PDFConversionResultDialog`, além do progresso batch)
  - BusyDialog (`src/ui/components/progress_dialog.py`)
  - Subpastas globais (`src/ui/subpastas_dialog.py`)
  - Navegador de uploads (`UploadsBrowserWindow`) e progress dialog (`src/modules/uploads/uploader_supabase.py`)
  - Tela de senhas (`PasswordDialog`, `ClientPasswordsDialog`)
  - ChatGPTWindow
  - Visualizador de PDFs (`PdfViewerWin`)
  - Lixeira/Auditoria (`UploadProgressDialog`, `DuplicatesDialog`)

## Alterações
- Todos os diálogos acima passam a importar `show_centered` e chamá-lo durante a inicialização, removendo geometrias manuais (`center_window`, `_center_on_parent`, cálculos de `geometry`).
- Lixeira agora centraliza tanto a janela principal quanto o diálogo “Aguarde” do purge com o helper global.
- Diálogos que escondiam/mostravam manualmente (`withdraw/deiconify`) mantêm somente o `show_centered`, reduzindo flicker.
- Visualizador de PDFs e Uploads Browser definem o tamanho desejado com `geometry()` e deixam o posicionamento para `show_centered`.

## QA
- `pytest tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase01.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase03.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -v`
- `ruff check` em todos os arquivos globais modificados (`src/ui/**`, `src/modules/lixeira/**`, `src/modules/uploads/**`, `src/modules/passwords/**`, `src/modules/chatgpt/views/chatgpt_window.py`, `src/modules/pdf_preview/views/main_window.py`, `src/modules/auditoria/views/dialogs.py`)
- `pyright src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py src/ui/window_utils.py`

## Verificação Manual
- Ao rodar `python -m src.app_gui`, validar:
  - Janela da Lixeira + diálogo “Aguarde”
  - Diálogos `show_info`/`ask_ok_cancel` (Menu Ajuda / prompts gerais)
  - Storage Destination + janela de progresso (`Enviar para Supabase`)
  - Conversor PDF (confirmação/resultado + progresso em lote)
  - BusyDialog (operações bloqueantes)
  - Subpasta global (`src/ui/subpastas_dialog.py`)
  - Navegador de uploads e progress dialog
  - PasswordDialog + ClientPasswordsDialog
  - ChatGPTWindow
  - Visualizador de PDFs
  - Dialogs de Auditoria (upload progress, duplicatas)
