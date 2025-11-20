# QA-DELTA-33: Navegação de arquivos de Clientes

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Arquivos alterados
- src/ui/files_browser.py

## Comportamento final
- Ao abrir a janela de arquivos do cliente, o prefixo inicial é sempre org_id/client_id, exibindo imediatamente as pastas de primeiro nível (ex.: GERAL).
- A mensagem "Sem arquivos para este cliente" só aparece quando a listagem do prefixo atual realmente está vazia (prefixo exibido no label).
- Botão "←" continua subindo um nível; o botão "→" agora entra na pasta selecionada ou redefine para a raiz do cliente (sem saltos GERAL/GERAL/Auditoria).

## Validações
`
Ruff   src/modules src/ui: OK
Flake8 src/modules src/ui: OK
Pyright src/modules src/ui: OK
`

Execução do app (python -m src.app_gui) não realizada aqui; navegação visual será testada pelo usuário.
