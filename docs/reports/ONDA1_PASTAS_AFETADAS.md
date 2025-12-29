# Registro de Pastas Afetadas - Onda 1 Limpeza
**Data**: 29/12/2025
**Escopo**: Limpeza de artefatos, relatórios, exports, coverage

## Pastas Identificadas para Limpeza:

### reports/_qa/
- coverage_* (diretórios HTML gerados)
- relatórios históricos mf{40-51}_*.md
- duplicados (bandit_report.txt vs bandit_latest.txt)

### exports/
- Verificar se há arquivos versionados que deveriam estar no .gitignore

### Cache/Build Artifacts:
- .pytest_cache/ (se versionado)
- __pycache__/ (se versionado)
- .coverage (se versionado)

### assets/
- assets/modulos/hub/ (untracked - verificar se é auto-gerado)
- assets/notificacoes/ (untracked - verificar se é auto-gerado)
- assets/topbar/pdf.png (untracked - verificar se necessário)

## Pastas NÃO Afetadas (conforme regras):
- src/
- infra/
- adapters/
- data/
- security/
- typings/
- migrations/
- tests/ (código de produção)
