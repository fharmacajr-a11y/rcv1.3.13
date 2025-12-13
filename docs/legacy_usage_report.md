# Relatório de Uso de Módulos Legados (src.ui.*)

**Gerado em:** C:\Users\Pichau\Desktop\v1.4.26

---

## Imports diretos em src/ (43 arquivos)

### src/features/cashflow/dialogs.py

- Linha 14: `from src.ui.window_utils import show_centered`

### src/features/cashflow/ui.py

- Linha 12: `from src.ui.window_utils import show_centered`

### src/modules/auditoria/views/dialogs.py

- Linha 11: `from src.ui.components.progress_dialog import ProgressDialog`
- Linha 12: `from src.ui.window_utils import show_centered`

### src/modules/auditoria/views/upload_flow.py

- Linha 16: `from src.ui.dialogs.file_select import select_archive_file`

### src/modules/chatgpt/views/chatgpt_window.py

- Linha 10: `from src.ui.window_utils import show_centered`

### src/modules/clientes/forms/_prepare.py

- Linha 154: `from src.ui.forms.actions import SubpastaDialog`

### src/modules/clientes/forms/client_form.py

- Linha 18: `from src.ui.window_utils import center_on_parent as center_on_parent  # noqa: F401`
- Linha 28: `from src.ui.forms.actions import preencher_via_pasta as preencher_via_pasta  # noqa: F401`

### src/modules/clientes/forms/client_form_new.py

- Linha 17: `from src.ui.window_utils import center_on_parent as center_on_parent`
- Linha 23: `from src.ui.forms.actions import preencher_via_pasta as preencher_via_pasta`

### src/modules/clientes/forms/client_form_view.py

- Linha 23: `from src.ui.window_utils import show_centered`

### src/modules/clientes/forms/client_picker.py

- Linha 18: `from src.ui.components.progress_dialog import BusyDialog`
- Linha 19: `from src.ui.window_utils import show_centered`

### src/modules/clientes/forms/client_subfolder_prompt.py

- Linha 14: `from src.ui.window_utils import show_centered`

### src/modules/clientes/forms/client_subfolders_dialog.py

- Linha 16: `from src.ui.window_utils import show_centered`

### src/modules/clientes/views/footer.py

- Linha 12: `from src.ui.components import create_footer_buttons`

### src/modules/clientes/views/main_screen_ui_builder.py

- Linha 44: `from src.ui.components import create_clients_treeview`

### src/modules/clientes/views/toolbar.py

- Linha 11: `from src.ui.components import create_search_controls`

### src/modules/forms/view.py

- Linha 14: `from src.ui.forms.actions import download_file, list_storage_objects`

### src/modules/hub/views/hub_dashboard_view.py

- Linha 57: `from src.ui.widgets.scrollable_frame import ScrollableFrame`

### src/modules/hub/views/hub_screen_view.py

- Linha 249: `from src.ui.widgets.scrollable_frame import ScrollableFrame`

### src/modules/lixeira/views/lixeira.py

- Linha 22: `from src.ui.window_utils import show_centered`

### src/modules/login/view.py

- Linha 28: `from src.ui.login_dialog import LoginDialog`
- Linha 29: `from src.ui.splash import show_splash`

### src/modules/main_window/app_actions.py

- Linha 9: `from src.ui.dialogs.pdf_converter_dialogs import ask_delete_images, show_conversion_result`
- Linha 285: `from src.ui.progress.pdf_batch_progress import PDFBatchProgressDialog`

### src/modules/main_window/controller.py

- Linha 161: `from src.ui.placeholders import ComingSoonScreen`

### src/modules/main_window/views/main_window.py

- Linha 124: `from src.ui.menu_bar import AppMenuBar`
- Linha 125: `from src.ui.topbar import TopBar`
- Linha 126: `from src.ui.window_policy import apply_fit_policy`
- Linha 127: `from src.ui import custom_dialogs`
- Linha 338: `from src.ui.status_footer import StatusFooter`

### src/modules/passwords/views/client_passwords_dialog.py

- Linha 18: `from src.ui.window_utils import show_centered`

### src/modules/passwords/views/password_dialog.py

- Linha 18: `from src.ui.window_utils import show_centered`

### src/modules/pdf_preview/view.py

- Linha 15: `from src.ui.pdf_preview_native import PdfViewerWin, open_pdf_viewer as _open_pdf_viewer`

### src/modules/pdf_preview/views/main_window.py

- Linha 15: `from src.ui.window_utils import show_centered`
- Linha 16: `from src.ui.wheel_windows import wheel_steps`

### src/modules/pdf_preview/views/text_panel.py

- Linha 9: `from src.ui.search_nav import SearchNavigator`

### src/modules/tasks/views/task_dialog.py

- Linha 18: `from src.ui.window_utils import show_centered`

### src/modules/uploads/uploader_supabase.py

- Linha 26: `from src.ui.components.progress_dialog import ProgressDialog`
- Linha 27: `from src.ui.window_utils import show_centered`

### src/modules/uploads/views/browser.py

- Linha 29: `from src.ui.files_browser.utils import sanitize_filename, suggest_zip_filename`
- Linha 30: `from src.ui.window_utils import show_centered`

### src/modules/uploads/views/upload_dialog.py

- Linha 23: `from src.ui.components.progress_dialog import ProgressDialog`

### src/ui/__init__.py

- Linha 3: `from src.ui.utils import OkCancelMixin, center_on_parent, center_window`

### src/ui/components/progress_dialog.py

- Linha 11: `from src.ui.window_utils import show_centered`

### src/ui/custom_dialogs.py

- Linha 9: `from src.ui.window_utils import show_centered`

### src/ui/dialogs/__init__.py

- Linha 4: `from src.ui.dialogs.file_select import (`

### src/ui/dialogs/pdf_converter_dialogs.py

- Linha 8: `from src.ui.window_utils import show_centered`

### src/ui/forms/actions.py

- Linha 21: `from src.ui.components.upload_feedback import show_upload_result_message`

### src/ui/login/login.py

- Linha 7: `from src.ui.login_dialog import LoginDialog  # Login moderno com Supabase`
- Linha 22: `from src.ui.login_dialog import LoginDialog as ModernLoginDialog`

### src/ui/login_dialog.py

- Linha 175: `from src.ui.window_utils import show_centered`

### src/ui/progress/pdf_batch_progress.py

- Linha 10: `from src.ui.window_utils import show_centered`

### src/ui/subpastas_dialog.py

- Linha 15: `from src.ui.window_utils import show_centered`

### src/ui/widgets/__init__.py

- Linha 7: `from src.ui.widgets.busy import BusyOverlay`

## Imports diretos em tests/ (19 arquivos)

### tests/test_login_dialog_focus.py

- Linha 11: `from src.ui import login_dialog as login_dialog_module`

### tests/test_login_dialog_style.py

- Linha 11: `from src.ui import login_dialog as login_dialog_module`

### tests/test_login_dialog_window_state.py

- Linha 11: `from src.ui import login_dialog as login_dialog_module`

### tests/ui/components/test_progress_dialog.py

- Linha 5: `from src.ui.components.progress_dialog import ProgressDialog`

### tests/unit/modules/clientes/views/test_main_screen_batch_ui_fase06.py

- Linha 23: `from src.ui.components.buttons import create_footer_buttons`
- Linha 34: `from src.ui.components.buttons import create_footer_buttons`
- Linha 51: `from src.ui.components.buttons import FooterButtons`

### tests/unit/test_no_new_legacy_ui_imports.py

- Linha 67: `# Busca por: import src.ui ou from src.ui`

### tests/unit/ui/test_custom_dialogs.py

- Linha 1: `from src.ui import custom_dialogs`

### tests/unit/ui/test_file_select.py

- Linha 10: `from src.ui.dialogs.file_select import (`
- Linha 233: `from src.ui.dialogs.file_select import (`
- Linha 248: `from src.ui.dialogs import (`

### tests/unit/ui/test_files_browser_utils_fase11.py

- Linha 15: `from src.ui.files_browser.utils import (`

### tests/unit/ui/test_forms_deprecation.py

- Linha 14: `import src.ui.forms`
- Linha 31: `import src.ui.forms  # noqa: F401`

### tests/unit/ui/test_inputs_search_controls.py

- Linha 5: `from src.ui.components.inputs import PLACEHOLDER_FG, PLACEHOLDER_TEXT, create_search_controls`

### tests/unit/ui/test_login_dialog.py

- Linha 11: `from src.ui.login_dialog import LoginDialog`

### tests/unit/ui/test_pdf_preview_native_fasePDF_final.py

- Linha 9: `import src.ui.pdf_preview_native as pdf_native`

### tests/unit/ui/test_splash_layout.py

- Linha 6: `from src.ui.splash import (`

### tests/unit/ui/test_splash_style.py

- Linha 8: `from src.ui.splash import get_splash_progressbar_bootstyle`

### tests/unit/ui/test_splash_timing.py

- Linha 6: `from src.ui import splash as splash_module`

### tests/unit/ui/test_topbar_chatgpt_button.py

- Linha 3: `from src.ui.topbar import TopBar`

### tests/unit/ui/test_topbar_sites_button.py

- Linha 3: `from src.ui.topbar import TopBar`

### tests/unit/ui/test_upload_feedback.py

- Linha 5: `from src.ui.components.upload_feedback import (`

## Imports dinâmicos (literal) (1 arquivos)

### tests/unit/core/test_startup.py

- Linha 6: `import_module('src.ui.splash')`

## Ocorrências textuais (32 arquivos)

### src/app_core.py

- Linha 301: `for module_name in ("src.modules.lixeira", "src.ui.lixeira", "ui.lixeira"):`

### src/modules/clientes/components/helpers.py

- Linha 3: `Extraidos de src.ui.main_screen para reutilizacao e testes.`

### src/modules/clientes/forms/_prepare.py

- Linha 157: `"Erro ao importar SubpastaDialog: %s. Verifique src.ui.forms.actions.",`

### src/modules/forms/view.py

- Linha 3: `Este módulo encapsula a UI legada de formulários (`src.ui.forms`)`

### src/modules/login/view.py

- Linha 7: `- LoginDialog: aponta para src.ui.login_dialog.LoginDialog (login moderno com Su`
- Linha 11: `- src.ui.login.login.LoginDialog: wrapper deprecated, não usar em código novo`

### src/modules/main_window/views/main_window.py

- Linha 60: `- TopBar: Barra superior com botão Home (src.ui.topbar)`
- Linha 61: `- AppMenuBar: Menu principal (src.ui.menu_bar)`
- Linha 62: `- StatusFooter: Rodapé com status (src.ui.status_footer)`

### src/modules/pdf_preview/view.py

- Linha 4: `(`src.ui.pdf_preview_native`) e reexporta os entrypoints usados`

### src/modules/uploads/components/helpers.py

- Linha 3: `Extraidos de src.ui.files_browser para permitir reutilizacao e testes.`

### src/ui/forms/__init__.py

- Linha 1: `"""DEPRECATED: src.ui.forms está deprecated. Use src.modules.clientes.forms.`
- Linha 19: `"src.ui.forms.form_cliente está deprecated. Use src.modules.clientes.forms.form_`

### src/ui/forms/pipeline.py

- Linha 11: `"src.ui.forms.pipeline está deprecated. Use src.modules.clientes.forms.pipeline"`

### src/ui/hub/__init__.py

- Linha 9: `"src.ui.hub está deprecated. Use src.modules.hub",`

### src/ui/hub_screen.py

- Linha 9: `"src.ui.hub_screen está deprecated. Use src.modules.hub.views.hub_screen",`

### src/ui/lixeira/__init__.py

- Linha 9: `"src.ui.lixeira está deprecated. Use src.modules.lixeira.views.lixeira",`

### src/ui/lixeira/lixeira.py

- Linha 9: `"src.ui.lixeira.lixeira está deprecated. Use src.modules.lixeira.views.lixeira",`

### src/ui/login/login.py

- Linha 26: `"src.ui.login.login está deprecated. Use src.ui.login_dialog.LoginDialog",`
- Linha 37: `Use src.ui.login_dialog.LoginDialog diretamente.`
- Linha 42: `"LoginDialog da UI antiga está deprecated. Use src.ui.login_dialog.LoginDialog",`

### src/ui/main_screen.py

- Linha 11: `"src.ui.main_screen está deprecated. Use src.modules.clientes.views.main_screen"`

### src/ui/main_window/__init__.py

- Linha 11: `"src.ui.main_window está deprecated. Use src.modules.main_window",`

### src/ui/menu_bar.py

- Linha 8: `- Ou componentes de menu em src.ui.components/`

### src/ui/passwords_screen.py

- Linha 9: `"src.ui.passwords_screen está deprecated. Use src.modules.passwords.views.passwo`

### src/ui/subpastas_dialog.py

- Linha 4: `Backup caso src.ui.subpastas.dialog não esteja disponível.`

### src/ui/widgets/client_picker.py

- Linha 11: `"src.ui.widgets.client_picker está deprecated. Use src.modules.clientes.forms",`

### tests/conftest.py

- Linha 36: `"markers", "legacy_ui: marca testes que cobrem UI antiga (src.ui.*) - mantidos a`

### tests/modules/hub/test_hub_actions.py

- Linha 174: `monkeypatch.setitem(sys.modules, "src.ui.custom_dialogs", custom_dialogs)`

### tests/unit/core/test_app_core_fase03.py

- Linha 452: `assert "src.ui.lixeira" in import_attempts`
- Linha 466: `if name in ("src.modules.lixeira", "src.ui.lixeira", "ui.lixeira"):`
- Linha 503: `if name == "src.ui.lixeira":`

### tests/unit/core/test_startup.py

- Linha 6: `splash = import_module("src.ui.splash")`

### tests/unit/modules/clientes/forms/test_prepare_round12.py

- Linha 145: `with patch.dict("sys.modules", {"src.ui.forms.actions": None}):`
- Linha 158: `with patch("src.ui.forms.actions.SubpastaDialog") as MockDialog:  # noqa: N806`
- Linha 170: `with patch("src.ui.forms.actions.SubpastaDialog") as MockDialog:  # noqa: N806`

### tests/unit/modules/main_window/test_app_actions_fase45.py

- Linha 56: `progress_module = types.ModuleType("src.ui.progress.pdf_batch_progress")`
- Linha 59: `progress_pkg = types.ModuleType("src.ui.progress")`
- Linha 64: `monkeypatch.setitem(sys.modules, "src.ui.progress.pdf_batch_progress", progress_`
- Linha 65: `monkeypatch.setitem(sys.modules, "src.ui.progress", progress_pkg)`

### tests/unit/modules/main_window/test_main_window_controller_fase12.py

- Linha 347: `monkeypatch.setitem(sys.modules, "src.ui.placeholders", placeholder_module)`

### tests/unit/test_no_new_legacy_ui_imports.py

- Linha 2: `Teste de guarda: impede novos imports de src.ui.* (fora da allowlist).`
- Linha 57: `"""Encontra imports de src.ui.* no arquivo."""`
- Linha 76: `Teste de guarda: nenhum novo arquivo em src/ deve importar src.ui.*`
- Linha 98: `msg = ["\n❌ Encontrados imports de src.ui.* em arquivos não permitidos:\n"]`
- Linha 106: `"\n  1. Remova o import de src.ui.* deste arquivo"`

### tests/unit/ui/test_forms_deprecation.py

- Linha 1: `"""Testes para verificar que src.ui.forms emite DeprecationWarning quando usado.`
- Linha 9: `"""Acessar form_cliente via src.ui.forms deve emitir DeprecationWarning."""`
- Linha 17: `_ = src.ui.forms.form_cliente`
- Linha 22: `assert "src.ui.forms.form_cliente está deprecated" in str(w[0].message)`
- Linha 27: `"""Apenas importar src.ui.forms (sem acessar atributos) não deve emitir warning.`
- Linha 37: `if issubclass(warning.category, DeprecationWarning) and "src.ui.forms" in str(wa`

### tests/unit/ui/test_login_dialog.py

- Linha 43: `with patch("src.ui.login_dialog.get_supabase") as mock:`
- Linha 56: `with patch("src.ui.login_dialog.authenticate_user") as mock:`
- Linha 64: `with patch("src.ui.login_dialog._get_access_token") as mock:`
- Linha 72: `with patch("src.ui.login_dialog.bind_postgrest_auth_if_any") as mock:`
- Linha 79: `with patch("src.ui.login_dialog.refresh_current_user_from_supabase") as mock:`
- Linha 86: `with patch("src.ui.login_dialog.healthcheck") as mock:`
- Linha 94: `with patch("src.ui.login_dialog.prefs_utils") as mock:`
- Linha 102: `with patch("src.ui.login_dialog.resource_path") as mock:`
- Linha 110: `with patch("src.ui.login_dialog.messagebox") as mock:`
- Linha 734: `with patch("src.ui.login_dialog.resource_path") as mock:`
- _... e mais 10 ocorrências_

### tests/unit/ui/test_upload_feedback.py

- Linha 38: `@patch("src.ui.components.upload_feedback.messagebox.showinfo")`
- Linha 39: `@patch("src.ui.components.upload_feedback.messagebox.showerror")`
- Linha 40: `@patch("src.ui.components.upload_feedback.messagebox.showwarning")`
- Linha 57: `@patch("src.ui.components.upload_feedback.messagebox.showinfo")`
- Linha 58: `@patch("src.ui.components.upload_feedback.messagebox.showerror")`
- Linha 59: `@patch("src.ui.components.upload_feedback.messagebox.showwarning")`

---

## Resumo

- **Imports diretos em src/:** 43
- **Imports diretos em tests/:** 19
- **Imports dinâmicos:** 1
- **Ocorrências textuais:** 32

**Total de arquivos com referências a src.ui.*:** 95
