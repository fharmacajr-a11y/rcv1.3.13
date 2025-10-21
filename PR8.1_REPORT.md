# PR8.1 - Hotfix gui.main_window App export

## Mudanças
- Nova unidade gui/main_window/app.py contendo a classe App (composition root).
- gui/main_window/__init__.py reexporta App, mantendo create_frame, 
avigate_to, 	k_report.
- gui/main_window.py removido em favor do pacote.

## Compatibilidade
- rom gui.main_window import App agora funciona (testado import).
- python -m py_compile em todo o projeto passou.

## Notas
- Nenhum comportamento alterado; logs originais preservados na classe App.
