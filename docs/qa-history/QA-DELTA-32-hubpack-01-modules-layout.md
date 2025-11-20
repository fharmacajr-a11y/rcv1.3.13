# QA-DELTA-32: HubPack-01 - layout de módulos

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Escopo
- Ajustar apenas o painel "Módulos" do Hub para refletir a ordem/cores solicitadas: Clientes e Auditoria (verde), Senhas e Fluxo de Caixa (laranja) e demais módulos (ANVISA, Farmácia Popular, SNGPC, SIFAP) reaparecendo em cinza.
- Nenhuma alteração em lógica da feature Auditoria ou demais serviços.

## Alterações
- src/ui/hub_screen.py: reorganizado o bloco de criação dos botões para a nova ordem e aplicado ootstyle="success" em Clientes/Auditoria, ootstyle="warning" em Senhas/Fluxo de Caixa e estilo padrão (cinza) para os demais botões.

## Validações
`
Ruff   src/ui: OK
Flake8 src/ui: OK
Pyright src/ui: OK
`

Execução de python -m src.app_gui não realizada aqui; verificação visual ficará a cargo do usuário.
