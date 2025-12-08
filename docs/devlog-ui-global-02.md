# UI-GLOBAL-02 – Centralização de diálogos de Cliente

## Escopo
- Garantir que todos os diálogos relacionados ao módulo Clientes abram já centralizados usando `show_centered`.
- Diálogos ajustados:
  - Formulário de cliente (`form_cliente`)
  - Seletor de clientes (`ClientPicker`)
  - Subpastas do cliente (`open_subpastas_dialog`)
  - Prompt de subpasta (`SubpastaDialog` em `client_subfolder_prompt`)
  - Diálogo de progresso do fluxo de upload de clientes (`UploadProgressDialog` em `_upload.py`)

## Alterações
- `src/modules/clientes/forms/client_form.py`
  - Remove lógica manual `_center_editor_window` e ativa `show_centered(win)` após montar o formulário.
- `src/modules/clientes/forms/client_picker.py`
  - Substitui `_center_window` por chamada direta a `show_centered(self)`.
- `src/modules/clientes/forms/client_subfolders_dialog.py`
  - Remove fallback `center_on_parent` e centraliza o `tb.Toplevel` com `show_centered`.
- `src/modules/clientes/forms/client_subfolder_prompt.py`
  - Importa `show_centered`, dropa `center_on_parent` e confia no helper global para posicionar o prompt.
- `src/modules/clientes/forms/_upload.py`
  - Centraliza `UploadProgressDialog` com `show_centered` e mantém apenas `minsize` manual.

## QA
- `pytest tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase01.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase03.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -v`
- `ruff check` sobre os arquivos modificados em `src/modules/clientes/forms/`
- `pyright src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py src/ui/window_utils.py`

## Verificação Manual
- Abrir o app (`python -m src.app_gui`) e validar visualmente:
  - Formulário Novo/Editar Cliente (abre centralizado)
  - ClientPicker (modal para selecionar cliente)
  - Subpastas do cliente (dialog `open_subpastas_dialog`)
  - Prompt de subpasta (texto + campos)
  - Progresso de upload (ao enviar documentos)
