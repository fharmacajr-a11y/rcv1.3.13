# MS-33 – Decisões de batch no controller headless

## Resumo executivo
A lógica de validação e confirmação das operações em lote (excluir, restaurar, exportar) estava concentrada na view (`main_screen.py`). Isso dificultava testes e mantinha regras de negócio acopladas ao Tkinter. Nesta fase, criei decisões headless no controller para que a view apenas traduza o resultado em diálogos e invoque o coordenador de batch.
Agora o controller expõe `BatchDecision` e funções `decide_batch_delete/restore/export` que encapsulam regras, mensagens e fluxos (noop, warning, confirmação e execução direta). A view passa o estado (seleção, online, trash flag) e mantém apenas UI e chamadas concretas ao `BatchOperationsCoordinator`, preservando o comportamento observado pelo usuário.

## Decisões de batch centralizadas
- `main_screen_controller.py`: adicionados `BatchDecision` e as funções `decide_batch_delete/restore/export`, com mensagens idênticas às usadas na view e regras atuais (inclui contagem na confirmação de delete e validações por operação). Uso das funções de validação de `batch_operations` para manter mensagens e patchability nos testes.
- Mantido o restante do controller headless intacto (filtros/ordem, estados de botões).

## Como a view interpreta `BatchDecision`
- `main_screen.py` agora chama `decide_batch_*` com o estado corrente (seleção, `is_online`, `is_trash_screen`).
- Fluxo na view:
  - `noop`: retorna silenciosamente (mesmo comportamento sem seleção).
  - `warning`: mostra `messagebox.showwarning("Operação não permitida", message)`.
  - `confirm`: mostra `messagebox.askyesno` com o texto retornado; só então executa.
  - `execute`: executa direto (export) sem confirmação.
- Execução continua via `_invoke_safe` chamando o `BatchOperationsCoordinator` e exibindo os mesmos diálogos de sucesso/parcial/erro.

## Estrutura de `BatchDecision`
| Campo | Significado |
| --- | --- |
| `kind` | `"noop"` (não faz nada), `"warning"` (exibe alerta e sai), `"confirm"` (pede confirmação), `"execute"` (pode executar direto) |
| `message` | Texto para alerta ou confirmação (mantém mensagens existentes) |
| `operation` | `"delete"`, `"restore"` ou `"export"` para identificar a ação associada |

## Arquivos alterados
- `src/modules/clientes/views/main_screen_controller.py`: adicionados `BatchDecision` e decisões de batch; validações reutilizam `batch_operations`.
- `src/modules/clientes/views/main_screen.py`: handlers de batch passam a consumir `BatchDecision`, mantendo apenas UI e chamadas ao coordenador.
- `devlog-main-screen-controller-ms33.md`: este devlog.

## Testes
- `pytest tests/unit/modules/clientes/controllers/test_main_screen_actions_ms25.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_batch_logic_fase07.py -q` ✅
- `pytest tests/unit/modules/clientes/ -k "batch or lixeira or delete or restore or export" -q` ✅

MS-33 concluída, decisões de batch centralizadas no controller, comportamento preservado; todos os testes deste módulo passaram.
