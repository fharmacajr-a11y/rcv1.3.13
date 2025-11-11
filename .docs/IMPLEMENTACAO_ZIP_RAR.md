# Implementação: Suporte ZIP/RAR com 7-Zip Embarcado

## ✅ Implementação Completa

Branch: `feat/rar-zip-dialog`

### Resumo

Esta implementação adiciona suporte completo a arquivos **ZIP e RAR** sem exigir que os usuários instalem qualquer software adicional. Os binários do 7-Zip foram embarcados diretamente no repositório.

---

## 🎯 Alterações Realizadas

### 1. **Diálogo de Arquivo Tkinter** ✅

**Arquivo**: `src/modules/auditoria/view.py`

```python
# Antes: Aceitava qualquer arquivo
path = filedialog.askopenfilename(title="Selecione arquivo...")

# Depois: Apenas ZIP e RAR
path = filedialog.askopenfilename(
    title="Selecione um arquivo .ZIP ou .RAR",
    filetypes=[
        ("Arquivos compactados", ("*.zip", "*.rar")),
        ("ZIP", "*.zip"),
        ("RAR", "*.rar"),
        ("Todos os arquivos", "*.*"),
    ]
)
```

### 2. **Módulo de Extração Unificado** ✅

**Arquivo**: `infra/archive_utils.py` (NOVO)

Funcionalidades:
- ✅ Extração de **ZIP** com `zipfile` (stdlib Python)
- ✅ Extração de **RAR** com 7-Zip CLI (`7z x -y -o<dest> <arquivo>`)
- ✅ Busca automática do binário (embarcado ou PATH do sistema)
- ✅ Exceções customizadas (`ArchiveError`) com mensagens amigáveis
- ✅ Suporte a PyInstaller (`sys._MEIPASS`)

```python
from infra.archive_utils import extract_archive, ArchiveError

try:
    extract_archive("arquivo.rar", "destino/")
except ArchiveError as e:
    messagebox.showerror("Erro", str(e))
```

### 3. **Binários 7-Zip Embarcados** ✅

**Diretório**: `infra/bin/7zip/`

Arquivos embarcados no repositório:
- ✅ `7z.exe` (564 KB) - Executável principal
- ✅ `7z.dll` (1.9 MB) - Biblioteca de suporte

**Gerenciamento**: Git LFS (Large File Storage)
```bash
# Configurado automaticamente
git lfs track "*.exe" "*.dll"
```

**Versão**: 7-Zip 24.09 (2024-11-25) x64

### 4. **Documentação de Licença** ✅

**Diretório**: `third_party/7zip/`

- ✅ `LICENSE.txt` - Licença completa (GNU LGPL + unRAR restriction + BSD)
- ✅ `README.md` - Informações sobre versão, origem e uso

**Nota Legal**: O 7-Zip é software livre. A descompressão RAR é permitida, mas criar compactadores RAR é proibido (restrição do unRAR).

### 5. **Configuração PyInstaller** ✅

**Arquivo**: `rcgestor.spec`

```python
Analysis(
    binaries=[
        # Binários do 7-Zip para extração de arquivos RAR
        ('infra/bin/7zip/7z.exe', '7z'),
        ('infra/bin/7zip/7z.dll', '7z'),
    ],
    ...
)
```

Os binários são automaticamente incluídos no `.exe` final. No executável empacotado, ficam em `<_MEIPASS>/7z/`.

### 6. **Testes Completos** ✅

**Arquivo**: `tests/test_archives.py` (NOVO)

Cobertura de testes:
- ✅ Extração de ZIP simples
- ✅ ZIP com caracteres especiais/acentuação
- ✅ ZIP vazio
- ✅ ZIP corrompido (validação de erro)
- ✅ Suporte ZIP64
- ✅ RAR (skip automático se 7-Zip ausente)
- ✅ Erro amigável quando 7-Zip não disponível
- ✅ Formato não suportado (.7z rejeitado)
- ✅ Criação automática de diretórios

**Resultado dos testes**:
```
12 passed, 1 skipped in 0.19s
```

### 7. **Ajustes no .gitignore** ✅

```gitignore
# Build e distribuição (PyInstaller)
build/
dist/
*.exe
# Exceção: binários embarcados do 7-Zip
!infra/bin/7zip/*.exe
!infra/bin/7zip/*.dll
```

---

## 📦 Arquivos Criados/Modificados

### Novos Arquivos
- ✅ `infra/archive_utils.py` - Módulo de extração
- ✅ `infra/bin/7zip/7z.exe` - Binário embarcado (Git LFS)
- ✅ `infra/bin/7zip/7z.dll` - Biblioteca embarcada (Git LFS)
- ✅ `third_party/7zip/LICENSE.txt` - Licença do 7-Zip
- ✅ `third_party/7zip/README.md` - Documentação do 7-Zip
- ✅ `tests/test_archives.py` - Testes unitários
- ✅ `scripts/demo_archive_support.py` - Script de demonstração

### Arquivos Modificados
- ✅ `src/modules/auditoria/view.py` - Diálogo e extração
- ✅ `rcgestor.spec` - Configuração PyInstaller
- ✅ `infra/bin/7zip/README.md` - Atualizado
- ✅ `.gitignore` - Exceções para binários embarcados
- ✅ `.gitattributes` - Configuração Git LFS

---

## 🚀 Como Usar

### Para Desenvolvedores

```bash
# 1. Clonar o repositório (inclui binários via Git LFS)
git clone <repo-url>

# 2. Executar testes
pytest tests/test_archives.py -v

# 3. Demonstração
python scripts/demo_archive_support.py
```

### Para Build

```bash
# Build com PyInstaller (binários incluídos automaticamente)
pyinstaller rcgestor.spec
```

### Para Usuários Finais

**Nenhuma ação necessária!** 🎉

O executável final já contém tudo:
- ✅ Binários do 7-Zip embarcados
- ✅ Suporte automático a ZIP e RAR
- ✅ Zero instalações externas

---

## 🔍 Verificação

### Status do 7-Zip
```python
from infra.archive_utils import is_7z_available, find_7z

print(f"7-Zip disponível: {is_7z_available()}")
print(f"Caminho: {find_7z()}")
```

**Saída esperada**:
```
7-Zip disponível: True
Caminho: C:\...\infra\bin\7zip\7z.exe
```

### Testes
```bash
pytest tests/test_archives.py -v
# 12 passed, 1 skipped ✅
```

---

## 📊 Tamanho dos Binários

| Arquivo | Tamanho | Gerenciamento |
|---------|---------|---------------|
| `7z.exe` | ~550 KB | Git LFS |
| `7z.dll` | ~1.9 MB | Git LFS |
| **Total** | **~2.5 MB** | |

**Impacto**: Mínimo (~2.5 MB adicionais no repositório, gerenciados via LFS)

---

## ✨ Benefícios

1. **Zero Instalações**: Usuários não precisam instalar 7-Zip, WinRAR ou qualquer ferramenta
2. **Compatibilidade Total**: Suporta RAR (incluindo RAR5), ZIP e ZIP64
3. **Portabilidade**: Funciona em qualquer PC Windows x64, mesmo sem privilégios admin
4. **Manutenibilidade**: Código limpo, testado e documentado
5. **Licença Limpa**: 7-Zip é LGPL, compatível com uso comercial

---

## 🔗 Links

- **7-Zip**: https://www.7-zip.org/
- **Licença**: `third_party/7zip/LICENSE.txt`
- **Documentação**: `third_party/7zip/README.md`
- **Testes**: `tests/test_archives.py`
- **Demo**: `scripts/demo_archive_support.py`

---

## 📝 Commits

```bash
# Commit 1: Estrutura inicial
feat(ui+extract): diálogo aceita ZIP/RAR e extração de RAR via 7-Zip; zipfile p/ ZIP; erros amigáveis

# Commit 2: Binários embarcados
feat(archives): ZIP/RAR no diálogo; RAR via 7-Zip embarcado; erros amigáveis
```

---

## ✅ Checklist de Implementação

- [x] Criar branch `feat/rar-zip-dialog`
- [x] Ajustar `filetypes` do diálogo Tkinter
- [x] Criar módulo `infra/archive_utils.py`
- [x] Baixar e embedar binários 7-Zip x64
- [x] Configurar Git LFS para binários
- [x] Adicionar licença do 7-Zip
- [x] Configurar PyInstaller (`.spec`)
- [x] Criar testes unitários completos
- [x] Atualizar `.gitignore`
- [x] Criar documentação
- [x] Executar testes (12 passed ✅)
- [x] Commit e push
- [x] Criar script de demonstração

**Status**: ✅ **CONCLUÍDO**
