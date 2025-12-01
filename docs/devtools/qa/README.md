# DevTools - QA

Esta pasta contém ferramentas e relatórios de Quality Assurance (QA) do projeto.

## 📁 Estrutura

- `analyze_linters.py` - Script de an?lise de relat?rios do Ruff (Pyright opcional)
- `analyze_security.py` - Runner do Bandit focado em c?digo de produ??o
- `*.json` - Relatórios gerados por ferramentas de QA (ignorados no git)
- `*.txt` - Relatórios de texto (ignorados no git)

## 🔧 Uso

### Executar Análise de Linters

```bash
# A partir da raiz do projeto
python docs/devtools/qa/analyze_linters.py
```

**Pré-requisitos**: Os relatórios devem estar gerados na pasta `docs/devtools/qa/`:
- `ruff.json`
- `pyright.json` (opcional)

### Gerar Relatórios

```bash
# Ruff
ruff check . --output-format=json > docs/devtools/qa/ruff.json

# Pyright
pyright --outputjson > docs/devtools/qa/pyright.json
```

> **Observa??o:** Flake8 foi aposentado em favor do Ruff. Relat?rios legados (`flake8.txt`) permanecem apenas para consulta em `docs/qa-history/`.

### Seguran?a (Bandit)

```bash
# Reinstalar Bandit caso a venv tenha sido copiada de outra vers?o
python -m pip install --force-reinstall bandit

# Rodar apenas nos diret?rios de produ??o (tests/ exclu?do)
python docs/devtools/qa/analyze_security.py
# ou
bandit -r src adapters data infra security -x tests
```

- O `-x tests` evita falsos positivos B101 (`assert_used`) nos testes pytest.
- O Bandit deve ser usado para revisar somente c?digo do app (src, adapters, data, infra, security).
- Existe um arquivo `.bandit` na raiz; se voc? rodar `bandit -r .`, ele reaplica o mesmo filtro de diret?rios automaticamente.

## 📊 Relatórios de Segurança

Esta pasta também contém relatórios de análise de segurança (quando gerados):
- `bandit-report.json` - Análise de segurança de código (Bandit)
- `pip-audit.json` - Auditoria de dependências (pip-audit)
- `ruff-report.json` - Relatório completo do Ruff

**Nota**: Estes arquivos são ignorados no git para evitar poluir o repositório.

## 📝 Histórico

Para consultar relatórios históricos de QA e FixPacks, veja `docs/qa-history/`.
