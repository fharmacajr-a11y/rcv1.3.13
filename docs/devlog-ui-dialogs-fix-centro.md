## UI-DIALOGS-FIX-CENTRO – 2025-12-??

- Ajustamos a `ChatGPTWindow` (`src/modules/chatgpt/views/chatgpt_window.py`) para parar de chamar `geometry("700x500")` antes de `show_centered`. Agora usamos apenas `minsize(700, 500)` e deixamos `show_centered(self)` calcular a posição (mesmo padrão da Lixeira e Ver Subpastas).
- Rodamos um `grep` por `show_centered` e checamos os diálogos relevantes; não encontramos mais `geometry()` imediatamente antes do helper global. Os demais diálogos já seguem o padrão recomendado.
- Novas correções: tanto o `form_cliente` quanto o `ChatGPTWindow` forçam o uso do `winfo_toplevel()` do chamador como parent do `tk.Toplevel`, garantindo que `show_centered()` utilize a janela principal como referência (mesmo quando o fluxo parte de frames internos). O `open_chatgpt_window` agora resolve explicitamente o toplevel antes de instanciar o diálogo.

### Testes

- `pyright src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py src/ui/window_utils.py src/core/auth_bootstrap.py src/modules/main_window/views/main_window.py src/modules/chatgpt/views/chatgpt_window.py src/modules/clientes/forms/client_form.py`
- `ruff check src/modules/chatgpt/views/chatgpt_window.py src/modules/clientes/forms/client_form.py`
- `pytest tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase01.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase03.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -v`
