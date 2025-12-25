Cobertura total (statements): 69.45%
Statements: 21198/30521

== Resumo por raiz (weighted por statements) ==
Pasta | Arquivos | Statements | Miss | Cobertura
---|---:|---:|---:|---:
src | 425 | 28841 | 9250 | 67.9%
security | 2 | 59 | 5 | 91.5%
data | 4 | 363 | 28 | 92.3%
infra | 22 | 1050 | 39 | 96.3%
adapters | 5 | 208 | 1 | 99.5%

== Sub-resumo do src (por 1º subpacote) ==
Pasta | Arquivos | Statements | Miss | Cobertura
---|---:|---:|---:|---:
src/app_gui.py | 1 | 123 | 99 | 19.5%
src/ui | 75 | 3157 | 1532 | 51.5%
src/modules | 251 | 20729 | 7306 | 64.8%
src/cli.py | 1 | 20 | 3 | 85.0%
src/utils | 27 | 1392 | 160 | 88.5%
src/core | 44 | 2395 | 129 | 94.6%
src/features | 8 | 314 | 12 | 96.2%
src/helpers | 6 | 142 | 5 | 96.5%
src/app_core.py | 1 | 201 | 3 | 98.5%
src/shared | 3 | 117 | 1 | 99.1%
src/__init__.py | 1 | 10 | 0 | 100.0%
src/app_status.py | 1 | 122 | 0 | 100.0%
src/app_utils.py | 1 | 49 | 0 | 100.0%
src/config | 4 | 62 | 0 | 100.0%
src/version.py | 1 | 8 | 0 | 100.0%

== TOP 30 oportunidades (NÃO-GUI, exclui src/ui, min 25 stmts; ordenado por miss) ==
Miss | Stmts | % | Arquivo
---:|---:|---:|---
609 | 692 | 9.7% | src\modules\pdf_preview\views\main_window.py
280 | 330 | 12.1% | src\modules\auditoria\views\main_frame.py
278 | 302 | 6.9% | src\modules\lixeira\views\lixeira.py
273 | 291 | 4.9% | src\modules\anvisa\views\_anvisa_handlers_mixin.py
258 | 419 | 36.3% | src\modules\main_window\views\main_window_actions.py
229 | 271 | 12.8% | src\modules\passwords\views\passwords_screen.py
208 | 246 | 13.4% | src\modules\clientes\forms\client_picker.py
207 | 228 | 7.8% | src\modules\clientes\views\main_screen_ui_builder.py
176 | 218 | 15.4% | src\modules\clientes\views\main_screen_dataflow.py
169 | 321 | 44.2% | src\modules\uploads\views\browser.py
159 | 183 | 10.3% | src\modules\auditoria\views\upload_flow.py
158 | 330 | 48.3% | src\modules\main_window\views\main_window.py
152 | 179 | 12.3% | src\modules\passwords\views\password_dialog.py
146 | 176 | 15.6% | src\modules\anvisa\views\_anvisa_requests_mixin.py
144 | 281 | 44.3% | src\modules\anvisa\views\anvisa_screen.py
144 | 157 | 5.8% | src\modules\anvisa\views\_anvisa_history_popup_mixin.py
143 | 205 | 24.5% | src\modules\hub\views\hub_screen_view.py
136 | 224 | 33.8% | src\modules\clientes\forms\client_form_view.py
133 | 337 | 58.3% | src\modules\hub\views\hub_screen.py
131 | 208 | 35.4% | src\modules\clientes\views\main_screen_frame.py
127 | 192 | 25.2% | src\modules\uploads\views\file_list.py
127 | 187 | 27.1% | src\modules\clientes\forms\client_form.py
126 | 155 | 16.0% | src\modules\passwords\views\client_passwords_dialog.py
119 | 130 | 7.3% | src\modules\clientes\forms\client_subfolders_dialog.py
117 | 130 | 8.0% | src\modules\pdf_preview\views\pdf_viewer_actions.py
111 | 156 | 25.3% | src\modules\clientes\views\main_screen_events.py
111 | 131 | 14.2% | src\modules\tasks\views\task_dialog.py
107 | 124 | 11.5% | src\modules\clientes\views\obligation_dialog.py
106 | 115 | 6.4% | src\modules\auditoria\views\layout.py
99 | 123 | 16.8% | src\app_gui.py

== TOP 30 oportunidades (GUI, só src/ui, min 25 stmts; ordenado por miss) ==
Miss | Stmts | % | Arquivo
---:|---:|---:|---
170 | 200 | 14.0% | src\ui\splash.py
137 | 171 | 15.8% | src\ui\components\notifications\notifications_popup.py
131 | 131 | 0.0% | src\ui\widgets\autocomplete_entry.py
128 | 210 | 35.9% | src\ui\window_utils.py

== Arquivos .py existentes que NÃO aparecem no coverage.json (possível: nunca importados/executados) ==
- src/features/cashflow/dialogs.py
- src/features/cashflow/ui.py
- src/modules/anvisa/views/anvisa_footer.py
- src/modules/auditoria/view.py
- src/modules/cashflow/__init__.py
- src/modules/cashflow/service.py
- src/modules/cashflow/view.py
- src/modules/cashflow/views/__init__.py
- src/modules/cashflow/views/fluxo_caixa_frame.py
- src/modules/clientes/forms/client_form_new.py
- src/modules/clientes/forms/pipeline.py
- src/modules/main_window/views/main_window_bootstrap.py
- src/modules/main_window/views/main_window_layout.py
- src/modules/main_window/views/main_window_services.py
- src/modules/uploads/form_service.py
- src/ui/subpastas/dialog.py
