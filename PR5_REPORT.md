# PR5 - Split ui/components.py

## Arquivos criados/alterados
- ui/components.py
- ui/components/__init__.py
- ui/components/buttons.py
- ui/components/inputs.py
- ui/components/lists.py
- ui/components/modals.py
- ui/components/misc.py

## Mapa de símbolos
- `MenuComponents`, `StatusIndicators`, `create_menubar`, `create_status_bar`, `get_whatsapp_icon`, `draw_whatsapp_overlays` → ui/components/misc.py
- `SearchControls`, `labeled_entry`, `create_search_controls` → ui/components/inputs.py
- `FooterButtons`, `toolbar_button`, `create_footer_buttons` → ui/components/buttons.py
- `create_clients_treeview` → ui/components/lists.py
- (Nenhum símbolo em modals.py por ora; reservado para futuros diálogos.)

## Compatibilidade
- O pacote `ui.components` reexporta todos os símbolos via `ui/components/__init__.py`.
- O arquivo ponte `ui/components.py` permanece importável e reexporta dos submódulos.
- `from ui.components import ...` continua funcionando sem alterações no restante do projeto.
