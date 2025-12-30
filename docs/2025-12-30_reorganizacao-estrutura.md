# 2025-12-30 — Reorganização da Estrutura do Projeto

## O que mudou

1. **Consolidação de pastas na raiz**
   - `helpers/` removida (estava vazia)
   - `tools/` movida para `scripts/` (consolidação de scripts de dev)

2. **Padronização da documentação**
   - `docs/` agora é a pasta principal (arquivos simples por assunto)
   - `docs/cronologia/` guarda apenas os 2 PDFs oficiais
   - Todas as subpastas antigas removidas (adr, architecture, releases, reports, etc.)

3. **Pasta `reports/` da raiz**
   - Removida do versionamento
   - Adicionada ao `.gitignore` (uso local apenas)

## Por que mudou

- Reduzir "ruído" na raiz do projeto (menos pastas)
- Simplificar onde criar/encontrar documentação
- Evitar duplicação e documentação espalhada
- Manter histórico oficial nos PDFs de cronologia

## Estrutura final

```
docs/
├── README.md              # Padrão de documentação
├── SECURITY_MODEL.md      # Doc de segurança (preservado)
├── 2025-12-30_reorganizacao-estrutura.md  # Este arquivo
└── cronologia/
    ├── Cronologia de App.pdf   # Overview
    └── Cronologia de App2.pdf  # Detalhado
```

## Impacto / Como testar

- **Zero impacto em runtime** — apenas organização de arquivos
- Scripts de `scripts/` continuam funcionando normalmente
- Relatórios locais podem ser gerados em `reports/` (ignorado pelo Git)
