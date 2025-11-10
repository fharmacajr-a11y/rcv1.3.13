# Guia de Release e Assinatura de Código

Este documento descreve o processo completo de geração, assinatura e publicação de releases do **RC-Gestor v1.1.0** no Windows usando **SignTool**.

---

## 1. Pré-requisitos

Antes de iniciar o processo de release, certifique-se de que os seguintes requisitos estão atendidos:

### Ferramentas e Certificados

- **Windows SDK** instalado (contém `signtool.exe`)
  - Caminho típico: `C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe`
  - Instale via [Visual Studio Installer][2] ou [Windows SDK standalone][3]

- **Certificado de Code Signing** válido
  - Certificado pode estar no **Windows Certificate Store** (recomendado para CI/CD)
  - Ou arquivo `.pfx` com senha (armazenar senha em variável de ambiente `CERT_PASSWORD`)
  - Certificado deve ser emitido por CA confiável (DigiCert, Sectigo, GlobalSign, etc.)

### Checklist de Versão

Antes de gerar o executável, valide que a versão está consistente em todos os arquivos:

- [ ] `src/version.py` — `__version__ = "v1.1.0"`
- [ ] `version_file.txt` — todas as linhas de versão com `1.1.0`
- [ ] `rcgestor.spec` — nome do executável `RC-Gestor-Clientes-v1.1.0.exe`
- [ ] `CHANGELOG.md` — changelog atualizado com features/fixes da versão

### Testes

Antes do build de produção:

```powershell
# Executar suite completa de testes
pytest tests/ -v

# Smoke test (validação de inicialização)
python -m src.app_gui --no-splash
```

---

## 2. Build Local (Geração do Executável)

### Limpeza de Builds Anteriores

```powershell
# Remover diretórios de builds anteriores
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
```

### Geração do Executável

```powershell
# Ativar ambiente virtual (se aplicável)
.\.venv\Scripts\Activate.ps1

# Gerar executável usando PyInstaller
pyinstaller rcgestor.spec
```

O executável será gerado em: **`dist\RC-Gestor-Clientes-v1.1.0.exe`**

### Verificação Pós-Build

```powershell
# Testar executável
.\dist\RC-Gestor-Clientes-v1.1.0.exe --no-splash

# Verificar tamanho (referência: ~50-80 MB)
Get-Item .\dist\RC-Gestor-Clientes-v1.1.0.exe | Select-Object Name, Length
```

---

## 3. Assinatura do Executável

A assinatura digital garante autenticidade e reduz avisos do Windows SmartScreen.

### Cenário A: Certificado no Windows Certificate Store

Recomendado para ambientes corporativos e CI/CD. O SignTool seleciona automaticamente o certificado apropriado.

```powershell
# Definir caminho do signtool
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"

# Assinar com certificado do store
& $signtool sign `
  /a `
  /tr http://timestamp.digicert.com `
  /td SHA256 `
  /fd SHA256 `
  "dist\RC-Gestor-Clientes-v1.1.0.exe"
```

**Parâmetros:**
- `/a` — Seleciona automaticamente o melhor certificado disponível
- `/tr` — URL do servidor de timestamp (RFC 3161)
- `/td` — Algoritmo de hash do timestamp (SHA256)
- `/fd` — Algoritmo de hash da assinatura (SHA256)

### Cenário B: Certificado em Arquivo PFX

Para certificados armazenados em arquivo `.pfx` com senha:

```powershell
# Definir caminho do signtool
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"

# Assinar usando PFX
& $signtool sign `
  /f "C:\caminho\para\certificado.pfx" `
  /p "$env:CERT_PASSWORD" `
  /tr http://timestamp.digicert.com `
  /td SHA256 `
  /fd SHA256 `
  "dist\RC-Gestor-Clientes-v1.1.0.exe"
```

**Parâmetros adicionais:**
- `/f` — Caminho do arquivo PFX
- `/p` — Senha do certificado (usar variável de ambiente, nunca hardcode)

### Servidores de Timestamp Alternativos

Se `http://timestamp.digicert.com` falhar, use um dos seguintes:

```powershell
# DigiCert (primário)
/tr http://timestamp.digicert.com

# Sectigo (backup)
/tr http://timestamp.sectigo.com

# GlobalSign (backup)
/tr http://timestamp.globalsign.com

# Microsoft (legacy, não usar para novos certificados)
/t http://timestamp.verisign.com/scripts/timstamp.dll
```

> ⚠️ **IMPORTANTE:** Sempre use `/tr` (RFC 3161) com `/td SHA256`. O parâmetro `/t` (Authenticode v1) é obsoleto. Sem timestamp válido, a assinatura expira junto com o certificado. ([Microsoft Learn][1])

---

## 4. Verificação da Assinatura

Após assinar, valide a assinatura digital:

### Verificação com SignTool

```powershell
# Verificar assinatura e cadeia de confiança
& $signtool verify /pa /v "dist\RC-Gestor-Clientes-v1.1.0.exe"
```

**Saída esperada:**
```
Verifying: dist\RC-Gestor-Clientes-v1.1.0.exe
Signature Index: 0 (Primary Signature)
Hash of file (sha256): [hash]
Signing Certificate Chain:
    [CA raiz]
    [CA intermediária]
    [Certificado de Code Signing]
Successfully verified: dist\RC-Gestor-Clientes-v1.1.0.exe
```

### Verificação com PowerShell

```powershell
# Obter detalhes da assinatura Authenticode
Get-AuthenticodeSignature "dist\RC-Gestor-Clientes-v1.1.0.exe" | Format-List

# Verificar timestamp especificamente
Get-AuthenticodeSignature "dist\RC-Gestor-Clientes-v1.1.0.exe" |
    Select-Object -ExpandProperty TimeStamperCertificate
```

**Campos importantes:**
- `Status` — Deve ser `Valid`
- `SignerCertificate` — Dados do certificado de assinatura
- `TimeStamperCertificate` — Dados do servidor de timestamp (se presente)

---

## 5. Publicação do Release

### Criar Tag Git

```bash
# Criar tag anotada
git tag -a v1.1.0 -m "Release v1.1.0"

# Enviar tag para repositório remoto
git push origin v1.1.0
```

### Criar Release no GitHub (Manual)

1. Acesse: `https://github.com/<owner>/<repo>/releases/new`
2. Selecione a tag: `v1.1.0`
3. Título: `RC-Gestor v1.1.0`
4. Descrição: Cole o conteúdo de `CHANGELOG.md` para v1.1.0
5. Anexe o arquivo: `dist\RC-Gestor-Clientes-v1.1.0.exe`
6. Clique em **Publish release**

### Criar Release no GitHub (CLI)

```bash
# Usando GitHub CLI (gh)
gh release create v1.1.0 \
  dist/RC-Gestor-Clientes-v1.1.0.exe \
  --title "RC-Gestor v1.1.0" \
  --notes-file CHANGELOG.md
```

### Checklist de Publicação

- [ ] Tag criada e enviada ao repositório
- [ ] Release criado no GitHub com changelog
- [ ] Executável assinado anexado ao release
- [ ] Testar download do executável em máquina limpa
- [ ] Verificar que Windows SmartScreen não bloqueia (pode levar 24-48h para reputação)

---

## 6. Troubleshooting

### Problema: "No certificates were found that met all the given criteria"

**Causa:** SignTool não encontrou certificado válido no Windows Certificate Store.

**Solução:**
```powershell
# Listar certificados disponíveis
certmgr.msc  # GUI
# ou
Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert

# Se não houver certificado, use /f para especificar PFX:
& $signtool sign /f "C:\caminho\cert.pfx" /p "$env:CERT_PASSWORD" ...
```

### Problema: "The specified timestamp server could not be reached"

**Causa:** Servidor de timestamp indisponível ou bloqueado por firewall.

**Solução:**
1. Verificar conectividade de rede
2. Testar servidor alternativo (Sectigo, GlobalSign)
3. Se persistir, assinar sem timestamp (não recomendado):
   ```powershell
   # Sem timestamp (assinatura expira com certificado)
   & $signtool sign /a /fd SHA256 "dist\RC-Gestor-Clientes-v1.1.0.exe"
   ```

### Problema: Windows SmartScreen bloqueia executável

**Causa:** Executável sem assinatura ou certificado não reconhecido.

**Solução:**
1. Garantir que assinatura está válida (`signtool verify`)
2. Certificado deve ser de CA confiável (não self-signed)
3. Timestamp deve estar presente e válido
4. Reputação do executável aumenta com downloads legítimos (24-48h)
5. Considerar **Extended Validation (EV) Code Signing** para bypass imediato

### Problema: "File not found: signtool.exe"

**Causa:** Windows SDK não instalado ou caminho incorreto.

**Solução:**
```powershell
# Buscar signtool no sistema
Get-ChildItem -Path "C:\Program Files (x86)\Windows Kits" -Recurse -Filter signtool.exe

# Ou instalar Windows SDK:
# https://developer.microsoft.com/windows/downloads/windows-sdk/
```

### Problema: Build PyInstaller falha com ModuleNotFoundError

**Causa:** Dependências não encontradas ou `hiddenimports` incompleto.

**Solução:**
1. Verificar `rcgestor.spec` — seção `hiddenimports`
2. Adicionar módulos ausentes manualmente
3. Testar no ambiente virtual limpo:
   ```powershell
   python -m venv .venv-test
   .\.venv-test\Scripts\Activate.ps1
   pip install -r requirements.txt
   pyinstaller rcgestor.spec
   ```

---

## 7. Referências Oficiais

### Microsoft Learn — SignTool

- **Sign Tool Documentation**: [https://learn.microsoft.com/windows/win32/seccrypto/signtool][1]
  - Opções de linha de comando (`/a`, `/f`, `/tr`, `/td`, `/fd`)
  - Diferenças entre Authenticode v1 (`/t`) e RFC 3161 (`/tr`)
  - Requisitos de timestamp para assinaturas duradouras

- **Code Signing Best Practices**: [https://learn.microsoft.com/windows-hardware/drivers/dashboard/code-signing-best-practices][4]
  - Algoritmos recomendados (SHA256)
  - Gerenciamento de certificados
  - Timestamp e validade de assinatura

### Autoridades Certificadoras

- **DigiCert**: [https://www.digicert.com/code-signing][5]
- **Sectigo**: [https://sectigo.com/ssl-certificates-tls/code-signing][6]
- **GlobalSign**: [https://www.globalsign.com/code-signing-certificate][7]

### PyInstaller

- **PyInstaller Documentation**: [https://pyinstaller.org/en/stable/][8]
- **Spec File Reference**: [https://pyinstaller.org/en/stable/spec-files.html][9]

---

## Notas Adicionais

- **Versionamento Semântico**: Este projeto segue [SemVer 2.0.0][10] (`MAJOR.MINOR.PATCH`)
- **Frequência de Release**: Definida pela equipe de desenvolvimento
- **Suporte a Versões**: Apenas a versão mais recente recebe updates de segurança

---

[1]: https://learn.microsoft.com/windows/win32/seccrypto/signtool
[2]: https://visualstudio.microsoft.com/downloads/
[3]: https://developer.microsoft.com/windows/downloads/windows-sdk/
[4]: https://learn.microsoft.com/windows-hardware/drivers/dashboard/code-signing-best-practices
[5]: https://www.digicert.com/code-signing
[6]: https://sectigo.com/ssl-certificates-tls/code-signing
[7]: https://www.globalsign.com/code-signing-certificate
[8]: https://pyinstaller.org/en/stable/
[9]: https://pyinstaller.org/en/stable/spec-files.html
[10]: https://semver.org/

---

**Última atualização:** 10 de novembro de 2025
**Versão do documento:** 1.0
**Aplicável a:** RC-Gestor v1.1.0+
