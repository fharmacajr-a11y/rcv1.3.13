# QA-DELTA-37: ClientFilesPack-02 - toolbar e exclusão

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Escopo
- Browser de arquivos aberto pelo módulo Clientes volta a exibir o prefixo Supabase: ... na barra superior (sem setas).
- Foram adicionados os botões Excluir arquivo(s) e Excluir pasta apenas para Clientes, com confirmação e validação de prefixo.
- Auditoria mantém layout e comportamento anteriores.

## Alterações
- src/ui/files_browser.py
  - Prefix label sempre visível; setas continuam apenas para Auditoria.
  - Novos botões de exclusão para Clientes com handlers _on_delete_files e _on_delete_folder, usando confirmações, logging e atualização imediata da lista.
  - Helpers _full_path_from_rel/_collect_files_under_prefix garantem que a exclusão fique restrita ao prefixo do cliente.

## Validações
`
Ruff   src/ui data: OK
Flake8 src/ui data: OK
Pyright src/ui data: OK
`

Execução do app (python -m src.app_gui) não realizada aqui; validação visual ficará com o usuário.
