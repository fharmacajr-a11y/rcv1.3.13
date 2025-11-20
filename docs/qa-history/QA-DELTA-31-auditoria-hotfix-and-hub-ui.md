# QA-DELTA-31: Auditoria hotfix (IDs) e ajuste do Hub

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Escopo
- Corrigir a exclusão de auditorias para aceitar IDs UUID (sem cast para inteiro) e garantir consistência em todas as chamadas relacionadas.
- Destacar o módulo Auditoria no Hub principal e ocultar o atalho da ANVISA, mantendo apenas Clientes, Senhas e Auditoria (nesta ordem) no card de módulos.

## Alterações
- src/modules/auditoria/service.py: update_auditoria_status e delete_auditorias agora tratam IDs como strings; delete_auditorias normaliza/filtra os valores antes de chamar o Supabase.
- src/modules/auditoria/view.py: o índice _aud_index só armazena IDs em string, e as chamadas para atualizar status/excluir auditorias deixam de converter para int.
- src/ui/hub_screen.py: botão ANVISA removido, Auditoria reposicionado após Senhas e forçado para ootstyle="success"; demais botões do painel não são renderizados para manter o hub enxuto.

## Validações
`
Ruff   src/modules/auditoria: OK
Flake8 src/modules/auditoria: OK
Pyright src/modules/auditoria: OK
Ruff   src/ui: OK
Flake8 src/ui: OK
Pyright src/ui: OK
`

Execução do app (python -m src.app_gui) não realizada aqui; validação visual do hub e do fluxo de Auditoria será concluída localmente.
