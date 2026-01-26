# 🔧 CI/CD - Integração e Deploy Contínuo

**Visão geral:** Documentação de CI/CD, comandos úteis e checklists de validação

---

## 📚 Documentos Disponíveis

### Quick Reference

**Comandos essenciais** para validação local:

- Pre-commit hooks
- Comandos de teste (pytest)
- Linter (ruff)
- Security scan (bandit)

**Use quando:** Precisa validar mudanças localmente antes de commit/push

---

### [../STAGING_CHECKLIST.md](../STAGING_CHECKLIST.md)

**Roteiro completo** de smoke test manual:

- Login e autenticação
- CRUD de clientes (listagem, criação, edição)
- Upload e gerenciamento de arquivos
- Exportação de dados (Excel, JSON)
- Navegação entre módulos

**Use quando:** Precisa validar release em ambiente de staging antes de produção

---

## 🚀 Quick Start

### Validação Local (Pré-Commit)

```powershell
# 1. Pre-commit hooks (automático no commit)
pre-commit run --all-files

# 2. Testes principais
pytest tests/modules/clientes_v2/ -v --tb=short

# 3. Ruff (linter)
ruff check src/ tests/

# 4. Bandit (security)
python -X utf8 -m bandit -c .bandit -r src infra adapters data security
```

### Workflow de Release

```bash
# 1. Garantir CI verde
# Verificar GitHub Actions

# 2. Criar tag anotada
git tag -a v1.5.63 -m "Release v1.5.63 - [descrição]"

# 3. Push (dispara release workflow)
git push origin v1.5.63
```

---

## ⚙️ Configuração

### Pre-commit Hooks (20 hooks)

Validações automáticas em cada commit:

**Formatação:**
- Trailing whitespace
- End of file fixer
- Mixed line endings

**Sintaxe:**
- YAML, TOML, JSON validation
- Python AST validation
- Compileall check

**Qualidade:**
- Ruff (linter + formatter)
- Check builtin literals
- Check docstring position

**Segurança:**
- Bandit security scan (UTF-8 safe)
- Debug statements check

**Políticas Customizadas:**
- CustomTkinter SSoT policy
- UI/Theme policy validation
- Test file naming

### Encoding UTF-8 (Windows)

**Problema:** Windows usa cp1252 por padrão

**Solução:**

```powershell
# Configurar ambiente
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"

# Verificar
python -X utf8 -c "import sys; print(sys.getdefaultencoding())"
```

**No pre-commit:** Hooks usam `python -X utf8` automaticamente

---

## 📊 Métricas de Qualidade

### Gates de Qualidade

| Gate | Critério | Status |
|------|----------|--------|
| **Testes** | 112+ passing | ✅ |
| **Ruff** | 0 errors | ✅ |
| **Bandit** | 0 issues | ✅ |
| **Pre-commit** | 20/20 passing | ✅ |

### Cobertura

- **Módulo clientes_v2:** ~85%
- **Global (src/):** ~75%
- **Meta:** >90%

---

## 🔍 Troubleshooting

### Pre-commit Falha (Encoding)

**Sintoma:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Solução:**
```powershell
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"
pre-commit run --all-files
```

### Testes Falhando Localmente

**Sintoma:** Testes passam no CI mas falham localmente

**Possíveis causas:**
1. Ambiente não atualizado (`pip install -r requirements-dev.txt`)
2. Cache corrompido (`pytest --cache-clear`)
3. Arquivos .pyc antigos (`find . -name '*.pyc' -delete`)

**Solução:**
```powershell
# Recriar ambiente
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/modules/clientes_v2/ -v
```

### Build Falha (PyInstaller)

**Sintoma:** Executável não inicia ou importa módulos errados

**Verificar:**
1. `rcgestor.spec` está atualizado
2. `sitecustomize.py` configurado corretamente
3. Todos os assets em `assets/` existem

**Solução:**
```powershell
# Limpar build cache
Remove-Item -Recurse -Force build, dist
pyinstaller --clean rcgestor.spec
```

---

## 🔗 Links Relacionados

- [../README.md](../README.md) - Índice da documentação
- [../../CONTRIBUTING.md](../../CONTRIBUTING.md) - Guia de contribuição
- [../../CHANGELOG.md](../../CHANGELOG.md) - Histórico de mudanças
- [../reports/releases/](../reports/releases/) - Relatórios de release

---

**Última atualização:** 26 de janeiro de 2026
