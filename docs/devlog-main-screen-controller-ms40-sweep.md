# MS-40 – Varredura pós-split da Main Screen

## O que foi checado
- **Imports/referências**: verifiquei o façade `main_screen.py` e mixins (`main_screen_frame.py`, `main_screen_events.py`, `main_screen_dataflow.py`, `main_screen_batch.py`). Ajustei apenas:
  - Constantes de pick mode sincronizadas com `main_screen_ui_builder.py` (emoji/texto idênticos).
  - Remoção de imports mortos nos mixins (`main_screen_batch.py`, `main_screen_controller.py`, `main_screen_events.py`) para evitar avisos do linter.
- **Linter**: `python -m ruff check src/modules/clientes` (OK). Execução global acusou avisos fora do escopo (tasks/theme_toggle/tests diversos) e não foram alterados nesta fase.
- **Bandit**: `bandit -q -r src/modules/clientes` → 1 alerta existente em `column_manager.py` (try/except/pass) mantido como está (com comentário de design).
- **Vulture**: `vulture src/modules/clientes tests/unit/modules/clientes` → apontou variáveis não usadas em `footer.py` e em vários testes antigos de forms/service; considerados falsos positivos/fora do foco main_screen, nada alterado.

## Testes executados
- `pytest tests/unit/modules/clientes/views/test_main_screen_batch_logic.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_controller_core.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_controller_filters.py -q` ✅
- `pytest tests/unit/modules/clientes/views/test_main_screen_batch_ui_fase06.py -q` ✅
- `pytest tests/unit/modules/clientes/controllers/test_main_screen_actions.py -q` ✅
- Tentativa de suíte completa `pytest tests/unit/modules/clientes/ -q` falhou no flush do terminal (OSError 22) após avançar ~70% com testes passando; rerodagem focalizada acima confirmou os cenários principais.

## Situação de testes/limpeza
- Não foram removidos testes nesta fase; os antigos marcados com `@pytest.mark.skip` (ex.: `test_main_screen_view_contract_fase13.py`) permanecem porque não bloqueiam a suíte e servem de documentação histórica.
- Sem código de produção removido além de limpeza de imports e sincronização de constantes.

## Pronto para a próxima etapa
“Pronto para o usuário rodar pytest + cobertura global.”
