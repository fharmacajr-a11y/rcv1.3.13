# DevTools - QA

Esta pasta contém ferramentas e relatórios de Quality Assurance (QA) do projeto.

## 📁 Estrutura

- `analyze_linters.py` - Script de análise de relatórios de linters (Ruff, Flake8, Pyright)
- `*.json` - Relatórios gerados por ferramentas de QA (ignorados no git)
- `*.txt` - Relatórios de texto (ignorados no git)

## 🔧 Uso

### Executar Análise de Linters

```bash
# A partir da raiz do projeto
python devtools/qa/analyze_linters.py
```

**Pré-requisitos**: Os relatórios devem estar gerados na pasta `devtools/qa/`:
- `ruff.json`
- `flake8.txt`
- `pyright.json` (opcional)

### Gerar Relatórios

```bash
# Ruff
ruff check . --output-format=json > devtools/qa/ruff.json

# Flake8
flake8 . --format="%(path)s:%(row)d:%(col)d:%(code)s:%(text)s" > devtools/qa/flake8.txt

# Pyright
pyright --outputjson > devtools/qa/pyright.json
```

## 📊 Relatórios de Segurança

Esta pasta também contém relatórios de análise de segurança (quando gerados):
- `bandit-report.json` - Análise de segurança de código (Bandit)
- `pip-audit.json` - Auditoria de dependências (pip-audit)
- `ruff-report.json` - Relatório completo do Ruff

**Nota**: Estes arquivos são ignorados no git para evitar poluir o repositório.

## 📝 Histórico

Para consultar relatórios históricos de QA e FixPacks, veja `docs/qa-history/`.
