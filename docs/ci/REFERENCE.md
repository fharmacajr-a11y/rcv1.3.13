# Guia Rápido - CI/CD FASE 6

**Quick reference para desenvolvimento diário**

---

## 🔧 Configurar Ambiente Local

```powershell
# Ativar virtual environment
.\.venv\Scripts\Activate.ps1

# Configurar encoding UTF-8
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"

# Verificar encoding
python -X utf8 -c "import sys; print(sys.getdefaultencoding())"
```

---

## ✅ Validação Local (Antes do Commit)

```powershell
# 1. Pre-commit hooks (roda automaticamente no commit, mas pode testar antes)
pre-commit run --all-files

# 2. Bandit security scan
python -X utf8 -m bandit -c .bandit -r src infra adapters data security

# 3. Suite ClientesV2 (gate de qualidade)
pytest tests/modules/clientes_v2/ -v --tb=short --maxfail=5

# 4. Suite completa (opcional)
pytest --cov=src --cov-report=term-missing -v
```

---

## 📤 Workflow de Desenvolvimento

```bash
# 1. Criar branch de feature
git checkout -b feature/minha-feature

# 2. Fazer alterações
# ... código ...

# 3. Commit (pre-commit roda automaticamente)
git add .
git commit -m "feat: minha feature"

# 4. Push (dispara CI)
git push origin feature/minha-feature

# 5. Criar Pull Request no GitHub
# CI roda automaticamente

# 6. Merge para develop/main
# CI roda novamente
```

---

## 🚀 Workflow de Release

```bash
# 1. Garantir que develop/main está verde
# Verificar Actions no GitHub

# 2. Criar tag anotada
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"

# 3. Push da tag (dispara release workflow)
git push origin v1.5.63

# 4. Verificar release no GitHub
# Actions > RC - release > v1.5.63
# Releases > v1.5.63

# 5. Baixar artefatos e validar
# Verificar checksum SHA256
```

---

## 🔍 Comandos de Debug

```powershell
# Verificar encoding configurado
python -X utf8 -c "import sys; print(f'Default: {sys.getdefaultencoding()}'); print(f'Filesystem: {sys.getfilesystemencoding()}'); print(f'Stdout: {sys.stdout.encoding}')"

# Testar Bandit com verbose
python -X utf8 -m bandit -c .bandit -r src -v

# Rodar teste específico
pytest tests/modules/clientes_v2/test_nome.py::test_funcao -v

# Rodar com coverage detalhado
pytest tests/modules/clientes_v2/ --cov=src --cov-report=html
# Abrir htmlcov/index.html
```

---

## 📊 Verificar Status dos Workflows

```bash
# Via GitHub CLI (gh)
gh workflow list
gh run list --workflow=ci.yml
gh run view <run-id>

# Via browser
# https://github.com/<owner>/<repo>/actions
```

---

## 🔐 Verificar Integridade de Release

```powershell
# Baixar artefatos da release
# https://github.com/<owner>/<repo>/releases/tag/v1.5.63

# Verificar checksum
(Get-FileHash RC-Gestor-v1.5.63.zip -Algorithm SHA256).Hash

# Comparar com arquivo .sha256
Get-Content RC-Gestor-v1.5.63.zip.sha256
```

---

## 🏷️ Gerenciar Tags

```bash
# Listar tags
git tag -l

# Ver detalhes de uma tag
git show v1.5.63

# Deletar tag local
git tag -d v1.5.63

# Deletar tag remota
git push origin :refs/tags/v1.5.63

# Re-criar tag (se necessário)
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"
git push origin v1.5.63
```

---

## 📋 Checklist Pré-Commit

- [ ] Código segue padrão do projeto
- [ ] Testes criados/atualizados
- [ ] ClientesV2 suite passa localmente
- [ ] Bandit não reporta issues críticas
- [ ] Documentação atualizada (se necessário)
- [ ] CHANGELOG.md atualizado (features/fixes)

---

## 📋 Checklist Pré-Release

- [ ] CI verde em develop/main
- [ ] ClientesV2 suite (113 testes) passando
- [ ] Bandit scan sem issues
- [ ] CHANGELOG.md atualizado
- [ ] Versão incrementada em pyproject.toml
- [ ] Tag anotada criada com mensagem descritiva
- [ ] Checklist de staging executado (manual)

---

## 🚨 Troubleshooting

### UnicodeEncodeError no Windows

```powershell
# Verificar encoding
$env:PYTHONUTF8
$env:PYTHONIOENCODING

# Configurar se necessário
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"

# Rodar comando com flag UTF-8
python -X utf8 -m <comando>
```

### CI Falhando

```bash
# 1. Verificar logs no GitHub Actions
# 2. Reproduzir localmente
pre-commit run --all-files
pytest tests/modules/clientes_v2/ -v

# 3. Corrigir e fazer commit
git add .
git commit -m "fix: correção de CI"
git push
```

### Release Falhando

```bash
# 1. Verificar logs no GitHub Actions
# 2. Deletar tag local e remota
git tag -d v1.5.63
git push origin :refs/tags/v1.5.63

# 3. Corrigir issue
# 4. Re-criar tag e push
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"
git push origin v1.5.63
```

---

## 📚 Links Úteis

- [CI/CD Overview](README.md)
- [Staging Checklist](STAGING_CHECKLIST.md)
- [ROADMAP](../ROADMAP.md)
- [Status](../STATUS.md)

---

**Última atualização:** 2026-01-24  
**Versão:** 1.5.62 (FASE 6)
