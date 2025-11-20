# Modulo Main Window - Overview

## Responsabilidades
- Inicializar a janela principal (`App`) com tema, menubar e topbar, aplicando politicas de janela e hidpi.
- Orquestrar navegacao entre Hub/Notas, Clientes, Auditoria, Senhas e placeholders via `NavigationController`.
- Integrar servicos centrais (auth, status monitor, supabase uploader, temas) e callbacks de menu/toolbar.
- Expor funcao de criacao de frames com cache de telas pesadas (Hub e Senhas) para evitar flicker.

## Situacao atual
- Codigo principal vive em `src/modules/main_window/`:
  - `controller.py` agrupa `create_frame`, `navigate_to` e `tk_report` (log de excecoes Tk).
  - `views/main_window.py` contem a classe `App` (ttkbootstrap.Window) com topbar, menu, binds e handlers.
- Pacote `src/ui/main_window/` virou shim fino que apenas reexporta `App`, `create_frame`, `navigate_to` e `tk_report` para manter a API publica anterior.
- `src/app_gui.py` continua importando `App` de `src.ui.main_window`, sem mudancas de comportamento.

## Arquivos principais
- `src/modules/main_window/views/main_window.py`: UI principal, montagem da janela, status/menus, binds globais e handlers de acoes.
- `src/modules/main_window/controller.py`: helper para criar frames (com cache do Hub) e roteador `navigate_to` para destinos conhecidos.
- `src/ui/main_window/{app,frame_factory,router,tk_report}.py`: shims que delegam para o modulo `src/modules/main_window` mantendo compatibilidade.

## Riscos / pontos de atencao
- Dependencia em serviços globais (Supabase, profiles, app_core) e fallbacks inline (resource_path, sha256_file, only_digits) permanecem no App.
- Caches de instancias (Hub, Senhas) mantidos no App; mudar lifecycle pode quebrar a UX esperada.
- NavigationController ainda manipula widgets diretamente (pack/place) e usa `_current` internamente; alterar assinatura pode impactar varias telas.
