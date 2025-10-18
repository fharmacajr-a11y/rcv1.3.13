# 🚀 Guia de Commit — v1.0.29

Este documento orienta o commit das mudanças da consolidação de arquivos auxiliares.

---

## 📋 O Que Foi Feito

### Consolidação
- ✅ Criada pasta `ajuda/` para todo material auxiliar
- ✅ Movidos `docs/` e `tests/` para `ajuda/`
- ✅ Movidos guias, changelogs e scripts de release para `ajuda/`
- ✅ Removidos todos os `__pycache__/` e `.pyc`

### Documentação
- ✅ Criado `ajuda/PROMPT-5-CHANGES.md` (relatório completo)
- ✅ Criado `ajuda/README.md` (índice de docs)
- ✅ Criado `ajuda/CONSOLIDACAO-RESUMO.md` (resumo executivo)
- ✅ Atualizado `README.md` (estrutura e quick start)

### Utilitários
- ✅ Criado `scripts/cleanup.py` (script reutilizável)
- ✅ Gerado `ajuda/_consolidation_log.txt` (log técnico)

---

## 🔍 Arquivos Alterados

### Novos Arquivos
```
ajuda/
├── PROMPT-5-CHANGES.md
├── README.md
├── CONSOLIDACAO-RESUMO.md
├── _consolidation_log.txt
├── docs/                    (movido)
├── tests/                   (movido)
├── CHANGELOG.md             (movido)
├── QUICK-START.md           (movido)
└── ... (8 arquivos movidos)

scripts/
└── cleanup.py               (criado)
```

### Arquivos Modificados
```
README.md                    (atualizado)
```

### Arquivos Removidos
```
docs/                        (movido → ajuda/docs/)
tests/                       (movido → ajuda/tests/)
CHANGELOG.md                 (movido → ajuda/)
QUICK-START.md               (movido → ajuda/)
RELEASE-GUIDE.md             (movido → ajuda/)
... (5 arquivos movidos)
__pycache__/                 (33 pastas removidas)
*.pyc                        (126 arquivos removidos)
```

---

## 🔐 Checklist Pré-Commit

Antes de fazer o commit, valide:

- [ ] App inicia normalmente: `python app_gui.py`
- [ ] Login funcional (Supabase Auth)
- [ ] Menu "Ajuda → Diagnóstico…" funcional
- [ ] Pasta `ajuda/` criada e populada
- [ ] `docs/` e `tests/` estão em `ajuda/`
- [ ] Nenhum `__pycache__/` na raiz
- [ ] README.md atualizado
- [ ] Documentação criada (3 novos arquivos em `ajuda/`)

---

## 📝 Comandos de Commit

### 1. Verificar Status
```powershell
git status
```

**Esperado:**
- 🟢 Novos: `ajuda/*`, `scripts/cleanup.py`
- 🟡 Modificados: `README.md`
- 🔴 Deletados: `docs/`, `tests/`, `CHANGELOG.md`, etc.

### 2. Adicionar Mudanças
```powershell
# Adicionar todos os arquivos
git add .

# Ou adicionar seletivamente
git add ajuda/
git add scripts/cleanup.py
git add README.md
git add -u  # adiciona deletions
```

### 3. Commit
```powershell
git commit -m "feat: consolidar material auxiliar em ajuda/ (v1.0.29)

- Criar pasta ajuda/ para docs, testes e guias
- Mover docs/ e tests/ para ajuda/
- Mover CHANGELOG.md, QUICK-START.md, RELEASE-GUIDE.md
- Mover scripts de release (*.ps1, *.sh)
- Remover __pycache__/ e *.pyc (159 itens)
- Criar scripts/cleanup.py (consolidação reutilizável)
- Atualizar README.md (estrutura e quick start)
- Documentar em ajuda/PROMPT-5-CHANGES.md

Refs: PROMPT-5"
```

### 4. Push
```powershell
git push origin main
# ou
git push
```

---

## 🔍 Validação Pós-Commit

Após o push, valide:

1. **GitHub/GitLab:**
   - [ ] Pasta `ajuda/` visível no repo
   - [ ] `docs/` e `tests/` não estão na raiz
   - [ ] README.md atualizado

2. **Clone Limpo:**
   ```powershell
   cd ..
   git clone <repo> v1.0.29-test
   cd v1.0.29-test
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python app_gui.py
   ```
   - [ ] App inicia normalmente
   - [ ] Pasta `ajuda/` presente

3. **Build:**
   ```powershell
   pyinstaller build/rc_gestor.spec --onefile
   ```
   - [ ] Build sem erros
   - [ ] `ajuda/` NÃO incluída no executável

---

## 🐛 Troubleshooting

### Problema: "fatal: pathspec 'docs/' did not match any files"

**Causa:** `docs/` já foi movido, não existe mais na raiz.

**Solução:**
```powershell
# Usar git add -u para adicionar deletions
git add -u
```

### Problema: "App não inicia após commit"

**Causa:** Algum import está quebrando.

**Solução:**
```powershell
# Verificar imports
python -c "import app_gui"

# Se houver erro, revisar:
# - infra/supabase_auth.py
# - ui/login/login.py
# - gui/main_window.py
```

### Problema: "Build inclui ajuda/"

**Causa:** `ajuda/` está sendo importada ou listada em `datas`.

**Solução:**
```powershell
# Verificar imports de ajuda/
grep -r "from ajuda" .
grep -r "import ajuda" .

# Verificar build/rc_gestor.spec
# Procurar por 'ajuda' em datas=[]
```

---

## 📚 Referências

- **Relatório Completo:** `ajuda/PROMPT-5-CHANGES.md`
- **Resumo Executivo:** `ajuda/CONSOLIDACAO-RESUMO.md`
- **Log Técnico:** `ajuda/_consolidation_log.txt`
- **Script Usado:** `scripts/cleanup.py`

---

## ✅ Checklist Final

Antes de encerrar:

- [ ] Commit realizado com sucesso
- [ ] Push realizado com sucesso
- [ ] README.md visível no GitHub/GitLab
- [ ] Pasta `ajuda/` visível no repo remoto
- [ ] Clone limpo funciona
- [ ] Build do PyInstaller sem erros

---

**Última atualização:** 2025-10-18  
**Versão:** v1.0.29 — Consolidação de Auxiliares
