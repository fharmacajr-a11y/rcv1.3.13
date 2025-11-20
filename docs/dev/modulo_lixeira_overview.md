# Modulo Lixeira - Overview

## Responsabilidades
- Listar clientes excluídos (soft delete) com suporte a restauração e exclusão definitiva.
- Operar em modo singleton de janela (abre/foco se já aberta), com refresh externo opcional.
- Delegar operações de restauração/remoção ao serviço de clientes mantendo UX existente.

## Situacao atual
- Código principal da tela vive em `src/modules/lixeira/views/lixeira.py` (Toplevel + Treeview + ações).
- Wrappers/aliases em `src/modules/lixeira/view.py` expõem `abrir_lixeira`/`refresh_if_open` e `LixeiraFrame`.
- Shim em `src/ui/lixeira/` reexporta as funções do módulo para manter compatibilidade com imports legados.

## Arquivos principais
- `src/modules/lixeira/views/lixeira.py`: UI e handlers (restore/purge, refresh, carregamento, busy cursor).
- `src/modules/lixeira/view.py`: alias compatível para abertura da Lixeira via módulo.
- `src/modules/lixeira/service.py`: reexports do serviço de clientes relacionado à lixeira.
- `src/ui/lixeira/__init__.py` e `src/ui/lixeira/lixeira.py`: shims finos para a API antiga.

## Riscos / pontos de atencao
- Usa estado singleton `_OPEN_WINDOW`; alterações no ciclo de vida podem afetar refresh externo.
- Depende de serviços de clientes (Supabase/storage) diretamente; falhas de rede ainda exibem diálogos via messagebox.
- Manuseia JSON carregado de tags da Treeview; inputs malformados podem disparar exceções se estrutura mudar.
