# GitHub Actions Workflows - RC-Gestor

Este diretório contém os workflows de CI/CD para o projeto RC-Gestor.

**Última atualização:** FASE 6 (2026-01-24)

---

## 📋 Workflows Disponíveis

### 1. `ci.yml` - Test & Build Contínuo (FASE 6)

**Trigger**:
- Push em `main`, `develop`, `maintenance/**`, `feature/**`
- Pull requests para `main`, `develop`
- Workflow dispatch (manual)

**Platforms**:
- ✅ Windows (windows-latest)
- ✅ Linux (ubuntu-latest, headless com Xvfb)

**Jobs**:

#### Job: `test` (Windows)
1. ✅ Checkout com histórico completo
2. ✅ Setup Python 3.13 com cache de pip
3. ✅ Instalação de dependências
4. ✅ Verificação de encoding UTF-8
5. ✅ Pre-commit hooks (all-files)
6. ✅ Bandit security scan
7. ✅ Validação de sintaxe (compileall)
8. ✅ Validação de política UI/Theme
9. ✅ Smoke test UI
10. ✅ Suite ClientesV2 (113 testes - gate de qualidade)
11. ✅ Suite completa com coverage
12. ✅ Upload de artefatos

#### Job: `test-linux` (Ubuntu)
- Mesmos steps do Windows
- Testes rodando em modo headless (Xvfb)

**Encoding UTF-8 (Windows)**:
```yaml
env:
  PYTHONUTF8: 1              # PEP 540
  PYTHONIOENCODING: utf-8    # Force UTF-8 em stdio
```

**Artefatos gerados**:
- `pytest-report-windows` (7 dias)
- `pytest-report-linux` (7 dias)
- `coverage-report` (7 dias, Ubuntu only)

**Como usar**:
```bash
# Push para branch dispara automaticamente
git push origin develop

# Ou via workflow_dispatch no GitHub UI
```

**Tempo médio**: 8-10min (Windows), 7-9min (Linux)

---

### 2. `release.yml` - Release Automatizada (FASE 6)

**Trigger**:
- Push de tags `v*`
- Workflow dispatch (manual)

**Platform**: Windows (windows-latest)

**Steps de Validação** (antes do build):
1. ✅ Pre-commit hooks (all-files)
2. ✅ Bandit security scan
3. ✅ Suite ClientesV2 (gate de qualidade)
4. ✅ Quick test suite

**Steps de Build**:
1. ✅ PyInstaller build (`rc_gestor.spec`)
2. ✅ Verificação de executável
3. ✅ Check de segurança (.env não deve estar no bundle)
4. ✅ Compactação em ZIP
5. ✅ Geração de checksum SHA256
6. ✅ Criação de GitHub Release

**Artefatos publicados na Release**:
- `RC-Gestor-{version}.zip` - Build completo Windows
- `RC-Gestor-{version}.zip.sha256` - Checksum SHA256
- `docs/FASE_5_RELEASE.md` - Documentação da release

**Como usar (Tag Anotada)**:
```bash
# Criar tag anotada (RECOMENDADO)
git tag -a v1.5.63 -m "Release v1.5.63 - FASE 6 CI/CD"
git push origin v1.5.63

# Tag simples (também funciona)
git tag v1.5.63
git push origin v1.5.63
```

**Resultado**:
- Release criada automaticamente em: `Releases` > `v1.5.63`
- ZIP e documentação anexados como assets
- Changelog e instruções incluídas

**Verificação de integridade**:
```powershell
# Windows (PowerShell)
(Get-FileHash RC-Gestor-v1.5.63.zip -Algorithm SHA256).Hash

# Comparar com o conteúdo de RC-Gestor-v1.5.63.zip.sha256
```

**Encoding UTF-8**:
```yaml
env:
  PYTHONUTF8: 1
  PYTHONIOENCODING: utf-8
```

---

### 3. `security-audit.yml` - Auditoria de Segurança (Opcional)

**Trigger**:
- Push/PR na branch `maintenance/v1.0.29`
- Schedule: Todo domingo às 00:00 UTC
- Manual via workflow_dispatch

**Jobs**:
1. **audit**: Executa `pip-audit` para detectar vulnerabilidades

**Artefatos gerados**:
- `pip-audit-report.json` (90 dias de retenção)

**Verificações**:
- ✅ Escaneia todas as dependências do `requirements.txt`
- ✅ Falha CI se vulnerabilidades críticas forem encontradas
- ✅ Gera relatório JSON detalhado

**Como usar**:
```bash
# Dispara automaticamente em push
git push origin maintenance/v1.0.29

# Ou manualmente via GitHub UI:
# Actions > Security - pip-audit > Run workflow
```

**Acessar relatório**:
1. Vá para: `Actions` > `Security - pip-audit` > Run específico
2. Na seção `Artifacts`, baixe `pip-audit-report`

---

## 🔐 Segurança

### Verificações Automáticas

**1. Sem `.env` no bundle**:
```powershell
$envFiles = Get-ChildItem -Path dist\RC-Gestor\ -Recurse -File | Where-Object {$_.Extension -eq '.env'}
if ($envFiles) {
    Write-Error "✗ Arquivos .env encontrados!"
    exit 1
}
```

**2. Validação do executável**:
```powershell
if (Test-Path dist\RC-Gestor\RC-Gestor.exe) {
    Write-Host "✓ RC-Gestor.exe criado com sucesso"
} else {
    Write-Error "✗ RC-Gestor.exe não encontrado!"
    exit 1
}
```

**3. Checksums SHA256**:
- Gerados automaticamente para cada release
- Permite verificação de integridade do download

### Secrets Necessários

**GITHUB_TOKEN**: Fornecido automaticamente pelo GitHub Actions (não requer configuração)

---

## 🚀 Melhorias Futuras (Opcional)

### 1. Code Signing (Certificado Digital)

**Com certificado Windows**:
```yaml
- name: Sign executable
  run: |
    signtool sign /a /tr http://timestamp.digicert.com /td SHA256 /fd SHA256 dist\RC-Gestor\RC-Gestor.exe
  env:
    CERT_PASSWORD: ${{ secrets.CERT_PASSWORD }}
```

**Benefícios**:
- Reduz alertas do Windows SmartScreen
- Melhora confiança do usuário
- Validação de identidade do publisher

**Pré-requisitos**:
- Adquirir certificado de code signing (ex: DigiCert, Sectigo)
- Adicionar certificado aos Secrets do GitHub
- Configurar `signtool` no runner

---

### 2. Sigstore (Assinatura de Transparência)

**Sem certificado pago**:
```yaml
- name: Install Cosign
  uses: sigstore/cosign-installer@v3

- name: Sign artifact with Sigstore
  run: |
    cosign sign-blob --yes RC-Gestor-v1.0.29.zip --output-signature RC-Gestor-v1.0.29.zip.sig --output-certificate RC-Gestor-v1.0.29.zip.pem
```

**Benefícios**:
- Assinatura gratuita e transparente
- Verificabilidade pública via Rekor
- Sem necessidade de certificado pago

**Verificação**:
```bash
cosign verify-blob --signature RC-Gestor-v1.0.29.zip.sig --certificate RC-Gestor-v1.0.29.zip.pem RC-Gestor-v1.0.29.zip
```

**Referências**:
- https://www.sigstore.dev/
- https://github.com/sigstore/cosign

---

### 3. Installer Windows (Inno Setup)

**Workflow adicional**:
```yaml
- name: Install Inno Setup
  run: choco install innosetup -y

- name: Create installer
  run: iscc installer.iss
```

**Exemplo de script `installer.iss`**:
```iss
[Setup]
AppName=RC-Gestor
AppVersion=1.0.29
DefaultDirName={pf}\RC-Gestor
OutputDir=installer
OutputBaseFilename=RC-Gestor-Setup-v1.0.29

[Files]
Source: "dist\RC-Gestor\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{commondesktop}\RC-Gestor"; Filename: "{app}\RC-Gestor.exe"
```

**Benefícios**:
- Instalador profissional (.exe)
- Criação de atalhos automática
- Desinstalação via Painel de Controle

**Referências**:
- https://jrsoftware.org/isinfo.php

---

## 📊 Status dos Workflows

### Badges para README

Adicione ao `README.md` principal:

```markdown
[![CI - Test & Build](https://github.com/{owner}/{repo}/actions/workflows/ci.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/ci.yml)
[![Security Audit](https://github.com/{owner}/{repo}/actions/workflows/security-audit.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/security-audit.yml)
[![Release](https://github.com/{owner}/{repo}/actions/workflows/release.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/release.yml)
```

Substitua `{owner}` e `{repo}` pelos valores reais.

---

## 🛠️ Troubleshooting

### Problema: Testes falhando no CI

**Solução**:
1. Execute localmente: `pytest -q`
2. Verifique warnings no output do CI
3. Confirme que `requirements.txt` está atualizado

### Problema: Build falhando

**Solução**:
1. Verifique `build/rc_gestor.spec` está versionado
2. Confirme que `app_gui.py` existe
3. Execute localmente: `pyinstaller build/rc_gestor.spec --clean`

### Problema: Artefato não aparece

**Solução**:
1. Verifique se o job `build` completou com sucesso
2. Confirme retenção de artefatos (7-90 dias)
3. Veja logs do step "Upload build artifact"

### Problema: Release não criada

**Solução**:
1. Confirme que a tag foi enviada: `git push origin v1.0.29`
2. Verifique permissões de `GITHUB_TOKEN` (deve ter `contents: write`)
3. Veja logs do workflow `release.yml`

---

## 📚 Referências

- **GitHub Actions**: https://docs.github.com/en/actions
- **actions/checkout**: https://github.com/actions/checkout
- **actions/setup-python**: https://github.com/actions/setup-python
- **actions/upload-artifact**: https://github.com/actions/upload-artifact
- **softprops/action-gh-release**: https://github.com/softprops/action-gh-release
- **PyInstaller**: https://pyinstaller.org/
- **pytest**: https://docs.pytest.org/
- **pip-audit**: https://github.com/pypa/pip-audit

---

## ✅ Checklist de Configuração

- [x] Workflows criados (`.github/workflows/`)
- [ ] Testar CI: Push para `maintenance/v1.0.29`
- [ ] Verificar artefato: `Actions` > `Artifacts`
- [ ] Testar Release: `git tag v1.0.29 && git push origin v1.0.29`
- [ ] Verificar Release: `Releases` > `v1.0.29`
- [ ] (Opcional) Configurar code signing
- [ ] (Opcional) Configurar Sigstore
- [ ] (Opcional) Criar Inno Setup installer
- [ ] Adicionar badges ao README principal
