# 📦 Estratégia de Gerenciamento de Dependências - RC Gestor v1.2.31

**Data:** 20 de novembro de 2025  
**Sprint:** P1-SEG/DEP  
**Documento:** requirements_strategy.md  
**Status:** 📋 **PROPOSTA PARA APROVAÇÃO**

---

## 🎯 Objetivo

Estabelecer uma estratégia clara e sustentável para gerenciamento de dependências do projeto, separando **dependências de produção** (runtime) de **dependências de desenvolvimento** (dev tools).

---

## 📊 Situação Atual

### Problemas Identificados

1. **Mistura de dependências:**
   - Ferramentas de desenvolvimento (pytest, ruff, mypy) no mesmo arquivo que dependências de produção
   - Dificulta análise de segurança focada em runtime
   - Aumenta tempo de instalação em ambientes de produção

2. **Duplicações removidas (Sprint P1):**
   - ~~pdfminer.six~~ → Removido (CVE)
   - ~~PyPDF2~~ → Removido (duplicado com pypdf)
   - ~~requests~~ → Removido (duplicado com httpx)

3. **Dependências não documentadas:**
   - Falta de comentários explicando para que serve cada pacote crítico
   - Dificulta auditoria e atualização

---

## 🏗️ Proposta de Estrutura

### Arquivos Propostos

```
requirements/
├── base.txt           # Dependências compartilhadas (prod + dev)
├── production.txt     # Apenas runtime (herda base.txt)
├── development.txt    # Ferramentas de dev (herda production.txt)
└── README.md          # Documentação da estrutura
```

**Alternativa Simplificada (RECOMENDADA para início):**
```
requirements.txt       # Produção (runtime)
requirements-dev.txt   # Desenvolvimento (testes, lint, build)
```

---

## 📋 Classificação de Dependências

### 🟢 PRODUÇÃO (requirements.txt)

Pacotes **essenciais** para execução do aplicativo instalado pelo usuário final.

#### Interface Gráfica (Tkinter + Extensões)
```
ttkbootstrap==1.14.2      # Framework moderno para Tkinter
sv_ttk==2.6.1             # Tema Sun Valley para ttk
tkinterweb==4.4.4         # Navegador web embarcado (preview)
tkinterweb-tkhtml==1.1.4  # Renderizador HTML para tkinterweb
```

#### Backend & Database
```
# Supabase SDK
supabase==2.22.0
supabase-auth==2.22.0
supabase-functions==2.22.0
storage3==2.22.0
realtime==2.22.0
postgrest==2.22.0
websockets==15.0.1

# PostgreSQL Drivers
psycopg==3.2.10           # Driver psycopg3 (async)
psycopg-binary==3.2.10    # Binários compilados
psycopg2-binary==2.9.10   # Driver psycopg2 (legacy/sync)

# ORM & Migrations
SQLAlchemy==2.0.36
alembic==1.13.2
```

#### HTTP & Networking
```
httpx==0.27.2             # Cliente HTTP (async, HTTP/2)
httpcore==1.0.9           # Core do httpx
h11==0.16.0               # HTTP/1.1 protocol
h2==4.3.0                 # HTTP/2 protocol
hpack==4.1.0              # Header compression (HTTP/2)
hyperframe==6.1.0         # HTTP/2 framing
certifi==2025.8.3         # Certificados CA
urllib3==2.5.0            # HTTP client (transitive)
```

#### Segurança & Criptografia
```
cryptography==46.0.1      # Primitivas criptográficas
bcrypt==5.0.0             # Hashing de senhas
PyJWT==2.10.1             # JSON Web Tokens
passlib==1.7.4            # Framework de hashing de senhas
cffi==2.0.0               # FFI para cryptography
pycparser==2.23           # Parser C para CFFI
```

#### Processamento de Arquivos
```
# PDFs
pypdf==6.2.0              # Extração de texto (fallback)
PyMuPDF==1.26.4           # Extração robusta + preview (primário)
pytesseract==0.3.13       # OCR para PDFs escaneados
pillow==10.4.0            # Manipulação de imagens

# Arquivos Compactados
rarfile>=4.2              # Suporte a RAR
py7zr>=1.0.0              # Suporte a 7z
```

#### Validação de Dados
```
pydantic==2.12.0          # Validação e serialização
pydantic-settings==2.6.0  # Carregamento de settings
pydantic_core==2.41.1     # Core do pydantic (Rust)
annotated-types==0.7.0    # Tipos anotados
typing_extensions==4.15.0 # Backport de tipos
typing-inspection==0.4.2  # Inspeção de tipos
```

#### Utilitários & Helpers
```
python-dotenv==1.0.1      # Carregamento de .env
click==8.3.0              # CLI framework
rich==14.2.0              # Terminal formatado
colorama==0.4.6           # Cores no terminal (Windows)
PyYAML==6.0.2             # Parser YAML
PyYAML-ft==8.0.0          # YAML full-featured
tzdata==2025.2            # Timezone database
tzlocal==5.3.1            # Detecção de timezone
```

#### Dependências Transitivas (Documentadas)
```
anyio==4.11.0             # Async primitives (httpx, supabase)
sniffio==1.3.1            # Detecção de async library
idna==3.10                # Internacionalized Domain Names
charset-normalizer==3.4.3 # Detecção de encoding
iniconfig==2.1.0          # Parser INI
packaging==25.0           # Versionamento de pacotes
platformdirs==4.5.0       # Diretórios específicos de plataforma
```

**Total Estimado:** ~65 pacotes

---

### 🔧 DESENVOLVIMENTO (requirements-dev.txt)

Pacotes usados **apenas** para desenvolvimento, testes, build e CI/CD.

```
# Herdar produção
-r requirements.txt

# ============================================================================
# TESTING
# ============================================================================
pytest==8.4.2
pytest-cov==7.0.0
coverage==7.10.7

# ============================================================================
# CODE QUALITY & LINTING
# ============================================================================
ruff==0.14.0              # Linter rápido (substitui flake8/isort)
black==25.9.0             # Formatador de código
mypy==1.18.2              # Type checker
mypy_extensions==1.1.0    # Extensões para mypy
bandit==1.8.6             # Security linter
vulture==2.14             # Dead code finder
deptry==0.23.1            # Dependency checker
import-linter==2.5.2      # Import rules enforcer

# ============================================================================
# SECURITY AUDIT
# ============================================================================
pip_audit==2.9.0          # CVE scanner
cyclonedx-python-lib==9.1.0  # SBOM generation (transitive)
license-expression==30.4.4   # License parsing (transitive)
packageurl-python==0.17.5    # Package URL (transitive)
py-serializable==2.1.0       # Serialization (transitive)
defusedxml==0.7.1            # XML parsing (transitive)
sortedcontainers==2.4.0      # Data structures (transitive)

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================
pip-tools==7.5.1          # pip-compile/pip-sync
pipdeptree==2.29.0        # Visualização de árvore de deps
pip-api==0.0.34           # API programática do pip
pip-requirements-parser==32.0.1  # Parser de requirements
requirements-parser==0.13.0      # Parser alternativo

# ============================================================================
# BUILD & PACKAGING
# ============================================================================
pyinstaller==6.16.0       # Empacotador de executáveis
pyinstaller-hooks-contrib==2025.9  # Hooks para libs populares
build==1.3.0              # Build backend PEP 517
wheel==0.45.1             # Wheel packaging
setuptools==80.9.0        # Setup tools (legacy)
pefile==2023.2.7          # PE file parser (Windows)
altgraph==0.17.4          # Graph data structure (PyInstaller)
pywin32-ctypes==0.2.3     # Windows API (PyInstaller)

# ============================================================================
# PRE-COMMIT & VCS HOOKS
# ============================================================================
pre_commit==4.3.0
cfgv==3.4.0               # Config validation
identify==2.6.15          # File identification
nodeenv==1.9.1            # Node.js env (para hooks JS)
virtualenv==20.35.3       # Virtualenv management
filelock==3.20.0          # File locking

# ============================================================================
# DOCUMENTATION & ANALYSIS
# ============================================================================
graphviz==0.21            # Geração de grafos
pydeps==3.0.1             # Visualização de deps Python
grimp==3.12               # Import graph analysis
libcst==1.8.5             # Concrete Syntax Tree (refactoring)
annotated-doc==0.0.3      # Doc annotations
boolean.py==5.0           # Boolean algebra
pyparsing==3.2.5          # Parser combinators
pytokens==0.2.0           # Token utilities
Pygments==2.19.2          # Syntax highlighting
markdown-it-py==4.0.0     # Markdown parser
mdurl==0.1.2              # Markdown URL utilities
MarkupSafe==3.0.3         # Safe string markup

# ============================================================================
# API DEVELOPMENT (Supabase Edge Functions local testing)
# ============================================================================
fastapi==0.121.1          # Framework API (se usado em dev)
uvicorn==0.30.6           # ASGI server
starlette==0.49.3         # ASGI framework (transitive)

# ============================================================================
# AUXILIARY LIBRARIES
# ============================================================================
toml==0.10.2              # TOML parser
click==8.3.0              # CLI framework (pode estar em prod)
Mako==1.3.10              # Template engine (alembic)
deprecation==2.1.0        # Deprecation warnings
stdlib-list==0.11.1       # List of stdlib modules
stevedore==5.5.0          # Plugin loader
StrEnum==0.4.15           # String enums backport
CacheControl==0.14.3      # HTTP caching
msgpack==1.1.2            # MessagePack serialization
multidict==6.7.0          # Multi-value dict
propcache==0.4.1          # Property caching
yarl==1.22.0              # URL parsing
distlib==0.4.0            # Distribution utilities
pathspec==0.12.1          # Path matching (gitignore)
pluggy==1.6.0             # Plugin system (pytest)
pyproject_hooks==1.2.0    # PEP 517 hooks
```

**Total Estimado:** ~60 pacotes (+ 65 de produção = 125 total)

---

## 🚀 Implementação Proposta

### Fase 1: Criação de requirements-dev.txt (Esta Sprint)

```bash
# 1. Criar requirements-dev.txt com estrutura acima
touch requirements-dev.txt

# 2. Instalar ambiente de dev
pip install -r requirements-dev.txt

# 3. Validar build
pytest -v
pyinstaller rcgestor.spec --noconfirm

# 4. Documentar no README
```

### Fase 2: Migração Gradual (Sprint Futura)

```bash
# 1. Dividir requirements.txt atual em 2 arquivos
# requirements.txt (só produção)
# requirements-dev.txt (herda produção + dev tools)

# 2. Atualizar CI/CD
# - Jobs de teste: requirements-dev.txt
# - Build de release: requirements.txt

# 3. Atualizar documentação
# - INSTALACAO.md
# - CONTRIBUTING.md
# - README.md
```

### Fase 3: Estrutura Modular (Futuro - Se Necessário)

```
requirements/
├── base.txt          # Comuns a todos
├── production.txt    # -r base.txt + runtime
├── development.txt   # -r production.txt + dev tools
├── testing.txt       # -r production.txt + pytest/cov
└── build.txt         # -r base.txt + pyinstaller
```

---

## 📐 Convenções e Boas Práticas

### Formato de Comentários

```
# ============================================================================
# CATEGORIA (exemplo: TESTING)
# ============================================================================
pytest==8.4.2             # Framework de testes
pytest-cov==7.0.0         # Cobertura de testes
coverage==7.10.7          # Relatórios de cobertura
```

### Versionamento

- **Produção:** Sempre versões **exatas** (`==`)
- **Desenvolvimento:** Versões exatas OU compatíveis (`~=` para minor updates)
- **Exceções:** Libs de arquivo (`rarfile>=4.2`, `py7zr>=1.0.0`) se necessário

### Segurança

- **Auditoria semanal:** `pip-audit -r requirements.txt` no CI
- **Atualizações mensais:** Revisar dependências defasadas
- **CVEs críticos:** Patch imediato, mesmo que quebre minor compatibility

### Documentação

- **Cada seção deve ter:**
  1. Comentário de categoria
  2. Breve descrição de cada pacote (se não óbvio)
  3. Justificativa para dependências transitivas documentadas

---

## 🔄 Processo de Atualização

### Adicionando Nova Dependência

```bash
# 1. Determinar se é PROD ou DEV
# 2. Adicionar ao arquivo correto com versão exata
echo "nova-lib==1.2.3  # Descrição do propósito" >> requirements.txt

# 3. Instalar e testar
pip install nova-lib==1.2.3
pytest -v

# 4. Commitar com mensagem semântica
git add requirements.txt
git commit -m "deps: Adicionar nova-lib 1.2.3 (motivo)"
```

### Atualizando Dependência Existente

```bash
# 1. Verificar changelog da lib
# 2. Atualizar versão
# 3. Rodar testes completos
pytest -v

# 4. Validar build (se for dep de prod)
pyinstaller rcgestor.spec --noconfirm

# 5. Commitar
git commit -m "deps: Atualizar lib de X.Y.Z para A.B.C (breaking/feature/fix)"
```

### Removendo Dependência

```bash
# 1. Garantir que não há imports no código
rg "^import lib|^from lib" src/

# 2. Verificar dependentes com pipdeptree
pipdeptree -r -p lib-name

# 3. Remover e testar
# Deixar comentário explicando remoção
# lib-name==1.0.0  # ❌ REMOVIDO: Motivo da remoção

# 4. Rodar suite completa
pytest -v
```

---

## 📊 Métricas de Saúde

### Indicadores

| Métrica | Meta | Atual |
|---------|------|-------|
| **Dependências de Produção** | < 70 | ~65 |
| **Dependências Duplicadas** | 0 | 0 ✅ |
| **CVEs Conhecidos** | 0 | 0 ✅ |
| **Dependências Defasadas (>1 ano)** | < 5% | TBD |
| **Licenças Incompatíveis** | 0 | 0 (assumido) |

### Auditoria Trimestral

- [ ] Revisar **todas** as dependências
- [ ] Atualizar libs com CVEs
- [ ] Considerar alternativas mais leves
- [ ] Documentar decisões de manter versões antigas

---

## 🎯 Próximos Passos

### Sprint Atual (P1-SEG/DEP)

- [x] Documentar estratégia (este arquivo)
- [ ] Criar `requirements-dev.txt` inicial
- [ ] Atualizar `.gitignore` para arquivos gerados
- [ ] Documentar em `CONTRIBUTING.md`

### Sprint Futura (DEP-002)

- [ ] Separar completamente prod/dev
- [ ] Atualizar CI/CD para usar arquivos corretos
- [ ] Migrar documentação (README, INSTALACAO)
- [ ] Automatizar validação de requirements no pre-commit

### Melhorias Contínuas

- [ ] Implementar `dependabot` ou equivalente
- [ ] Dashboard de dependências (ex: `libraries.io`)
- [ ] SBOM (Software Bill of Materials) automatizado
- [ ] Política de EOL para libs (ex: não usar libs sem manutenção há >2 anos)

---

## 📚 Referências

- **PEP 508:** Dependency specification
- **PEP 440:** Version identification
- **pip-tools:** https://github.com/jazzband/pip-tools
- **pip-audit:** https://github.com/pypa/pip-audit
- **Python Packaging Guide:** https://packaging.python.org/

---

**Status:** 📋 Proposta pronta para revisão  
**Aprovação Pendente:** Product Owner / Tech Lead  
**Implementação Estimada:** Sprint P1 (parcial) + Sprint DEP-002 (completa)
