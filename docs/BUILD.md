# Guia de Build – RC Gestor de Clientes

Este documento descreve como gerar o executável e o instalador do RC Gestor.

---

## Visão Geral do Processo

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Código Fonte  │────▶│   PyInstaller   │────▶│   Inno Setup    │
│   (src/*.py)    │     │   (.spec)       │     │   (.iss)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        dist/RC-Gestor-         installer/Output/
                        Clientes-X.Y.Z.exe      RC-Gestor-Setup.exe
```

---

## Pré-requisitos

### Para gerar o executável (PyInstaller)

- Python 3.10+ com ambiente virtual ativado
- Dependências instaladas: `pip install -r requirements.txt`
- PyInstaller instalado: `pip install pyinstaller`

### Para gerar o instalador (Inno Setup)

- [Inno Setup 6.x](https://jrsoftware.org/isdl.php) instalado
- Executável já gerado pelo PyInstaller

---

## Parte 1: Gerando o Executável (PyInstaller)

### Arquivo de configuração

O projeto usa o arquivo `rcgestor.spec` na raiz, que define:

- **Entrypoint**: `src/app_gui.py`
- **Nome do executável**: `RC-Gestor-Clientes-{versão}.exe`
- **Ícone**: `rc.ico`
- **Arquivos extras**: `.env`, `CHANGELOG.md`, assets, templates

### Comando para build

```bash
# Ativar ambiente virtual primeiro
.\.venv\Scripts\Activate.ps1

# Gerar executável
pyinstaller rcgestor.spec
```

### Saída

O executável será gerado em:
```
dist/RC-Gestor-Clientes-X.Y.Z.exe
```

### Arquivos incluídos automaticamente

| Arquivo/Pasta | Destino no exe | Descrição |
|---------------|----------------|-----------|
| `rc.ico` | `.` | Ícone do aplicativo |
| `.env` | `.` | Configurações de ambiente |
| `CHANGELOG.md` | `.` | Histórico de versões |
| `assets/` | `assets/` | Imagens e recursos visuais |
| `templates/` | `templates/` | Templates de documentos |
| `infra/bin/7zip/` | `7z/` | Binários do 7-Zip |

### Verificação de versão

A versão é lida automaticamente de `src/version.py` e aplicada:
- No nome do arquivo `.exe`
- Nos metadados do Windows (via `version_file.txt`)

---

## Parte 2: Gerando o Instalador (Inno Setup)

### Arquivo de configuração

O script Inno Setup está em `installer/rcgestor.iss`.

### Passos para gerar o instalador

1. **Abra o Inno Setup Compiler**
   - Baixe em: https://jrsoftware.org/isdl.php

2. **Carregue o script**
   - File → Open → `installer/rcgestor.iss`

3. **Verifique os caminhos**
   - O script assume que o executável está em `dist/`
   - Ajuste `SourceDir` se necessário

4. **Compile**
   - Build → Compile (ou Ctrl+F9)

5. **Saída**
   - O instalador será gerado em `installer/Output/RC-Gestor-Setup-X.Y.Z.exe`

### O que o instalador faz

- Instala o executável em `C:\Program Files\RC Gestor\`
- Cria atalho no Menu Iniciar
- Cria atalho na Área de Trabalho (opcional)
- Registra desinstalador no Painel de Controle
- Associa extensões de arquivo (se configurado)

---

## Parte 3: Atualizando a Versão

Ao lançar uma nova versão, atualize os seguintes arquivos:

### 1. `src/version.py`

```python
__version__ = "X.Y.Z"  # Nova versão
```

### 2. `version_file.txt`

```
filevers=(X, Y, Z, 0),
prodvers=(X, Y, Z, 0),
...
StringStruct(u'FileVersion', u'X.Y.Z'),
StringStruct(u'ProductVersion', u'X.Y.Z')
```

### 3. `installer/rcgestor.iss`

```pascal
#define MyAppVersion "X.Y.Z"
```

### 4. `CHANGELOG.md`

Adicione entrada para a nova versão seguindo o formato Keep a Changelog.

---

## Troubleshooting

### Erro: "ModuleNotFoundError" no executável

Adicione o módulo faltante em `hiddenimports` no `rcgestor.spec`:

```python
hiddenimports=["tzdata", "tzlocal", "modulo_faltante"],
```

### Erro: Arquivo não encontrado no executável

Adicione o arquivo em `datas` no `rcgestor.spec`:

```python
add_file(BASE / "arquivo.ext", "pasta_destino")
```

### Executável muito grande

- Verifique se não há dependências desnecessárias em `requirements.txt`
- Use `--exclude-module` para módulos não utilizados
- Considere usar UPX (já habilitado no spec)

### Instalador não encontra arquivos

- Verifique se o PyInstaller foi executado antes
- Confirme que o caminho em `SourceDir` do `.iss` está correto
- Execute o Inno Setup como Administrador se necessário

---

## Checklist de Release

- [ ] Atualizar versão em `src/version.py`
- [ ] Atualizar `version_file.txt`
- [ ] Atualizar `installer/rcgestor.iss`
- [ ] Adicionar entrada no `CHANGELOG.md`
- [ ] Rodar testes: `pytest tests/ --maxfail=3`
- [ ] Rodar lint: `ruff check src/`
- [ ] Gerar executável: `pyinstaller rcgestor.spec`
- [ ] Testar executável em máquina limpa
- [ ] Gerar instalador com Inno Setup
- [ ] Testar instalador em máquina limpa
- [ ] Criar tag no Git: `git tag vX.Y.Z`
- [ ] Push da tag: `git push origin vX.Y.Z`

---

## Referências

- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [Inno Setup Documentation](https://jrsoftware.org/ishelp/)
- [Keep a Changelog](https://keepachangelog.com/)
