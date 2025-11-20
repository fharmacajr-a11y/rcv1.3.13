# QA-DELTA-36: ClientFilesPack-01

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Escopo
- Browser de arquivos aberto pelo módulo **Clientes** não exibe mais os botões de navegação (setas) e usa o título Arquivos: ID X — Razão — CNPJ, igual ao padrão da Auditoria.
- Contexto da Auditoria permanece com setas e título antigo.

## Alterações
- src/ui/files_browser.py: adicionada flag de contexto (module == "auditoria") para controlar o título e a renderização das setas; clientes agora veem apenas o label de prefixo e navegam via double-click.

## Validações
`
Ruff   src/ui: OK
Flake8 src/ui: OK
Pyright src/ui: OK
`

Execução de python -m src.app_gui não realizada; validação visual ficará com o usuário.
