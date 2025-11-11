# 📦 Suporte a Arquivos Compactados — Auditoria

## 🎯 Resumo

O módulo **Auditoria** suporta upload de arquivos compactados preservando a estrutura de subpastas:

- ✅ **ZIP** — Leitura direta (biblioteca padrão Python)
- ✅ **RAR** — Extração temporária (requer UnRAR/WinRAR no PATH)

---

## 📋 Implementação

### Dependências

```txt
rarfile>=4.2
```

### Estratégias

| Formato | Biblioteca | Estratégia | Disco Temporário |
|---------|------------|------------|------------------|
| `.zip`  | `zipfile`  | Leitura direta de membros | ❌ Não |
| `.rar`  | `rarfile`  | Extração → Upload | ✅ Sim |

### Código Principal

```python
# ZIP - Eficiente
with zipfile.ZipFile(path, "r") as zf:
    for info in zf.infolist():
        if info.is_dir():
            continue
        rel = info.filename.lstrip("/").replace("\\", "/")
        data = zf.read(info)
        storage.upload(f"{base_prefix}/{rel}", data, {"upsert": "true"})

# RAR - Extração temporária
with rarfile.RarFile(path) as rf:
    with tempfile.TemporaryDirectory() as tmpdir:
        rf.extractall(tmpdir)
        # caminhar pela árvore e fazer upload de cada arquivo
```

---

## 🔧 Requisitos RAR

### Windows
1. Instalar [WinRAR](https://www.win-rar.com/download.html)
2. Adicionar `C:\Program Files\WinRAR` ao PATH
3. Reiniciar VS Code/terminal

### Linux
```bash
sudo apt install unrar
```

### macOS
```bash
brew install unar
```

---

## 🧪 Validação

### Teste ZIP
```powershell
# Criar ZIP de teste com subpastas
$zip = New-Object -ComObject shell.application
# Upload no módulo Auditoria
# Verificar estrutura preservada no Storage
```

### Teste RAR
```powershell
# Verificar backend RAR
.\.venv\Scripts\python.exe -c "import rarfile; print('OK')"
# Upload arquivo .rar com subpastas
# Verificar estrutura idêntica no Storage
```

---

## 📊 Vantagens da Simplificação

| Aspecto | Antes (ZIP/7z/RAR) | Agora (ZIP/RAR) |
|---------|---------------------|-----------------|
| **Dependências** | zipfile + py7zr + rarfile | zipfile + rarfile |
| **Complexidade** | 3 estratégias diferentes | 2 estratégias otimizadas |
| **ZIP Performance** | Extração temporária | Leitura direta (mais rápido) |
| **Warnings Pylance** | py7zr warnings | Zero warnings |
| **Manutenção** | 3 libs para manter | 2 libs para manter |

### Performance ZIP

**Antes (com .7z):**
- ZIP extraia para temp → caminhava árvore → upload
- Disco: ~2x o tamanho do ZIP
- Tempo: extração + upload

**Agora (otimizado):**
- ZIP lê membros diretamente → upload
- Disco: 0 bytes temporários
- Tempo: apenas upload

---

## 🎨 Interface

### Botão
```
"Enviar ZIP/RAR p/ Auditoria"
```

### Filtros de Arquivo
```python
filetypes=[
    ("Arquivos compactados", "*.zip *.rar"),
    ("ZIP", "*.zip"),
    ("RAR", "*.rar")
]
```

### Mensagem de Sucesso
```
Upload concluído para EMPRESA EXEMPLO LTDA — 12.345.678/0001-90.
42 arquivo(s) enviados para org123/456/GERAL/Auditoria/
```

---

## 🚀 Benefícios

1. **Menos dependências** — Removida py7zr (complexa)
2. **ZIP mais rápido** — Leitura direta sem temp files
3. **Código mais limpo** — Menos branches condicionais
4. **Zero warnings** — Pylance completamente limpo
5. **Foco nos essenciais** — ZIP (universal) + RAR (comum)

---

**Implementado:** Novembro 2025
**Python:** 3.13.7
**rarfile:** 4.2