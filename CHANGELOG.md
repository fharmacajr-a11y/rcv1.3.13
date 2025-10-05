# Changelog

## v20
- Modularização em subpacotes (sem renomear arquivos): 
  - core/{auth, db_manager, session, search, classify_document}/
  - ui/{login, forms, lixeira, users, menu}/
  - utils/{file_utils, helpers, themes}/
  - config/configuracoes/
- `__init__.py` criado em todos os pacotes, reexportando os módulos originais.
- Menubar no topo (Arquivo → Sair, Admin → Gerenciar Usuários, Ajuda → Sobre/Changelog).
- Botão Refresh já existia (↻) chamando `self._on_refresh()` — mantido.
- Rodar com `python main.py`.

## v19
- Base consolidada (estrutura original).


## v1.3.6-fixed — 2025-10-03
- Corrigido uso inconsistente de `log`/`logger`:
  - Adicionado alias `log = logger` em módulos que usavam ambos.
  - Arquivos ajustados: app_core.py, app_gui.py, core/services/lixeira_service.py, ui/forms/forms.py, ui/lixeira/lixeira.py, utils/pdf_reader.py
- Verificado todos os .py com `py_compile`: nenhum erro de sintaxe.
- Pronto para rodar via `main.py` com `APP_LOG_LEVEL` configurável (DEBUG/INFO).
