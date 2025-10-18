# 📦 PyInstaller Build - RC-Gestor v1.0.34

## 🎯 IMPORTANTE - ARQUIVOS RUNTIME

O bundle do PyInstaller **DEVE** incluir apenas a pasta `runtime_docs/` (não `ajuda/`).

### ⚠️ CRÍTICO
A pasta `runtime_docs/` contém arquivos carregados **EM RUNTIME** pelo aplicativo:

| Arquivo | Usado em | Função |
|---------|----------|--------|
| `CHANGELOG.md` | `gui/main_window.py:629` | Menu "Ajuda > Histórico de Mudanças" |

**Se `runtime_docs/` não estiver no bundle, o menu "Ajuda" falhará!**

---

## 🛠️ COMANDOS DE BUILD

### Windows (PowerShell)

```powershell
# Build básico (onedir - pasta dist/RC-Gestor/)
pyinstaller app_gui.py --add-data "runtime_docs;runtime_docs"

# Build com ícone e nome customizado
pyinstaller app_gui.py `
  --name "RC-Gestor" `
  --icon "assets/rc.ico" `
  --add-data "runtime_docs;runtime_docs" `
  --add-data "rc.ico;." `
  --windowed

# Build onefile (executável único)
pyinstaller app_gui.py `
  --name "RC-Gestor" `
  --icon "assets/rc.ico" `
  --add-data "runtime_docs;runtime_docs" `
  --add-data "rc.ico;." `
  --onefile `
  --windowed
```

### Linux/macOS (Bash)

```bash
# Build básico (onedir)
pyinstaller app_gui.py --add-data "runtime_docs:runtime_docs"

# Build completo
pyinstaller app_gui.py \
  --name "RC-Gestor" \
  --icon "assets/rc.ico" \
  --add-data "runtime_docs:runtime_docs" \
  --add-data "rc.ico:." \
  --windowed

# Build onefile
pyinstaller app_gui.py \
  --name "RC-Gestor" \
  --icon "assets/rc.ico" \
  --add-data "runtime_docs:runtime_docs" \
  --add-data "rc.ico:." \
  --onefile \
  --windowed
```

---

## 📝 ARQUIVO .SPEC (RECOMENDADO)

Para builds reproduzíveis, crie `build/rc_gestor.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('runtime_docs', 'runtime_docs'),  # ⚠️ CRÍTICO - arquivos runtime
        ('rc.ico', '.'),                    # Ícone do app
        ('.env', '.'),                      # Config (se empacotado)
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'ajuda',           # ✅ NÃO incluir documentação no bundle
        'scripts',         # ✅ NÃO incluir scripts de dev
        'tests',           # ✅ NÃO incluir testes
        '.git',
        '.github',
        '__pycache__',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RC-Gestor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed (sem terminal)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/rc.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RC-Gestor',
)
```

### Build com .spec:

```bash
# Windows
pyinstaller build/rc_gestor.spec --clean

# Linux/macOS
pyinstaller build/rc_gestor.spec --clean
```

---

## 🔍 VERIFICAÇÃO PÓS-BUILD

### 1. Verificar Estrutura do Bundle

```powershell
# Windows
Get-ChildItem -Path dist\RC-Gestor\ -Recurse | Where-Object {$_.Name -eq "CHANGELOG.md"}
# Deve retornar: dist\RC-Gestor\runtime_docs\CHANGELOG.md

# Verificar que ajuda/ NÃO está no bundle
Get-ChildItem -Path dist\RC-Gestor\ -Recurse | Where-Object {$_.FullName -like "*\ajuda\*"}
# Deve retornar: NADA (vazio)
```

```bash
# Linux/macOS
find dist/RC-Gestor -name "CHANGELOG.md"
# Deve retornar: dist/RC-Gestor/runtime_docs/CHANGELOG.md

# Verificar que ajuda/ NÃO está no bundle
find dist/RC-Gestor -path "*/ajuda/*"
# Deve retornar: NADA (vazio)
```

### 2. Verificar Ausência de .env

```powershell
# Windows
Get-ChildItem -Path dist\RC-Gestor\ -Recurse -File | Where-Object {$_.Extension -eq '.env'}
# Deve retornar: NADA (ou apenas .env.example se intencionalmente incluído)
```

```bash
# Linux/macOS
find dist/RC-Gestor -name "*.env"
# Deve retornar: NADA (ou apenas .env.example se intencionalmente incluído)
```

### 3. Testar Menu "Ajuda > Histórico"

```powershell
# Executar o bundle
.\dist\RC-Gestor\RC-Gestor.exe

# Testar:
# 1. Abrir o app
# 2. Menu "Ajuda" > "Histórico de Mudanças"
# 3. Deve abrir popup com as primeiras 20 linhas do CHANGELOG
```

---

## 📊 TAMANHO ESPERADO DO BUNDLE

| Componente | Tamanho Estimado |
|------------|------------------|
| Executável (.exe) | ~15-25 MB |
| runtime_docs/ | ~50-200 KB |
| Bibliotecas Python | ~30-50 MB |
| **Total (onedir)** | **~50-80 MB** |
| **Total (onefile)** | **~50-80 MB** |

### ❌ NÃO incluir ajuda/ (economiza ~2-5 MB)

A pasta `ajuda/` contém 28+ arquivos `.md` de documentação que **não são necessários em runtime**.

---

## 🚀 WORKFLOW CI/CD (GitHub Actions)

Atualizar `.github/workflows/ci.yml`:

```yaml
- name: PyInstaller build (usando comandos diretos)
  run: |
    pyinstaller app_gui.py `
      --name "RC-Gestor" `
      --icon "assets/rc.ico" `
      --add-data "runtime_docs;runtime_docs" `
      --add-data "rc.ico;." `
      --windowed `
      --clean

- name: Verify runtime_docs in bundle
  run: |
    if (Test-Path dist\RC-Gestor\runtime_docs\CHANGELOG.md) {
      Write-Host "✓ CHANGELOG.md presente no bundle"
    } else {
      Write-Error "✗ CHANGELOG.md NÃO encontrado no bundle!"
      exit 1
    }

- name: Verify ajuda/ NOT in bundle
  run: |
    $ajudaFiles = Get-ChildItem -Path dist\RC-Gestor\ -Recurse | Where-Object {$_.FullName -like "*\ajuda\*"}
    if ($ajudaFiles) {
      Write-Error "✗ Pasta ajuda/ encontrada no bundle (deve ser excluída)!"
      exit 1
    } else {
      Write-Host "✓ Pasta ajuda/ corretamente excluída do bundle"
    }
```

---

## 🛡️ BOAS PRÁTICAS

### ✅ FAZER:
1. Sempre incluir `runtime_docs/` com `--add-data`
2. Excluir `ajuda/` do bundle (economiza espaço)
3. Testar menu "Ajuda > Histórico" após build
4. Verificar ausência de `.env` no bundle
5. Usar `.spec` para builds reproduzíveis

### ❌ NÃO FAZER:
1. Incluir `ajuda/` no bundle (desnecessário, ~2-5 MB)
2. Esquecer `--add-data runtime_docs`
3. Empacotar `.env` com credenciais
4. Usar caminhos absolutos (quebra em outras máquinas)
5. Fazer build sem `--clean` (cache pode causar bugs)

---

## 🐛 TROUBLESHOOTING

### Problema: "Arquivo CHANGELOG.md nao encontrado"

**Causa:** `runtime_docs/` não está no bundle.

**Solução:**
```bash
# Verificar que o comando inclui --add-data
pyinstaller app_gui.py --add-data "runtime_docs;runtime_docs"  # Windows
pyinstaller app_gui.py --add-data "runtime_docs:runtime_docs"  # Linux/macOS
```

### Problema: Bundle muito grande (>100 MB)

**Causa:** `ajuda/` foi incluída por engano.

**Solução:**
```python
# No .spec, adicionar em excludes:
excludes=[
    'ajuda',    # ⚠️ NÃO incluir docs
    'scripts',
    'tests',
]
```

### Problema: Erro ao abrir menu "Ajuda"

**Causa:** `resource_path()` não resolve corretamente no bundle.

**Solução:** Verificar `utils/resource_path.py`:
```python
def resource_path(relative_path: str) -> str:
    """Return an absolute path to the given resource, handling PyInstaller."""
    try:
        base_path: str = getattr(sys, "_MEIPASS")  # PyInstaller bundle
    except Exception:
        base_path = os.path.abspath(".")  # Dev environment
    return os.path.join(base_path, relative_path)
```

---

## 📚 REFERÊNCIAS

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller --add-data](https://pyinstaller.org/en/stable/usage.html#what-to-bundle-where-to-search)
- [PyInstaller .spec files](https://pyinstaller.org/en/stable/spec-files.html)
- [sys._MEIPASS explained](https://pyinstaller.org/en/stable/runtime-information.html)

---

**📌 LEMBRE-SE:**
- `runtime_docs/` = OBRIGATÓRIO no bundle ✅
- `ajuda/` = NÃO incluir no bundle ❌
- Sempre testar menu "Ajuda > Histórico" após build!
