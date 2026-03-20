# Guia de Contribuição - RC Gestor de Clientes

**Versão:** v1.6.23  
**Data:** Março de 2026  
**Branch principal:** `main`

---

## 📋 Visão Geral

O **RC Gestor de Clientes** é uma aplicação desktop desenvolvida em Python usando Tkinter/CustomTkinter, voltada para gestão de clientes e documentos com integração ao Supabase.

Para setup completo, veja também [docs/SETUP.md](docs/SETUP.md).

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

### 4. Instalar hooks do pre-commit

**IMPORTANTE:** Configure os hooks de pre-commit para garantir qualidade de código antes de cada commit:

```powershell
pre-commit install
pre-commit run --all-files  # primeira vez
```

Após essa configuração:

- ✅ Antes de cada commit, o pre-commit executará automaticamente:
  - Ruff (linter e formatador Python)
  - Verificação de trailing whitespace
  - Garantia de nova linha no final dos arquivos
  - Validação de sintaxe YAML/TOML/JSON
  - Detecção de merge conflicts
  - Normalização de line endings
  - **Enforcement de políticas CustomTkinter** (ver abaixo)

- ⚠️ **Se algum hook falhar** (ex: ruff encontrar problema de lint/formato), você precisa:
  1. Revisar as correções automáticas feitas pelo pre-commit
  2. Adicionar os arquivos corrigidos (`git add <arquivos>`)
  3. Tentar o commit novamente

- 🚫 **Não use `--no-verify`** para pular pre-commit, exceto em casos muito específicos (ex: commits de docs/merge)

#### 🎨 Política CustomTkinter (Single Source of Truth)

**REGRA DE OURO:** Nunca importe `customtkinter` diretamente em qualquer arquivo do projeto.

✅ **CORRETO:**
```python
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if HAS_CUSTOMTKINTER:
    # usar ctk.CTkButton, etc.
```

❌ **PROIBIDO:**
```python
import customtkinter  # ❌ HOOK VAI FALHAR!
from customtkinter import CTkButton  # ❌ HOOK VAI FALHAR!
```

**Por quê?**
- `src/ui/ctk_config.py` é o **único arquivo permitido** para importar customtkinter
- Isso garante Single Source of Truth (SSoT) para detecção de CTk
- Evita duplicação de lógica try/except em múltiplos módulos
- Facilita manutenção e debugging

**O que acontece se eu importar direto?**
- ⚠️ O hook `no-direct-customtkinter-import` do pre-commit **vai falhar o commit**
- ⚠️ A CI/CD no GitHub Actions **vai falhar o PR**
- 📝 Você precisará refatorar para usar `src.ui.ctk_config`

**Arquivo whitelist (permitido):**
- `src/ui/ctk_config.py` (único permitido)

### 5. Validar instalação rodando testes

```powershell
pytest -v
```

**Resultado esperado:** Todos os testes devem passar (1035+ testes).

```
======================= 1035 passed in ~50s =======================
```

#### 📊 Coverage (Cobertura de Testes)

A CI do projeto roda testes com medição de cobertura e **falha automaticamente se a cobertura total ficar abaixo de 25%**.

Para rodar localmente com coverage (recomendado antes de abrir PR):

```powershell
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -v
```

Este comando:
- `--cov=src`: mede cobertura do código em `src/`
- `--cov-report=term-missing`: mostra quais linhas NÃO estão cobertas
- `--cov-fail-under=25`: falha se cobertura total < 25%
- `-v`: modo verbose (mostra cada teste)

### Bandit (an?lise de seguran?a)

Use o Bandit para varrer o reposit?rio antes de releases de QA. Como esta c?pia pode ter sido clonada de uma vers?o anterior, o `bandit.exe` pode continuar apontando para outro Python e disparar erros como:

> Fatal error in launcher: Unable to create process using '"C:\...v1.2.64\.venv\Scripts\python.exe" ...'

Para garantir que a ferramenta esteja alinhada com a venv atual (ex: `v1.2.79`), siga estes passos:

1. Ative a venv correta do projeto:

   ```powershell
   .venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

2. Reinstale o Bandit apontando explicitamente para o Python da venv (isto corrige o launcher):

   ```powershell
   python -m pip install --force-reinstall bandit
   ```

3. Rode o scan apenas nos diret?rios de produ??o (tests/ fica de fora para evitar falsos positivos B101 em asserts de pytest):

   ```powershell
   bandit -r src adapters data infra security -x tests
   ```

O Bandit se concentra no c?digo do aplicativo (src, adapters, data, infra, security). Diret?rios de teste n?o entram na varredura porque `assert` em testes (alertas B101) s?o esperados e n?o representam risco em produ??o. Se preferir rodar `bandit -r .`, o arquivo `.bandit` na raiz aplica os mesmos filtros automaticamente (tests, docs, caches). Se o erro do launcher aparecer novamente, repita o passo 2 certificando-se de que a venv ativa corresponda ao diret?rio atual.

---

## 📦 Como funciona a separação de dependências

### ❓ O que vai em `requirements.txt`?

**Apenas bibliotecas usadas em runtime** — pacotes que o aplicativo precisa para funcionar na máquina do usuário final:

- Interface gráfica: `customtkinter`, `sv_ttk`, `tkinterweb`
- Backend/Database: `supabase`, `psycopg`, `SQLAlchemy`, `alembic`
- HTTP/Networking: `httpx`, `certifi`, `urllib3`
- Segurança/Crypto: `cryptography`, `bcrypt`, `PyJWT`, `passlib`
- Processamento de arquivos: `pypdf`, `PyMuPDF`, `pillow`, `pytesseract`, `py7zr`
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
   git checkout main
   git pull origin main
   git checkout sua-branch
   git merge main
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

- **Setup para desenvolvimento:** [`docs/SETUP.md`](docs/SETUP.md)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)
- **Índice de documentação:** [`docs/README.md`](docs/README.md)

---

## ❓ FAQ

### Por que não usar `pip install -r requirements.txt` para dev?

Porque você perderia todas as ferramentas de teste, lint, build, etc. O `requirements.txt` contém **apenas** as libs de runtime. Para desenvolvimento, **sempre use `requirements-dev.txt`**.

### Posso usar `pip-compile` ou `poetry`?

O projeto atualmente usa gerenciamento manual de dependências com `pip` + arquivos `.txt` fixados. Se quiser propor migração para `pip-tools` (pip-compile) ou `poetry`, abra uma issue primeiro para discussão.

### Como sei se minha mudança quebrou algo?

Rode `python -m pytest tests/ -q` localmente. Se todos os 1035+ testes passarem, é muito provável que está tudo certo. A CI também rodará testes automaticamente no PR.

### Preciso atualizar `requirements.in` também?

O arquivo `requirements.in` existe como referência de dependências diretas de alto nível, mas o arquivo autoritativo é `requirements.txt`. Normalmente, edite apenas `requirements.txt` (produção) ou `requirements-dev.txt` (dev).

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
