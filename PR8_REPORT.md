# PR8 - Split gui/main_window.py

## Arquivos criados/alterados
- gui/main_window.py
- gui/main_window/__init__.py
- gui/main_window/frame_factory.py
- gui/main_window/router.py
- gui/main_window/tk_report.py

## Linhas movidas
- Linhas removidas de gui/main_window.py: 195

## Conteúdo dos módulos
- frame_factory.py: lógica de criação/reuso de frames (equivalente ao antigo _frame_factory)
- router.py: centraliza navegação (
avigate_to) para hub, main, placeholders, senhas e picker de clientes
- tk_report.py: callback _tk_report para capturar exceções do Tkinter

## Confirmação
- APIs e logs preservados; sem mudança de comportamento.
