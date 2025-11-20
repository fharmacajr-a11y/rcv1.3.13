# QA-DELTA-34: Combobox de clientes (Auditoria)

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Escopo
Aumentar a largura da combo "Cliente para auditoria" para exibir o ID, razão social e CNPJ completos sem cortar o texto.

## Alterações
- src/modules/auditoria/view.py: a coluna da combobox agora tem weight=1, a combo usa sticky="ew" e width=64, permitindo ocupar toda a linha disponível.

## Validações
`
Ruff   src/modules/auditoria: OK
Flake8 src/modules/auditoria: OK
Pyright src/modules/auditoria: OK
`

Execução do app não realizada aqui; a validação visual ficará a cargo do usuário.
