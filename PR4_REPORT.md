# PR4 - Hub Layout Extraction

## Arquivos criados/alterados
- gui/hub_screen.py
- ui/hub/__init__.py
- ui/hub/constants.py
- ui/hub/layout.py

## Linhas removidas de gui/hub_screen.py
- 13 linhas substituídas por chamadas ao layout externo.

## Widgets esperados pelo layout
- `modules_panel` — criado em `HubScreen.__init__` como `self.modules_panel`.
- `spacer` — frame central `self.center_spacer` instanciado em `HubScreen.__init__`.
- `notes_panel` — labelframe atribuído em `HubScreen._build_notes_panel` como `self.notes_panel`.

## Declaração
**Nenhuma lógica foi movida/alterada; apenas grid/constantes.**
