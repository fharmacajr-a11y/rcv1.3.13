# Guia de Contribuição - RC Gestor de Clientes

**Versão:** v1.2.31+  
**Data:** 20 de novembro de 2025  
**Branch principal:** `qa/fixpack-04`

---

## 📋 Visão Geral

O **RC Gestor de Clientes** é uma aplicação desktop desenvolvida em Python usando Tkinter/ttkbootstrap, voltada para gestão de clientes e documentos com integração ao Supabase.

Este repositório segue **boas práticas de gerenciamento de dependências Python**, separando:

- **`requirements.txt`** → Dependências de **produção/runtime** (bibliotecas necessárias para o app rodar na máquina do usuário final)
- **`requirements-dev.txt`** → Dependências de **desenvolvimento** (ferramentas de teste, lint, type-checking, build, segurança, CI)

Esta separação mantém o ambiente de produção enxuto, facilita auditoria de segurança e acelera instalações em ambientes de CI/CD.

---

## 🛠️ Pré-requisitos

Antes de começar a contribuir, certifique-se de ter instalado:

- **Python 3.13** (versão oficial do projeto)
- **Git** (para controle de versão)
- **Ambiente virtual** (altamente recomendado para isolar dependências)

### Verificar versão do Python

```powershell
python --version
# Saída esperada: Python 3.13.x
```

---

## 🚀 Setup Rápido para Desenvolvimento

### 1. Clonar o repositório

```powershell
git clone https://github.com/fharmacajr-a11y/rcv1.3.13.git
cd rcv1.3.13
```

### 2. Criar e ativar ambiente virtual

```powershell
# Criar venv
python -m venv .venv

# Ativar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Ativar (Windows CMD)
.venv\Scripts\activate.bat

# Ativar (Linux/macOS)
source .venv/bin/activate
```

### 3. Instalar dependências de desenvolvimento

**IMPORTANTE:** Sempre use `requirements-dev.txt` para desenvolvimento:

```powershell
pip install --upgrade pip
pip install -r requirements-dev.txt
```

> **Por quê?** O arquivo `requirements-dev.txt` **já inclui** `requirements.txt` via `-r requirements.txt`, ou seja, ao instalar o ambiente de dev você automaticamente ganha:
>
> - ✅ Todas as dependências de produção (Tkinter, Supabase, httpx, pydantic, etc.)
> - ✅ Todas as ferramentas de desenvolvimento (pytest, ruff, mypy, pip-audit, pyinstaller, pre-commit, etc.)

### 4. Validar instalação rodando testes

```powershell
pytest -v
```

**Resultado esperado:** Todos os testes devem passar (215+ testes).

```
======================= 215 passed in ~30s =======================
```

---

## 📦 Como funciona a separação de dependências

### ❓ O que vai em `requirements.txt`?

**Apenas bibliotecas usadas em runtime** — pacotes que o aplicativo precisa para funcionar na máquina do usuário final:

- Interface gráfica: `ttkbootstrap`, `sv_ttk`, `tkinterweb`
- Backend/Database: `supabase`, `psycopg`, `SQLAlchemy`, `alembic`
- HTTP/Networking: `httpx`, `certifi`, `urllib3`
- Segurança/Crypto: `cryptography`, `bcrypt`, `PyJWT`, `passlib`
- Processamento de arquivos: `pypdf`, `PyMuPDF`, `pillow`, `pytesseract`, `rarfile`, `py7zr`
- Validação/Config: `pydantic`, `python-dotenv`, `PyYAML`
- Utilitários: `click`, `rich`, `colorama`, `tzdata`, `tzlocal`

**Total:** ~65 pacotes de produção (111 linhas com comentários/organização)

### ❓ O que vai em `requirements-dev.txt`?

**Ferramentas de desenvolvimento, testes, qualidade, build e CI** — pacotes usados apenas por desenvolvedores ou pipelines de CI/CD:

#### 🧪 Testing
- `pytest`, `pytest-cov`, `coverage`

#### 🔍 Code Quality
- `ruff` (linter/formatter moderno)
- `black` (formatador de código)
- `mypy` (type-checking estático)
- `bandit` (análise de segurança)
- `vulture` (detecção de código morto)
- `deptry`, `import-linter` (análise de imports/dependências)

#### 🛡️ Security Audit
- `pip-audit` (scanner de CVEs)
- `cyclonedx-python-lib`, `license-expression` (análise de licenças/SBOM)

#### 📦 Dependency Management
- `pip-tools`, `pipdeptree`, `pip-requirements-parser`

#### 🏗️ Build & Packaging
- `pyinstaller` (criação de executáveis)
- `build`, `wheel`, `setuptools`
- `pefile` (manipulação de executáveis Windows)

#### 🔧 Pre-commit
- `pre_commit` (hooks de git)
- `cfgv`, `identify`, `nodeenv`, `virtualenv`

#### 📚 Documentation & Dev Tools
- `graphviz`, `pydeps`, `grimp`, `libcst`
- `fastapi`, `uvicorn` (ferramentas de API para desenvolvimento)

**Total:** ~60 pacotes de desenvolvimento (117 linhas)

### 📏 Regra prática para novos contribuidores

Ao adicionar uma nova dependência, pergunte-se:

> **"O aplicativo precisa disso para rodar na máquina do usuário final?"**

- ✅ **SIM** → Adicione em `requirements.txt` (seção apropriada com comentário)
- ❌ **NÃO** (é só para testes/dev/build) → Adicione em `requirements-dev.txt` (categoria apropriada)

**Exemplos:**

| Pacote | Arquivo | Motivo |
|--------|---------|--------|
| `httpx` | `requirements.txt` | App faz requisições HTTP ao Supabase |
| `pytest` | `requirements-dev.txt` | Só usado para rodar testes |
| `cryptography` | `requirements.txt` | App criptografa dados locais |
| `ruff` | `requirements-dev.txt` | Só usado para lint/format do código |
| `pyinstaller` | `requirements-dev.txt` | Só usado para gerar executável |

Esta abordagem segue padrões comuns na comunidade Python ([Real Python - Managing Dependencies](https://realpython.com/python-virtual-environments-a-primer/)) e ajuda a manter o ambiente de produção mais leve e seguro.

---

## 🔄 Fluxo básico para abrir PR

### Antes de abrir um Pull Request

1. **Atualizar sua branch** com a principal:

   ```powershell
   git checkout qa/fixpack-04
   git pull origin qa/fixpack-04
   git checkout sua-branch
   git merge qa/fixpack-04
   ```

2. **Rodar testes localmente:**

   ```powershell
   pytest -v
   ```

   ✅ Certifique-se de que todos os testes passam.

3. **(Opcional) Verificar qualidade de código:**

   ```powershell
   # Rodar linter
   ruff check .

   # Formatar código (se habilitado)
   ruff format .

   # Type-checking (se aplicável)
   mypy src/
   ```

### Ao abrir o PR

- **Título claro:** Use prefixos como `feat:`, `fix:`, `docs:`, `deps:`, `refactor:`, `test:`, `ci:` (seguindo convenção de commits)
  
  Exemplos:
  - `feat: adicionar filtro de busca por data`
  - `fix: corrigir erro ao carregar PDF`
  - `docs: atualizar CONTRIBUTING com fluxo de testes`
  - `deps: atualizar httpx para 0.28.0`

- **Descrição:** Explique brevemente:
  - O que foi alterado
  - Por que foi necessário
  - Como testar (se aplicável)

- **Commits:** Tente manter histórico limpo. Se fizer muitos commits pequenos durante desenvolvimento, considere fazer squash antes de mergear.

### Estilo de Código

- Siga **PEP 8** (formatação automática com `ruff` ou `black`)
- Use **type hints** sempre que possível (seguindo padrão do projeto)
- Docstrings em funções públicas importantes (estilo Google ou NumPy)
- Comentários em português (idioma do projeto)

---

## 📚 Como lidar com novas dependências

### ➕ Adicionar dependência de PRODUÇÃO

Quando o aplicativo precisa de uma nova biblioteca para funcionar em runtime:

1. **Decidir se é realmente necessário em produção:**
   - A lib é usada em código que roda na máquina do usuário final?
   - Não existe alternativa já instalada?

2. **Adicionar em `requirements.txt` com versão fixa:**

   ```text
   # HTTP & Networking
   httpx==0.27.2             # Cliente HTTP (async, HTTP/2)
   requests==2.32.5          # Cliente HTTP (sync) - NOVA LIB
   ```

   - Use `==` para fixar versão exata (evita surpresas em builds)
   - Adicione comentário curto explicando uso
   - Insira na seção apropriada (GUI, Backend, HTTP, Security, etc.)

3. **Instalar localmente e testar:**

   ```powershell
   pip install requests==2.32.5
   pip freeze | findstr requests
   # Atualizar requirements.txt com a versão exata
   
   # Rodar testes
   pytest -v
   ```

4. **Verificar segurança (CVEs):**

   ```powershell
   pip-audit -r requirements.txt
   ```

   ⚠️ Se forem detectadas vulnerabilidades, considere outra versão ou lib alternativa.

5. **Commitar mudança:**

   ```powershell
   git add requirements.txt
   git commit -m "deps: adicionar requests==2.32.5 para feature X"
   ```

### 🔧 Adicionar dependência de DESENVOLVIMENTO

Quando você precisa de uma ferramenta apenas para testes, lint, build, etc.:

1. **Adicionar em `requirements-dev.txt` na categoria correta:**

   ```text
   # ===========================
   # CODE QUALITY
   # ===========================
   pytest==8.4.2
   ruff==0.14.0
   pylint==3.0.3              # Linter adicional - NOVA FERRAMENTA
   ```

2. **Instalar e validar:**

   ```powershell
   pip install pylint==3.0.3
   pip freeze | findstr pylint
   
   # Testar ferramenta
   pylint src/
   
   # Validar que testes ainda passam
   pytest -v
   ```

3. **Commitar:**

   ```powershell
   git add requirements-dev.txt
   git commit -m "deps: adicionar pylint==3.0.3 para análise de código"
   ```

### ⬆️ Atualizar dependência existente

1. **Verificar versão atual:**

   ```powershell
   pip show httpx
   ```

2. **Testar versão mais recente:**

   ```powershell
   pip install --upgrade httpx
   pip freeze | findstr httpx
   # Ex: httpx==0.28.0
   
   # Rodar testes completos
   pytest -v
   ```

3. **Se tudo passar, atualizar arquivo apropriado:**

   ```powershell
   # Editar requirements.txt ou requirements-dev.txt
   # Trocar versão antiga pela nova
   
   git add requirements*.txt
   git commit -m "deps: atualizar httpx de 0.27.2 para 0.28.0"
   ```

4. **Se os testes quebrarem:**
   - Reverter (`pip install httpx==0.27.2`)
   - Investigar breaking changes no changelog da lib
   - Ajustar código do projeto se necessário

### 🗑️ Remover dependência não utilizada

1. **Verificar se realmente não é usada:**

   ```powershell
   # Buscar imports no código
   grep -r "import requests" src/
   grep -r "from requests" src/
   ```

2. **Se não houver nenhum import:**
   - Remover linha do arquivo apropriado
   - Desinstalar: `pip uninstall requests`
   - Rodar testes: `pytest -v`

3. **Commitar:**

   ```powershell
   git add requirements*.txt
   git commit -m "deps: remover requests (não utilizado)"
   ```

---

## 📖 Documentação Adicional

- **Estratégia completa de dependências:** [`docs/dev/requirements_strategy.md`](docs/dev/requirements_strategy.md)
- **Checklist de tarefas priorizadas:** [`docs/dev/checklist_tarefas_priorizadas.md`](docs/dev/checklist_tarefas_priorizadas.md)
- **Instalação para usuário final:** [`INSTALACAO.md`](INSTALACAO.md)
- **Histórico de releases:** [`docs/releases/`](docs/releases/)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

---

## ❓ FAQ

### Por que não usar `pip install -r requirements.txt` para dev?

Porque você perderia todas as ferramentas de teste, lint, build, etc. O `requirements.txt` contém **apenas** as libs de runtime. Para desenvolvimento, **sempre use `requirements-dev.txt`**.

### Posso usar `pip-compile` ou `poetry`?

O projeto atualmente usa gerenciamento manual de dependências com `pip` + arquivos `.txt` fixados. Se quiser propor migração para `pip-tools` (pip-compile) ou `poetry`, abra uma issue primeiro para discussão.

### Como sei se minha mudança quebrou algo?

Rode `pytest -v` localmente. Se todos os 215+ testes passarem, é muito provável que está tudo certo. A CI também rodará testes automaticamente no PR.

### Preciso atualizar `requirements.in` também?

Não existe `requirements.in` neste projeto no momento. Usamos apenas `requirements.txt` e `requirements-dev.txt` com versões fixadas manualmente.

### O que é o arquivo `rcgestor.spec`?

É a especificação do PyInstaller para build do executável Windows. **Não mexa neste arquivo** a menos que esteja trabalhando especificamente em melhorias do processo de build.

---

## 🤝 Código de Conduta

Este projeto adota um código de conduta básico:

- Seja respeitoso com outros contribuidores
- Críticas construtivas são bem-vindas, ataques pessoais não
- Mantenha discussões focadas no problema técnico
- Documente suas mudanças adequadamente

---

## 📞 Contato e Suporte

- **Issues:** Use o [GitHub Issues](https://github.com/fharmacajr-a11y/rcv1.3.13/issues) para reportar bugs ou sugerir melhorias
- **Discussões:** Use [GitHub Discussions](https://github.com/fharmacajr-a11y/rcv1.3.13/discussions) para perguntas gerais

---

**Obrigado por contribuir! 🎉**
