# DevLog - Main Screen MS-11: Test doubles e contrato UI/headless

**Branch:** `qa/fixpack-04`  
**Objetivo:** Criar fakes simples para `MainScreenStateLike` e `MainScreenComputedLike` e validar que a UI aceita Protocols sem depender das dataclasses concretas.

---

## Entregas
- Novos fakes dataclass reutilizaveis: `tests/unit/modules/clientes/views/main_screen_doubles_ms11.py`.
- Novos testes contratuais headless+UI: `tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py`, com monkeypatch do `ClientesViewModel` para evitar dependencias reais e chamadas diretas aos metodos `_refresh_with_controller` e `_update_ui_from_computed`.
- Nenhuma mudanca de logica em `main_screen.py`, controller ou helpers; apenas utilizacao dos Protocols existentes.

## Testes e lint
- `pytest tests\unit\modules\clientes\views\test_main_screen_contract_ms11.py -v` → 2 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_controller_ms1.py -v` → 21 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_controller_filters_ms4.py -v` → 26 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_helpers_fase01.py -v` → 35 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_helpers_fase02.py -v` → 53 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_helpers_fase03.py -v` → 53 passed.
- `pytest tests\unit\modules\clientes\views\test_main_screen_helpers_fase04.py -v` → 46 passed.
- Observacao: o comando unico com todos os arquivos abortou por OSError ao dar flush no stdout; rodando os arquivos individualmente todos os alvos passaram.
- `ruff check src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py tests/unit/modules/clientes/views/main_screen_doubles_ms11.py tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py` → All checks passed.
- Pyright (config do repo) ainda lista ruidos antigos de Tkinter em `main_screen.py`; novos arquivos de teste estao limpos e nenhuma nova queixa relacionada aos Protocols foi introduzida.

## Estado final
- UI continua aceitando objetos que implementam `MainScreenStateLike` e `MainScreenComputedLike` via fakes simples; base pronta para testes UI/headless hibridos.
- Nao houve alteracao em comportamento ou layout.
- CF2 da Main Screen esta concluido, pronto para voce abrir o app e testar manualmente.
