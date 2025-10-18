# 📚 Pasta ajuda/ — Material Auxiliar

Esta pasta contém toda a documentação, testes e scripts de suporte do projeto **RC — Gestor de Clientes v1.0.29**.

> ⚠️ **Nota:** Esta pasta **NÃO é incluída no executável** gerado pelo PyInstaller. Serve apenas para desenvolvimento e documentação.

---

## 📁 Estrutura

```
ajuda/
├── docs/                        # 📖 Documentação técnica
│   ├── DEV-MAP.md              # Mapa de desenvolvimento
│   ├── BATCH-17-RELATORIO.md   # Relatórios de lotes
│   ├── DEADCODE-REPORT.md      # Análise de código morto
│   └── LOC-REPORT.md           # Contagem de linhas
├── tests/                       # 🧪 Testes unitários
│   ├── test_entrypoint.py
│   ├── test_net_session.py
│   ├── test_supabase_client_headers.py
│   └── ...
├── PROMPT-*-CHANGES.md          # 📝 Logs de mudanças por prompt
│   ├── PROMPT-5-CHANGES.md     # Este documento (consolidação)
│   └── ...
├── CHANGELOG.md                 # 📋 Histórico de versões
├── QUICK-START.md               # 🚀 Guia rápido de instalação
├── RELEASE-GUIDE.md             # 📦 Guia de release/build
├── README-Implantacao.txt       # 📋 Instruções de implantação
├── POLIMENTO-VISUAL-GUIA.md     # 🎨 Guia de polish visual
├── release-commands.ps1         # 🛠️ Scripts de release (PowerShell)
├── release-commands.sh          # 🛠️ Scripts de release (Bash)
├── release-curl-commands.ps1    # 🌐 Comandos curl para API
└── _consolidation_log.txt       # 📜 Log da última consolidação
```

---

## 📖 Documentos Importantes

### 🚀 Para Começar
- **[QUICK-START.md](QUICK-START.md)**: Instalação e primeira execução
- **[README-Implantacao.txt](README-Implantacao.txt)**: Deploy em produção

### 🔧 Para Desenvolvedores
- **[docs/DEV-MAP.md](docs/DEV-MAP.md)**: Mapa da arquitetura
- **[PROMPT-5-CHANGES.md](PROMPT-5-CHANGES.md)**: Última mudança (consolidação)
- **[CHANGELOG.md](CHANGELOG.md)**: Histórico completo de versões

### 📦 Para Release
- **[RELEASE-GUIDE.md](RELEASE-GUIDE.md)**: Como fazer build e release
- **[release-commands.ps1](release-commands.ps1)**: Scripts automatizados

### 🧪 Para Testes
- **[tests/](tests/)**: Suite completa de testes unitários
- Execute: `pytest tests/` ou `python -m pytest tests/`

---

## 🛠️ Scripts Úteis

### Consolidação e Limpeza

```powershell
# Visualizar o que será consolidado (dry-run)
python scripts/cleanup.py

# Aplicar consolidação
python scripts/cleanup.py --apply

# Remover apenas código legado
python scripts/cleanup.py --legacy-only --apply
```

### Testes

```powershell
# Rodar todos os testes
pytest tests/

# Teste específico
pytest tests/test_supabase_client_headers.py -v

# Com coverage
pytest tests/ --cov=infra --cov=core
```

---

## ❓ Por Que Consolidar?

### Antes (Raiz Bagunçada)
```
v1.0.29/
├── docs/
├── tests/
├── CHANGELOG.md
├── QUICK-START.md
├── RELEASE-GUIDE.md
├── README-Implantacao.txt
├── release-commands.ps1
├── app_gui.py
├── main.py
└── ...
```

### Depois (Raiz Limpa)
```
v1.0.29/
├── ajuda/              ← TODO material auxiliar aqui
│   ├── docs/
│   ├── tests/
│   └── ...
├── app_gui.py
├── main.py
├── requirements.txt
└── ...
```

**Benefícios:**
✅ Raiz do projeto limpa e profissional  
✅ Fácil identificar código de produção vs auxiliar  
✅ Build do PyInstaller mais rápido (menos arquivos pra escanear)  
✅ `ajuda/` não vai pro executável (não é importada)

---

## 🔍 FAQ

### 1. Por que `ajuda/` não vai pro build do PyInstaller?

O PyInstaller só inclui:
- Módulos Python importados pelo código
- Arquivos explicitamente listados em `datas=[]` no `.spec`

Como `ajuda/` não é importada e não está em `datas`, ela fica só no repo.

### 2. Como adicionar novos arquivos auxiliares?

Coloque diretamente em `ajuda/`:
```powershell
# Exemplo: novo guia
New-Item ajuda/DEPLOY-AZURE.md -ItemType File
```

Ou configure `scripts/cleanup.py` para mover automaticamente:
```python
MOVE_FILES_GLOBS = [
    # ... existentes ...
    "DEPLOY-*.md",  # ← adicione aqui
]
```

### 3. E se eu quiser desfazer a consolidação?

Mova manualmente de volta:
```powershell
Move-Item ajuda/docs/ docs/
Move-Item ajuda/tests/ tests/
# ... etc
```

Ou use git:
```powershell
git checkout HEAD~1 -- docs/ tests/
```

---

## 📜 Histórico de Mudanças

Ver documentos `PROMPT-*-CHANGES.md` para logs detalhados de cada iteração:
- **PROMPT-1**: Supabase Auth (email/senha)
- **PROMPT-2**: Session guard e cleanup
- **PROMPT-3**: Temas e overlay de loading
- **PROMPT-4**: Diagnóstico e retry lógico
- **PROMPT-5**: Consolidação de auxiliares (este)

---

## 📞 Suporte

Em caso de dúvidas sobre a estrutura ou documentação:
1. Consulte `QUICK-START.md` para setup básico
2. Leia `PROMPT-5-CHANGES.md` para detalhes da consolidação
3. Execute `python scripts/cleanup.py` para ver o que foi movido

---

**Última atualização:** 2025-10-18 (v1.0.29 — Consolidação)
