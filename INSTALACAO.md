# 📦 Instalação e Configuração — RC Gestor

## 1️⃣ Preparação do Ambiente

### 1.1 Criar ambiente virtual

```powershell
# Windows PowerShell
python -m venv .venv
```

### 1.2 Ativar ambiente virtual

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Se houver erro de política de execução:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 1.3 Atualizar pip

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

## 2️⃣ Instalar Dependências

### 2.1 Instalação completa

```powershell
# Instalar todas as dependências do projeto
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2.2 Pacotes essenciais

O arquivo `requirements.txt` inclui:

- **py7zr>=0.21.0** — Suporte para arquivos .7z no módulo Auditoria
- **ttkbootstrap** — Interface gráfica moderna
- **supabase** — Cliente para backend Supabase
- **PyMuPDF** — Visualização de PDFs
- Demais dependências listadas no arquivo

## 3️⃣ Configurar VS Code

### 3.1 Selecionar interpretador Python

1. Abra o **Command Palette** (`Ctrl+Shift+P`)
2. Digite: **Python: Select Interpreter**
3. Escolha: **`.venv\Scripts\python.exe`** (Python 3.13.x)

> ⚠️ **IMPORTANTE**: Esta etapa elimina warnings do Pylance sobre imports como `py7zr`

### 3.2 Verificar pyrightconfig.json

O arquivo já está configurado com:

```json
{
  "venvPath": ".",
  "venv": ".venv",
  "extraPaths": ["src", "infra", "adapters"],
  "typeCheckingMode": "basic"
}
```

## 4️⃣ Verificação da Instalação

### 4.1 Testar imports

```powershell
.\.venv\Scripts\python.exe -c "import rarfile; print('rarfile OK:', rarfile.__version__)"
.\.venv\Scripts\python.exe -c "import ttkbootstrap; print('ttkbootstrap OK')"
.\.venv\Scripts\python.exe -c "from supabase import create_client; print('supabase OK')"
```

### 4.2 Executar aplicação

```powershell
.\.venv\Scripts\python.exe -m src.app_gui
```

## 5️⃣ Funcionalidades de Arquivos Compactados (Auditoria)

### 5.1 Suporte a formatos

O módulo **Auditoria** suporta upload de:

- ✅ **Arquivos .zip** (biblioteca padrão Python)
- ✅ **Arquivos .rar** (via pacote `rarfile` + UnRAR/unar/bsdtar)

### 5.2 Comportamento

- **ZIP**: Leitura direta de membros com `zipfile.ZipFile` (sem extração temporária)
- **RAR**: Extração temporária com `rarfile.RarFile.extractall()` (requer UnRAR/unar/bsdtar no PATH)
- **Ambos**: Preservam estrutura de subpastas no Storage
- **Uploads**: Usam `upsert: "true"` (sobrescrita idempotente)
- **Mensagem de sucesso**: Mostra Razão Social + CNPJ formatado (00.000.000/0000-00)

### 5.3 Requisitos para arquivos .rar

**Windows:**
1. Instalar [WinRAR](https://www.win-rar.com/download.html)
2. Adicionar `C:\Program Files\WinRAR` ao PATH do sistema
3. Ou garantir que `UnRAR.exe` esteja acessível

**Linux/macOS:**
```bash
# Debian/Ubuntu
sudo apt install unrar

# macOS (Homebrew)
brew install unar
```

### 5.4 Teste rápido

1. Abrir módulo **Auditoria**
2. Selecionar cliente na lista
3. Clicar em **"Enviar ZIP/RAR p/ Auditoria"**
4. Escolher arquivo `.zip` ou `.rar` com subpastas
5. Verificar mensagem de sucesso com Razão Social + CNPJ formatado
6. Verificar upload no Storage: `{org}/{client}/GERAL/Auditoria/{subpastas}`

## 🔧 Resolução de Problemas

### Erro: "rarfile não encontrado"

```powershell
# Reinstalar rarfile
.\.venv\Scripts\python.exe -m pip install --force-reinstall rarfile
```

### Erro: "Backend do RAR não encontrado"

Este erro indica que o `rarfile` está instalado, mas a ferramenta de extração não está no PATH.

**Solução Windows:**
1. Instalar WinRAR: https://www.win-rar.com/download.html
2. Adicionar ao PATH: `C:\Program Files\WinRAR`
3. Reiniciar VS Code/terminal

### Erro: "Não foi possível resolver a importação rarfile" (Pylance)

1. Verificar se o **Interpreter** está apontando para `.venv`
2. Recarregar janela do VS Code (`Ctrl+Shift+P` → "Reload Window")

### Erro: "Suporte a .7z indisponível"

Significa que `py7zr` não está instalado no ambiente. Execute:

```powershell
.\.venv\Scripts\python.exe -m pip install py7zr
```

## 📝 Notas Técnicas

### Estrutura de Uploads

```
Supabase Storage: rc-docs
└── {org_id}/
    └── {client_id}/
        └── GERAL/
            └── Auditoria/
                ├── 2024/
                │   ├── Janeiro.pdf
                │   └── Fevereiro.pdf
                └── 2025/
                    └── Marco.pdf
```

### MIME Types

O sistema detecta automaticamente o MIME type correto para:
- PDFs: `application/pdf`
- Imagens: `image/jpeg`, `image/png`
- ZIP: `application/zip`
- 7z: `application/x-7z-compressed`

### Segurança

- ✅ Proteção contra **zip-slip** (path traversal)
- ✅ Sanitização de nomes de arquivos
- ✅ Validação de extensões
- ✅ Filtragem de arquivos ocultos (`__MACOSX`, `.keep`)

---

**Versão**: 1.0.99
**Data**: Novembro 2025
**Python**: 3.13.x
