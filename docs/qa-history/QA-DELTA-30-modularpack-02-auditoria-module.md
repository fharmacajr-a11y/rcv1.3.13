# QA-DELTA-30: ModularPack-02 - Auditoria isolada (UI -> service)

**Data**: 2025-11-13
**Autor**: Codex (GPT-5)
**Tipo**: Quality Assurance - Modularizacao
**Prioridade**: Alta

---

## Objetivo
Isolar a feature Auditoria garantindo um contrato UI -> service consistente, removendo acessos diretos da view ao Supabase/infra e mantendo o comportamento original (listas, filtros, status, upload e subpastas).

---

## Alteracoes principais
- Consolidado o acesso Supabase/Storage em src/modules/auditoria/service.py (clientes, auditorias, status, uploads, rollback, criacao de pastas, utilitarios de arquivo).
- Atualizada src/modules/auditoria/view.py para depender apenas das funcoes do service, mantendo a responsabilidade da UI focada em eventos/renderizacao.
- Registrada a arquitetura da feature em docs/architecture/FEATURE-auditoria-v1.md para descrever fronteiras e funcoes expostas.

---

## Validacoes
`
Ruff:    0 issues
Flake8:  0 issues
Pyright: 0 errors
python -m src.app_gui: nao executado (ambiente CLI sem UI)
`

Validacao manual (listar/filtrar auditorias, alterar status, iniciar/excluir, abrir subpastas e fazer upload) permanece pendente para um ambiente com interface grafica.

---

## Escopo
- Somente a feature Auditoria foi tocada; SIFAP, Farmacia e demais modulos continuam intactos.
- Configuracoes globais e outros adapters nao sofreram alteracao funcional.
