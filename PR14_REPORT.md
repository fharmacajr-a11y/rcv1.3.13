# PR14 — helpers de autor

- **Funções movidas:** `_author_display_name` → `gui/hub/authors.py`; `_debug_resolve_author` → `gui/hub/authors.py`.
- **Linhas removidas em `gui/hub_screen.py`:** retirada das definições originais dos helpers dentro de `HubScreen` (trecho que começava nas antigas linhas ~640–740) e atualização das chamadas para usar o módulo novo.
- **Confirmação:** as funções em `gui/hub/authors.py` não fazem acesso direto a `self`; recebem a instância como parâmetro `screen` e operam apenas com dados fornecidos.
- **Resultados dos comandos:**
  - `python -c '…py_compile…'` → OK (`OK: py_compile`)
  - `python scripts/dev_smoke.py` → OK (`SMOKE: OK`)

