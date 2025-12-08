| ID | Arquivo | Linha | Regra | Severidade | Comentário inicial |
| -- | ------- | ----- | ----- | ---------- | ------------------ |
| 1 | src/modules/clientes/forms/client_picker.py | 182 | B110 | Low | Corrigido em SEC-001 – try/except/pass trocado por `log.exception`. |
| 2 | src/modules/main_window/app_actions.py | 119 | B110 | Low | Corrigido em SEC-001 – fallback registra `logger.exception` para src.ui.lixeira. |
| 3 | src/modules/main_window/app_actions.py | 127 | B110 | Low | Corrigido em SEC-001 – fallback registra `logger.exception` para src.modules.lixeira. |
| 4 | src/modules/main_window/app_actions.py | 135 | B110 | Low | Corrigido em SEC-001 – fallback registra `logger.exception` para views.lixeira. |
| 5 | src/modules/uploads/upload_retry.py | 308 | B101 | Low | Corrigido em SEC-001 – assert substituído por checagem `if` + `RuntimeError`. |
