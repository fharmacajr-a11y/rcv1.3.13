# 📊 Análise Completa do Projeto - RC Gestor de Clientes

**Versão do Documento:** 1.0  
**Data de Geração:** 22 de dezembro de 2025  
**Versão do Projeto:** 1.4.72

---

## 📋 Índice

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Estrutura de Pastas e Arquivos](#2-estrutura-de-pastas-e-arquivos)
3. [Funcionalidades Principais](#3-funcionalidades-principais)
4. [Dependências e Configurações](#4-dependências-e-configurações)
5. [Fluxo de Trabalho](#5-fluxo-de-trabalho)
6. [Pontos Notáveis](#6-pontos-notáveis)
7. [Arquitetura do Sistema](#7-arquitetura-do-sistema)
8. [Testes e Qualidade](#8-testes-e-qualidade)

---

## 1. Visão Geral do Projeto

### 1.1 Descrição

O **RC – Gestor de Clientes** é um sistema desktop desenvolvido em **Python** para gestão de clientes, documentos e senhas. O software é voltado principalmente para:

- Escritórios de contabilidade
- Consultorias
- Farmácias

O objetivo principal é gerenciar informações de múltiplos clientes de forma organizada e segura.

### 1.2 Tecnologias Principais

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| **Linguagem** | Python | 3.10+ |
| **Interface Gráfica** | Tkinter + ttkbootstrap | 1.14.2+ |
| **Backend/Database** | Supabase (PostgreSQL) | 2.22.0+ |
| **ORM** | SQLAlchemy | 2.0.36+ |
| **HTTP Client** | httpx | 0.28.1+ |
| **Criptografia** | cryptography (Fernet) | 46.0.3+ |
| **Build** | PyInstaller | 6.16.0+ |
| **Testes** | pytest | 8.4.2+ |
| **Linting** | ruff, mypy, bandit | Várias |

### 1.3 Plataforma

- **Sistema Operacional:** Windows 10+ (64-bit)
- **Requisitos:** 4GB RAM mínimo, conexão com internet

---

## 2. Estrutura de Pastas e Arquivos

### 2.1 Visão Geral da Hierarquia

```
v1.4.79/
├── 📁 src/                    # Código fonte principal
├── 📁 infra/                  # Infraestrutura (DB, HTTP, Auth)
├── 📁 adapters/               # Adaptadores de storage
├── 📁 data/                   # Tipos de domínio e repositórios
├── 📁 security/               # Módulo de criptografia
├── 📁 tests/                  # Suíte de testes
├── 📁 docs/                   # Documentação
├── 📁 assets/                 # Recursos visuais (ícones, imagens)
├── 📁 config/                 # Configurações (API keys)
├── 📁 helpers/                # Utilitários auxiliares
├── 📁 scripts/                # Scripts de automação
├── 📁 tools/                  # Ferramentas de desenvolvimento
├── 📁 migrations/             # Migrações de banco de dados
├── 📁 installer/              # Arquivos do instalador
├── 📁 htmlcov/                # Relatórios de cobertura HTML
├── 📁 reports/                # Relatórios de análise
├── 📄 main.py                 # Entry point principal
├── 📄 requirements.txt        # Dependências de produção
├── 📄 requirements-dev.txt    # Dependências de desenvolvimento
├── 📄 pyproject.toml          # Configuração do projeto Python
├── 📄 pytest.ini              # Configuração do pytest
└── 📄 README.md               # Documentação principal
```

### 2.2 Detalhamento das Pastas Principais

#### 📁 `src/` - Código Fonte Principal

```
src/
├── app_gui.py              # Entry-point da aplicação GUI
├── app_core.py             # Ações de alto nível (CRUD, lixeira)
├── app_status.py           # Gerenciamento de status
├── app_utils.py            # Utilitários da aplicação
├── cli.py                  # Interface de linha de comando
├── version.py              # Gerenciamento de versão
├── 📁 core/                # Núcleo do sistema
│   ├── bootstrap.py        # Inicialização do ambiente
│   ├── auth_bootstrap.py   # Bootstrap de autenticação
│   ├── auth_controller.py  # Controlador de autenticação
│   ├── logger.py           # Sistema de logging
│   ├── models.py           # Modelos de dados
│   ├── navigation_controller.py  # Navegação entre telas
│   ├── status_monitor.py   # Monitor de saúde da conexão
│   ├── 📁 auth/            # Autenticação local
│   ├── 📁 services/        # Serviços de domínio
│   ├── 📁 db_manager/      # Gerenciador de banco de dados
│   └── 📁 session/         # Gerenciamento de sessão
├── 📁 modules/             # Módulos funcionais
│   ├── 📁 clientes/        # Gestão de clientes
│   ├── 📁 passwords/       # Gestão de senhas
│   ├── 📁 auditoria/       # Auditoria de documentos
│   ├── 📁 hub/             # Tela principal (dashboard)
│   ├── 📁 lixeira/         # Recuperação de clientes
│   ├── 📁 cashflow/        # Fluxo de caixa
│   ├── 📁 chatgpt/         # Integração com IA
│   ├── 📁 anvisa/          # Upload de documentos ANVISA
│   ├── 📁 login/           # Tela de login
│   ├── 📁 notas/           # Sistema de notas
│   ├── 📁 main_window/     # Janela principal
│   ├── 📁 uploads/         # Sistema de upload de arquivos
│   └── 📁 pdf_tools/       # Ferramentas para PDFs
├── 📁 ui/                  # Componentes de interface
│   ├── components.py       # Componentes reutilizáveis
│   ├── menu_bar.py         # Barra de menu
│   ├── topbar.py           # Barra superior
│   ├── status_footer.py    # Rodapé com status
│   ├── theme.py            # Configuração de temas
│   └── 📁 dialogs/         # Caixas de diálogo
└── 📁 utils/               # Utilitários gerais
```

#### 📁 `infra/` - Infraestrutura

```
infra/
├── supabase_client.py      # Cliente Supabase (barrel module)
├── supabase_auth.py        # Autenticação Supabase
├── settings.py             # Persistência de configurações
├── healthcheck.py          # Verificação de saúde
├── archive_utils.py        # Manipulação de arquivos compactados
├── db_schemas.py           # Esquemas de banco de dados
├── net_session.py          # Gerenciamento de sessão de rede
├── net_status.py           # Status de conectividade
├── 📁 supabase/            # Módulos Supabase específicos
│   ├── db_client.py        # Cliente de banco de dados
│   ├── storage_client.py   # Cliente de storage
│   ├── auth_client.py      # Cliente de autenticação
│   └── http_client.py      # Cliente HTTP configurado
├── 📁 repositories/        # Repositórios de dados
└── 📁 http/                # Configurações HTTP (retry, timeout)
```

#### 📁 `adapters/` - Adaptadores

```
adapters/
└── 📁 storage/
    ├── api.py              # API pública de storage
    ├── port.py             # Interface/Port do storage
    └── supabase_storage.py # Implementação Supabase
```

#### 📁 `security/` - Segurança

```
security/
├── __init__.py
└── crypto.py               # Criptografia Fernet para senhas
```

#### 📁 `tests/` - Testes

```
tests/
├── conftest.py             # Configuração global do pytest
├── 📁 unit/                # Testes unitários
│   ├── 📁 modules/         # Testes por módulo
│   │   ├── 📁 clientes/
│   │   ├── 📁 passwords/
│   │   ├── 📁 auditoria/
│   │   ├── 📁 hub/
│   │   ├── 📁 lixeira/
│   │   └── ...
│   ├── 📁 core/            # Testes do núcleo
│   ├── 📁 infra/           # Testes de infraestrutura
│   └── 📁 security/        # Testes de segurança
├── 📁 integration/         # Testes de integração
└── 📁 manual/              # Testes manuais
```

---

## 3. Funcionalidades Principais

### 3.1 Módulos do Sistema

#### 🏢 Módulo de Clientes (`src/modules/clientes/`)

| Componente | Descrição |
|------------|-----------|
| `service.py` | Serviços de domínio (CRUD, validação de CNPJ, duplicatas) |
| `view.py` | Tela de listagem de clientes |
| `viewmodel.py` | Lógica de apresentação |
| `forms/` | Formulários de cadastro/edição |
| `components/` | Componentes reutilizáveis |

**Funcionalidades:**
- Cadastro completo com CNPJ, razão social, contatos
- Busca por nome, CNPJ ou telefone
- Filtro por status (Ativo, Inativo)
- Edição inline de campos
- Validação de CNPJ duplicado
- Integração com módulos de senhas e documentos

#### 🔑 Módulo de Senhas (`src/modules/passwords/`)

| Componente | Descrição |
|------------|-----------|
| `service.py` | Serviços (agrupamento, filtros, resumos) |
| `controller.py` | Controlador de ações |
| `view.py` | Tela de senhas |
| `helpers.py` | Funções auxiliares |

**Funcionalidades:**
- Armazenamento seguro com criptografia Fernet
- Organização por cliente e serviço (SIFAP, ANVISA, e-CAC)
- Copiar senha com um clique
- Filtros por serviço
- Histórico de alterações

#### 📋 Módulo de Auditoria (`src/modules/auditoria/`)

| Componente | Descrição |
|------------|-----------|
| `service.py` | Operações de dados e storage |
| `repository.py` | Acesso a dados |
| `storage.py` | Operações de armazenamento |
| `archives.py` | Manipulação de arquivos compactados |

**Funcionalidades:**
- Upload e organização de arquivos por cliente
- Suporte a múltiplos formatos (PDF, ZIP, RAR, 7z)
- Extração automática de arquivos compactados
- Integração com Supabase Storage

#### 🏠 Hub Central (`src/modules/hub/`)

| Componente | Descrição |
|------------|-----------|
| `controller.py` | Orquestração de polling e updates |
| `dashboard_service.py` | Serviço do dashboard |
| `notes_rendering.py` | Renderização de notas |
| `state.py` | Gerenciamento de estado |
| `views/` | Componentes visuais do Hub |

**Funcionalidades:**
- Dashboard com visão unificada
- Sistema de notas colaborativas em tempo real
- Acesso rápido aos módulos
- Indicadores de status

#### 🗑️ Módulo Lixeira (`src/modules/lixeira/`)

**Funcionalidades:**
- Recuperação de clientes excluídos
- Exclusão cascata de senhas associadas
- Exclusão permanente
- Histórico de exclusões

#### 💰 Fluxo de Caixa (`src/modules/cashflow/`)

**Funcionalidades:**
- Controle financeiro básico
- Registro de entradas e saídas
- Relatórios simples

#### 🤖 Integração ChatGPT (`src/modules/chatgpt/`)

**Funcionalidades:**
- Assistente IA para consultas rápidas
- Integração com API OpenAI
- Contexto de clientes

#### 📄 ANVISA Upload (`src/modules/anvisa/`)

**Funcionalidades:**
- Upload de PDFs por processo ANVISA
- Organização automática em pastas
- Slugificação de nomes de processos

### 3.2 Fluxo de Interação entre Módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (Entry Point)                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    src/app_gui.py (GUI Entry)                    │
│  - Configure environment                                         │
│  - Configure logging                                             │
│  - Show splash screen                                            │
│  - Ensure login                                                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              src/modules/main_window/views/main_window.py        │
│                        (App - Janela Principal)                  │
│  - TopBar + MenuBar                                              │
│  - NavigationController                                          │
│  - StatusFooter                                                  │
│  - StatusMonitor                                                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
    ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
    │   HubScreen │        │  Clientes   │        │   Senhas    │
    │  (Dashboard)│        │   Screen    │        │   Screen    │
    └─────────────┘        └─────────────┘        └─────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   infra/supabase_client.py                   │
    │              (Comunicação com Supabase Backend)              │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     Supabase Cloud                           │
    │         (PostgreSQL + Storage + Auth + Realtime)             │
    └─────────────────────────────────────────────────────────────┘
```

---

## 4. Dependências e Configurações

### 4.1 Dependências de Produção

#### Interface Gráfica
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `ttkbootstrap` | ≥1.14.2 | Framework moderno para Tkinter |
| `sv_ttk` | ≥2.6.1 | Tema Sun Valley para ttk |
| `tkinterweb` | ≥4.4.4 | Navegador web embarcado |

#### Backend & Database
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `supabase` | ≥2.22.0 | SDK Supabase completo |
| `postgrest` | ≥2.22.0 | Cliente PostgreSQL REST |
| `SQLAlchemy` | ≥2.0.36 | ORM Python |
| `alembic` | ≥1.13.2 | Migrações de banco |
| `psycopg` | ≥3.2.10 | Driver PostgreSQL async |
| `psycopg2-binary` | ≥2.9.10 | Driver PostgreSQL sync |

#### HTTP & Networking
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `httpx` | ≥0.28.1 | Cliente HTTP async/HTTP2 |
| `websockets` | ≥15.0.1 | Suporte a WebSockets |

#### Segurança
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `cryptography` | ≥46.0.3 | Primitivas criptográficas |
| `bcrypt` | ≥5.0.0 | Hashing de senhas |
| `PyJWT` | ≥2.10.1 | JSON Web Tokens |

#### IA / LLM
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `openai` | ≥1.40.0 | Cliente OpenAI (ChatGPT) |

#### Processamento de Arquivos
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `PyMuPDF` | ≥1.26.4 | Extração de PDFs |
| `pypdf` | ≥6.2.0 | Fallback para PDFs |
| `pytesseract` | ≥0.3.13 | OCR |
| `pillow` | ≥10.4.0 | Manipulação de imagens |
| `py7zr` | ≥1.0.0 | Suporte a 7z |

#### Validação
| Pacote | Versão | Descrição |
|--------|--------|-----------|
| `pydantic` | ≥2.12.4 | Validação de dados |
| `pydantic-settings` | ≥2.12.0 | Configurações tipadas |

### 4.2 Dependências de Desenvolvimento

| Categoria | Pacotes |
|-----------|---------|
| **Testes** | `pytest`, `pytest-cov`, `coverage` |
| **Linting** | `ruff`, `black`, `mypy`, `bandit`, `vulture` |
| **Segurança** | `pip_audit`, `cyclonedx-python-lib` |
| **Build** | `pyinstaller`, `build` |
| **Deps** | `pip-tools`, `pipdeptree`, `deptry` |

### 4.3 Configuração de Ambiente

#### Arquivo `.env` (criar na raiz)

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon

# Storage
RC_STORAGE_BUCKET_CLIENTS=rc-docs

# Criptografia (gerar com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
RC_CLIENT_SECRET_KEY=sua-chave-fernet-base64

# Configurações opcionais
RC_NO_LOCAL_FS=1          # Modo somente nuvem
RC_LOG_LEVEL=INFO         # Nível de log (DEBUG, INFO, WARNING, ERROR)
RC_TESTING=0              # Modo de teste
RC_HEALTHCHECK_DISABLE=0  # Desabilitar health check
```

#### Arquivo `config.yml`

```yaml
status_probe:
  url: https://httpbin.org/status/204
  timeout_seconds: 2.0
  interval_ms: 5000
```

### 4.4 Instalação

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd v1.4.79

# 2. Criar ambiente virtual
python -m venv .venv

# 3. Ativar ambiente (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 4. Instalar dependências de produção
pip install -r requirements.txt

# 5. (Opcional) Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# 6. Configurar .env com suas credenciais

# 7. Executar
python -m src.app_gui
```

---

## 5. Fluxo de Trabalho

### 5.1 Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `python -m src.app_gui` | Executar aplicação |
| `python main.py` | Entry point alternativo |
| `pytest` | Rodar testes (modo rápido) |
| `pytest -c pytest_cov.ini` | Rodar testes com cobertura |
| `ruff check .` | Verificar código com linter |
| `mypy src/` | Verificar tipos |
| `bandit -r src infra adapters` | Análise de segurança |

### 5.2 Testes por Módulo

```bash
# Clientes
pytest tests/unit/modules/clientes --no-cov -q

# Senhas
pytest tests/unit/modules/passwords --no-cov -q

# Auditoria
pytest tests/unit/modules/auditoria --no-cov -q

# Hub
pytest tests/unit/modules/hub --no-cov -q

# Lixeira
pytest tests/unit/modules/lixeira --no-cov -q
```

### 5.3 Build do Executável

```bash
# Build com PyInstaller
pyinstaller rcgestor.spec

# O executável será gerado em dist/
```

### 5.4 Ciclo de Vida da Aplicação

```
1. STARTUP
   ├── main.py → src.app_gui
   ├── Configure environment (.env)
   ├── Configure logging
   ├── Configure HiDPI
   └── Cleanup temporários antigos

2. SPLASH SCREEN
   └── show_splash()

3. AUTENTICAÇÃO
   ├── ensure_logged()
   ├── Validar credenciais (Supabase Auth)
   └── Carregar sessão

4. JANELA PRINCIPAL
   ├── App.__init__()
   ├── TopBar + MenuBar
   ├── NavigationController
   ├── StatusFooter
   └── StatusMonitor (health checks)

5. HUB SCREEN
   ├── Dashboard
   ├── Sistema de notas (polling/realtime)
   └── Navegação para módulos

6. OPERAÇÕES
   ├── CRUD de clientes
   ├── Gestão de senhas (criptografadas)
   ├── Upload de documentos
   └── Sincronização com Supabase

7. SHUTDOWN
   └── app.destroy()
```

### 5.5 Integrações Externas

| Serviço | Uso |
|---------|-----|
| **Supabase PostgreSQL** | Banco de dados principal |
| **Supabase Storage** | Armazenamento de arquivos |
| **Supabase Auth** | Autenticação de usuários |
| **Supabase Realtime** | Sincronização em tempo real |
| **OpenAI API** | Assistente ChatGPT |

---

## 6. Pontos Notáveis

### 6.1 Padrões de Design

| Padrão | Aplicação |
|--------|-----------|
| **MVC/MVVM** | Separação clara entre View, ViewModel e Service |
| **Repository** | Abstração de acesso a dados (`infra/repositories/`) |
| **Adapter** | Storage plugável (`adapters/storage/`) |
| **Singleton** | Cliente Supabase, cache de Fernet |
| **Observer** | StatusMonitor, polling de notas |
| **Factory** | Criação de clientes e conexões |

### 6.2 Segurança

#### Criptografia de Senhas
```python
# security/crypto.py
# - Fernet (symmetric encryption) para senhas locais
# - Chave derivada de RC_CLIENT_SECRET_KEY no .env
# - Cache singleton para performance
```

#### Autenticação
- Supabase Auth (JWT)
- Hash PBKDF2 para senhas locais
- bcrypt como alternativa

#### Boas Práticas
- Variáveis sensíveis em `.env` (não commitado)
- Análise com `bandit` para vulnerabilidades
- `pip_audit` para CVEs em dependências

### 6.3 Performance

| Otimização | Descrição |
|------------|-----------|
| **Lazy Loading** | Módulos carregados sob demanda |
| **Startup Oculto** | Janela principal criada hidden |
| **Health Check Agendado** | Não bloqueia startup |
| **Cache de Sessão** | Evita queries repetidas |
| **HTTP/2** | Via httpx para requisições mais rápidas |

### 6.4 Tratamento de Erros

```python
# Hierarquia de exceções customizadas
AuditoriaServiceError
├── AuditoriaOfflineError
ClienteServiceError
├── ClienteCNPJDuplicadoError
NotesTransientError
NotesAuthError
NotesTableMissingError
```

### 6.5 Logging

```python
# Configuração em src/core/logs/configure.py
# Níveis controlados por RC_LOG_LEVEL
# Formato: "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
```

### 6.6 Modo Cloud-Only

O sistema suporta operação sem filesystem local:
```python
# RC_NO_LOCAL_FS=1 no .env
# Todos os arquivos em Supabase Storage
```

---

## 7. Arquitetura do Sistema

### 7.1 Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│  src/ui/, src/modules/*/view.py, src/modules/*/views/            │
│  (Tkinter + ttkbootstrap)                                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                            │
│  src/modules/*/service.py, src/core/services/                    │
│  (Regras de negócio, orquestração)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                                │
│  data/domain_types.py, src/core/models.py                        │
│  (Entidades, tipos de dados)                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
│  infra/, adapters/storage/                                       │
│  (Supabase, Storage, HTTP, Crypto)                              │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Módulos Independentes

Cada módulo em `src/modules/` segue uma estrutura consistente:

```
module/
├── __init__.py        # Exports públicos
├── service.py         # Lógica de negócio
├── view.py            # Tela principal
├── viewmodel.py       # Lógica de apresentação (opcional)
├── controller.py      # Controlador (opcional)
├── views/             # Sub-views
├── components/        # Componentes reutilizáveis
├── forms/             # Formulários
└── helpers/           # Utilitários específicos
```

---

## 8. Testes e Qualidade

### 8.1 Estrutura de Testes

| Categoria | Localização | Descrição |
|-----------|-------------|-----------|
| **Unit** | `tests/unit/` | Testes isolados por módulo |
| **Integration** | `tests/integration/` | Testes de integração |
| **Manual** | `tests/manual/` | Scripts de teste manual |

### 8.2 Configuração do pytest

```ini
# pytest.ini
[pytest]
pythonpath = .
addopts = -q --tb=short --import-mode=importlib
testpaths = tests
```

### 8.3 Coverage

```bash
# Gerar relatório de cobertura
pytest -c pytest_cov.ini

# Relatórios em:
# - htmlcov/ (HTML interativo)
# - reports/coverage.json
```

### 8.4 Ferramentas de Qualidade

| Ferramenta | Propósito | Comando |
|------------|-----------|---------|
| **ruff** | Linter rápido | `ruff check .` |
| **mypy** | Type checking | `mypy src/` |
| **bandit** | Security linter | `bandit -r src` |
| **vulture** | Dead code finder | `vulture src/` |
| **deptry** | Dependency checker | `deptry .` |
| **pip_audit** | CVE scanner | `pip_audit` |

### 8.5 Markers Customizados

```python
# Definidos em tests/conftest.py
@pytest.mark.legacy_ui      # Testes de UI antiga
@pytest.mark.slow           # Testes demorados
@pytest.mark.integration    # Testes de integração
```

---

## 📝 Notas Finais

### Documentação Adicional

| Documento | Descrição |
|-----------|-----------|
| `docs/BUILD.md` | Instruções de build |
| `docs/TEST_ARCHITECTURE.md` | Arquitetura de testes |
| `docs/NAMING_GUIDELINES.md` | Convenções de nomenclatura |
| `docs/ANVISA_UPLOAD_FEATURE.md` | Feature de upload ANVISA |
| `CHANGELOG.md` | Histórico de mudanças |
| `CONTRIBUTING.md` | Guia de contribuição |

### Contato

Para dúvidas ou contribuições, consulte o arquivo `CONTRIBUTING.md`.

---

*Documento gerado automaticamente em 22/12/2025*
