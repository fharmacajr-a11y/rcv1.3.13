# FASE 6: CI Windows + Release Automatizada + Staging

**Data:** 2026-01-24  
**Status:** ✅ **CONCLUÍDO**  
**Responsável:** DevOps Team  

---

## 📋 Objetivos

1. **Workflow de CI robusto** para Windows e Linux
2. **Encoding UTF-8** garantido em todos os pipelines
3. **Release automatizada** via tags anotadas
4. **Checklist de Staging** para validação manual

---

## 🎯 Contexto

### Problemas Identificados

- **FASE 5:** Bandit rodava localmente com `python -X utf8`, mas CI não estava configurado
- **Encoding:** Windows usa cp1252 por padrão, causando `UnicodeEncodeError` em outputs com emojis
- **Release:** Processo manual, sem validação automatizada completa
- **Staging:** Sem roteiro documentado para smoke tests

### Solução Implementada

Implementação de pipelines CI/CD completos com:
- Suporte nativo a UTF-8 no Windows
- Pre-commit hooks rodando em todos os PRs
- Bandit security scan integrado
- Suite ClientesV2 (113 testes) como gate de qualidade
- Release reprodutível via tags anotadas

---

## ✅ Implementação

### 1. Workflow de CI (.github/workflows/ci.yml)

#### 1.1 Configuração de Encoding

**Variáveis de ambiente adicionadas:**

```yaml
env:
  PYTHONUTF8: 1              # PEP 540 - Force UTF-8 mode
  PYTHONIOENCODING: utf-8    # Force UTF-8 em stdio
```

**Aplicado em:**
- Job `test` (Windows)
- Job `test-linux` (Ubuntu)

#### 1.2 Steps do Pipeline

**Windows:**
1. ✅ Checkout com histórico completo (`fetch-depth: 0`)
2. ✅ Setup Python 3.13 com cache de pip
3. ✅ Instalação de dependências (requirements.txt + requirements-dev.txt)
4. ✅ Verificação de encoding (diagnostic step)
5. ✅ Pre-commit hooks (all-files)
6. ✅ Bandit security scan com `python -X utf8`
7. ✅ Validação de sintaxe (compileall)
8. ✅ Validação de política UI/Theme
9. ✅ Smoke test UI
10. ✅ Suite ClientesV2 (113 testes)
11. ✅ Suite completa com coverage
12. ✅ Upload de artefatos (coverage reports)

**Linux (Ubuntu):**
- Mesmos steps do Windows
- Xvfb para testes headless
- Sem flag `-X utf8` (Linux já usa UTF-8 por padrão)

#### 1.3 Triggers

```yaml
on:
  push:
    branches: ["main", "develop", "maintenance/**", "feature/**"]
  pull_request:
    branches: ["main", "develop"]
  workflow_dispatch:
```

---

### 2. Workflow de Release (.github/workflows/release.yml)

#### 2.1 Trigger por Tag

```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:
```

**Comando para criar tag anotada:**

```bash
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"
git push origin v1.5.63
```

#### 2.2 Steps de Validação

Antes do build, o workflow executa:

1. ✅ Pre-commit hooks
2. ✅ Bandit security scan
3. ✅ Suite ClientesV2 (gate de qualidade)
4. ✅ Quick test suite

**Se qualquer step falhar, o build é abortado.**

#### 2.3 Build e Empacotamento

1. ✅ PyInstaller build (`rc_gestor.spec`)
2. ✅ Verificação de executável
3. ✅ Check de segurança (.env não deve estar no bundle)
4. ✅ Compactação em ZIP
5. ✅ Geração de checksum SHA256

#### 2.4 Release no GitHub

**Artefatos anexados:**

- `RC-Gestor-{tag}.zip` - Build completo do Windows
- `RC-Gestor-{tag}.zip.sha256` - Checksum para verificação
- `docs/FASE_5_RELEASE.md` - Documentação da release

**Informações na release:**

- Changelog linkado
- Verificações realizadas (FASE 6)
- Instruções de verificação de integridade
- Instruções para criar tags anotadas

---

### 3. Hardening do Bandit

#### 3.1 Configuração (.bandit)

```yaml
exclude_dirs:
  - '.venv'
  - 'tests'
  - '__pycache__'
  # ... outros

skips: ['B110', 'B101']
```

- **B110:** try-except-pass (comum em GUI cleanup)
- **B101:** assert (usado em third_party code)

#### 3.2 Execução no CI

**Windows:**
```bash
python -X utf8 -m bandit -c .bandit -r src infra adapters data security
```

**Linux:**
```bash
python -m bandit -c .bandit -r src infra adapters data security
```

**Flag `-X utf8` é necessária no Windows** para evitar `UnicodeEncodeError` quando Bandit imprime output com emojis/unicode.

---

### 4. Checklist de Staging

**Arquivo:** [docs/STAGING_CHECKLIST.md](./STAGING_CHECKLIST.md)

#### 4.1 Escopo do Smoke Test

**Módulo ClientesV2 (padrão):**

1. ✅ Inicialização do aplicativo
   - Login
   - Tema light/dark

2. ✅ Operações CRUD
   - Listar clientes
   - Buscar clientes
   - Novo cliente
   - Editar cliente
   - Excluir (lixeira)
   - Restaurar da lixeira

3. ✅ Funcionalidades auxiliares
   - Upload de arquivos
   - Export (CSV/Excel)
   - Modo pick (seleção)
   - WhatsApp integration

4. ✅ Testes de estabilidade
   - Performance
   - Tratamento de erros
   - Encoding UTF-8

5. ✅ Testes de interface
   - Responsividade
   - Alternância de temas

#### 4.2 Registro de Evidências

Cada execução deve ser documentada no próprio checklist com:

- Data, versão, build
- Testador
- Resultados (✅/⚠️/❌)
- Screenshots/logs
- Notas

#### 4.3 Frequência

**Obrigatório:**
- Antes de cada release de produção (tag `v*`)
- Após merge de features críticas

**Recomendado:**
- Semanalmente no branch `develop`
- Após correção de bugs críticos

---

## 📊 Resultados

### CI Pipeline

**Status atual:**
- ✅ Windows: UTF-8 configurado
- ✅ Linux: Suporte headless (Xvfb)
- ✅ Pre-commit: Rodando em all-files
- ✅ Bandit: Integrado sem falhas de encoding
- ✅ ClientesV2 suite: 113 testes (gate de qualidade)

**Tempo médio de execução:**
- Windows: ~8-10 minutos
- Linux: ~7-9 minutos

### Release Pipeline

**Melhorias:**
- ✅ Validação completa antes do build
- ✅ Segurança: Check de .env no bundle
- ✅ Checksum SHA256 para verificação de integridade
- ✅ Documentação anexada (FASE_5_RELEASE.md)
- ✅ Instruções claras para criar tags anotadas

**Reprodutibilidade:**
- Build é determinístico (mesma tag → mesmo build)
- Histórico completo (`fetch-depth: 0`)
- Versão de Python fixada (3.13)

---

## 🔧 Configurações Técnicas

### Encoding UTF-8 no Windows

**Três camadas de proteção:**

1. **Variáveis de ambiente globais:**
   ```yaml
   env:
     PYTHONUTF8: 1
     PYTHONIOENCODING: utf-8
   ```

2. **Flag no comando Python:**
   ```bash
   python -X utf8 -m bandit ...
   ```

3. **Verificação diagnóstica:**
   ```python
   import sys
   print(f'Default encoding: {sys.getdefaultencoding()}')
   print(f'Filesystem encoding: {sys.getfilesystemencoding()}')
   print(f'stdout encoding: {sys.stdout.encoding}')
   ```

**Resultado esperado:**
```
Default encoding: utf-8
Filesystem encoding: utf-8
stdout encoding: utf-8
```

---

## 📝 Comandos Úteis

### Criar Tag Anotada

```bash
# Criar tag anotada localmente
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"

# Enviar para remote (dispara release workflow)
git push origin v1.5.63

# Listar tags
git tag -l

# Ver detalhes de uma tag
git show v1.5.63
```

### Rodar CI Localmente (Simulação)

```powershell
# Windows PowerShell
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"

# Verificar encoding
python -X utf8 -c "import sys; print(f'Default encoding: {sys.getdefaultencoding()}')"

# Rodar pre-commit
pre-commit run --all-files

# Rodar Bandit
python -X utf8 -m bandit -c .bandit -r src infra adapters data security

# Rodar ClientesV2 suite
pytest tests/modules/clientes_v2/ -v --tb=short --maxfail=5
```

### Verificar Release Build

```powershell
# Download do artefato
# (manual via GitHub Releases)

# Verificar checksum
(Get-FileHash RC-Gestor-v1.5.63.zip -Algorithm SHA256).Hash

# Comparar com arquivo .sha256
Get-Content RC-Gestor-v1.5.63.zip.sha256
```

---

## 🚀 Próximos Passos (FASE 7)

Sugestões para evolução:

1. **CD para Staging/Prod**
   - Deploy automático para ambiente de staging
   - Blue-green deployment

2. **Testes E2E automatizados**
   - Playwright/Selenium para smoke tests
   - Integração com CI

3. **Métricas e Monitoring**
   - Sentry para error tracking
   - Telemetria de performance

4. **Auto-update**
   - Cliente com capacidade de auto-atualização
   - Verificação de versão no startup

---

## 📚 Referências

- [FASE_5_RELEASE.md](./FASE_5_RELEASE.md) - Fase anterior (Bandit UTF-8 fix)
- [STAGING_CHECKLIST.md](./STAGING_CHECKLIST.md) - Roteiro de smoke tests
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PEP 540 - UTF-8 Mode](https://peps.python.org/pep-0540/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

---

## 🎯 Critérios de Sucesso

✅ **TODOS ATINGIDOS:**

1. ✅ CI rodando em Windows sem `UnicodeEncodeError`
2. ✅ Pre-commit + Bandit integrados no pipeline
3. ✅ ClientesV2 suite (113 testes) como gate de qualidade
4. ✅ Release automatizada via tag anotada
5. ✅ Documentação completa de staging
6. ✅ Checksum SHA256 para verificação de integridade

---

## 🔒 Considerações de Segurança

1. **Bandit scan obrigatório** em CI e Release
2. **Validação de .env** no bundle (não deve existir)
3. **Checksum SHA256** para verificar integridade do download
4. **Secrets via GitHub Secrets** (não hardcoded)
5. **Baseline de skips documentada** (.bandit file)

---

## 📌 Notas Finais

- Esta fase estabelece a **fundação de CI/CD** para o projeto
- Foco em **reprodutibilidade** e **segurança**
- **Encoding UTF-8** resolvido definitivamente no Windows
- **Checklist de staging** garante validação manual criteriosa

---

**Última atualização:** 2026-01-24  
**Status:** ✅ Pronto para produção  
**Tag sugerida:** `v1.5.63-fase6`
