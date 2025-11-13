# MODULE-MAP v1 — Mapa de Módulos e Arquitetura

**Data:** 2025-11-13  
**Versão:** 1.0  
**Status:** 📐 Documentação inicial (sem alterações de código)

---

## 1. Visão Geral da Arquitetura

Este projeto segue uma arquitetura em camadas, com separação de responsabilidades entre:

- **UI (Interface)**: Componentes visuais Tkinter/ttkbootstrap
- **Core (Núcleo)**: Lógica de negócio e coordenação
- **Domain (Domínio)**: Modelos de dados e tipos de domínio
- **Infra (Infraestrutura)**: Banco de dados, rede, Supabase, autenticação
- **Adapter (Adaptadores)**: Integrações externas (storage, APIs)
- **Typing (Stubs)**: Type hints para bibliotecas sem tipos nativos
- **Script (Utilitários)**: Ferramentas de desenvolvimento, testes, demos

### Estatísticas do Projeto

| Camada       | Módulos | Descrição                                    |
|--------------|---------|----------------------------------------------|
| UI           | 76      | Telas, widgets, diálogos, componentes visuais|
| Core         | 53      | Lógica de negócio, serviços, controladores   |
| Infra        | 34      | Banco, rede, Supabase, cache, autenticação   |
| Script       | 11      | Ferramentas de desenvolvimento e testes      |
| Adapter      | 5       | Integrações de storage e APIs externas       |
| Domain       | 4       | Modelos de dados, tipos de domínio           |
| Typing       | 0       | Stubs de tipos (atualmente vazio)            |
| Third Party  | 0       | Bibliotecas de terceiros (atualmente vazio)  |
| **TOTAL**    | **183** | Total de módulos Python analisados           |

---

## 2. Entrypoints do Aplicativo

### 2.1. Entrypoint Principal (Recomendado)

```bash
python -m src.app_gui
```

**Descrição:**
- Módulo `src/app_gui.py` é o entrypoint oficial para desenvolvimento
- Configura ambiente cloud-only: `RC_NO_LOCAL_FS=1`
- Carrega `.env` com suporte a PyInstaller onefile
- Configura logging via `src.core.logs.configure`
- Reexporta a classe `App` de `src.ui.main_window`
- Instala global exception hook
- Inicializa aplicação Tkinter

### 2.2. Entrypoint Alternativo (Compatibilidade)

```bash
python main.py
```

**Descrição:**
- Script raiz `main.py` é um **wrapper minimalista**
- Usa `runpy.run_module("src.app_gui", run_name="__main__")`
- Mantido para compatibilidade com workflows antigos
- **Recomendação:** Usar `python -m src.app_gui` diretamente

### 2.3. Build PyInstaller

**Spec file:** `rcgestor.spec`

Gera executável standalone para Windows com:
- Onefile mode (UPX compressão)
- Icon e metadados de versão
- Coleta de dados (assets, .env, migrations, third_party/7zip)
- Hooks para Supabase, Postgrest, httpx, pydantic

---

## 3. Estrutura de Camadas

### 3.1. UI (76 módulos)

**Responsabilidade:** Interface gráfica do usuário

| Subpasta               | Função                                       | Exemplos de Módulos                    |
|------------------------|----------------------------------------------|----------------------------------------|
| `src/ui/`              | Componentes visuais reutilizáveis            | `main_window`, `login`, `sidebar`      |
| `src/ui/widgets/`      | Widgets customizados                         | `autocomplete_entry`, `file_button`    |
| `src/ui/dialogs/`      | Diálogos modais                              | `file_select_dialog`                   |
| `src/features/*/view.py` | Telas de features específicas              | `auditoria/view`, `sifap/view`         |
| `src/modules/*/main_screen.py` | Telas principais de módulos      | `hub/main_screen`, `cliente/main_screen` |

**Principais Módulos UI:**
- `src/ui/main_window.py` — Janela principal (classe `App`)
- `src/ui/login.py` — Tela de login
- `src/ui/sidebar.py` — Barra lateral de navegação
- `src/ui/widgets/autocomplete_entry.py` — Campo com autocomplete
- `src/ui/widgets/file_button.py` — Botão de seleção de arquivo
- `src/features/auditoria/view.py` — Tela de auditoria
- `src/features/cashflow/dialogs.py` — Diálogos de fluxo de caixa
- `src/modules/hub/main_screen.py` — Hub principal
- `src/modules/cliente/main_screen.py` — Gestão de clientes

### 3.2. Core (53 módulos)

**Responsabilidade:** Lógica de negócio, coordenação, serviços

| Subpasta               | Função                                       | Exemplos de Módulos                    |
|------------------------|----------------------------------------------|----------------------------------------|
| `src/core/`            | Serviços centrais                            | `navigation_controller`, `models`      |
| `src/core/api/`        | Clientes de API interna                      | `api_clients`, `commands`              |
| `src/core/services/`   | Serviços de negócio                          | `upload_service`, `lixeira_service`    |
| `src/config/`          | Configurações e preferências                 | `preferences`, `flags`                 |
| `src/features/`        | Features de negócio                          | `cashflow/service`, `search/controller`|
| `src/modules/`         | Módulos de domínio                           | `farmacia/controller`, `sifap/logic`   |
| `helpers/`             | Utilitários de negócio                       | `data_fetcher`, `validation`           |

**Principais Módulos Core:**
- `src/core/navigation_controller.py` — Coordenação de navegação
- `src/core/models.py` — Modelos de dados centrais
- `src/core/api/api_clients.py` — Clientes HTTP internos
- `src/core/services/upload_service.py` — Serviço de upload
- `src/config/preferences.py` — Gerenciamento de preferências
- `src/features/search/controller.py` — Controlador de busca
- `src/modules/farmacia/controller.py` — Lógica Farmácia Popular
- `src/modules/sifap/logic.py` — Lógica SIFAP

### 3.3. Domain (4 módulos)

**Responsabilidade:** Modelos de domínio e tipos de dados

| Módulo                 | Função                                       |
|------------------------|----------------------------------------------|
| `data/domain_types.py` | Tipos de domínio (enums, dataclasses)        |
| `data/supabase_repo.py`| Repositório Supabase (camada de acesso)      |
| `data/auth_bootstrap.py`| Inicialização de autenticação               |
| `data/__init__.py`     | Exportações do pacote de dados               |

### 3.4. Infra (34 módulos)

**Responsabilidade:** Infraestrutura técnica (banco, rede, cache, auth)

| Subpasta               | Função                                       | Exemplos de Módulos                    |
|------------------------|----------------------------------------------|----------------------------------------|
| `infra/`               | Serviços de infraestrutura                   | `supabase_client`, `net_session`       |
| `infra/http/`          | Cliente HTTP e retry logic                   | `httpx_client`, `retry_strategy`       |
| `infra/supabase/`      | Integrações Supabase                         | `auth_service`, `client_factory`       |
| `security/`            | Criptografia e segurança                     | `crypto`                               |

**Principais Módulos Infra:**
- `infra/supabase_client.py` — Cliente Supabase singleton
- `infra/supabase_auth.py` — Autenticação Supabase
- `infra/net_session.py` — Sessão HTTP com retry
- `infra/net_status.py` — Health check e status de rede
- `infra/settings.py` — Configurações de ambiente
- `infra/http/httpx_client.py` — Cliente HTTP customizado
- `security/crypto.py` — Utilitários de criptografia

### 3.5. Adapter (5 módulos)

**Responsabilidade:** Adaptadores para sistemas externos

| Módulo                           | Função                                  |
|----------------------------------|-----------------------------------------|
| `adapters/storage/api.py`        | API de storage abstrata                 |
| `adapters/storage/port.py`       | Interface de storage (port)             |
| `adapters/storage/supabase_storage.py` | Implementação Supabase Storage  |

### 3.6. Script (11 módulos)

**Responsabilidade:** Ferramentas de desenvolvimento, testes, demos

| Subpasta               | Função                                       | Exemplos                               |
|------------------------|----------------------------------------------|----------------------------------------|
| `devtools/qa/`         | Análise de qualidade                         | `analyze_pyright_errors.py`            |
| `devtools/arch/`       | Ferramentas de arquitetura                   | `analyze_modules.py`                   |
| `scripts/`             | Demos e testes manuais                       | `test_upload_advanced.py`              |
| `tests/`               | Testes automatizados                         | `test_core.py`, `test_network.py`      |

### 3.7. Typing (0 módulos)

**Status:** Pasta `typings/` existe mas está vazia no scan

**Nota:** Stubs de tipo para `tkinter`, `supabase`, `postgrest` podem ser adicionados futuramente.

### 3.8. Third Party (0 módulos)

**Status:** Pasta `third_party/` contém binários (7zip) mas sem módulos Python

---

## 4. Módulos Principais por Feature

### 4.1. SIFAP (Sistema de Informatização das Farmácias do Atendimento Programado)

**Camada:** Core  
**Módulos:**
- `src/modules/sifap/logic.py` — Lógica de negócio SIFAP
- `src/modules/sifap/view.py` — Interface SIFAP (UI)

### 4.2. Farmácia Popular

**Camada:** Core  
**Módulos:**
- `src/modules/farmacia/controller.py` — Controlador Farmácia Popular
- `src/modules/farmacia/view.py` — Interface Farmácia Popular (UI)

### 4.3. Gestão de Clientes

**Camada:** Core + UI  
**Módulos:**
- `src/modules/cliente/main_screen.py` — Tela principal de clientes
- `src/core/models.py` — Modelo `Cliente`

### 4.4. Auditoria

**Camada:** Core + UI  
**Módulos:**
- `src/features/auditoria/view.py` — Interface de auditoria
- `src/features/auditoria/controller.py` — Lógica de auditoria

### 4.5. Fluxo de Caixa (Cashflow)

**Camada:** Core + UI  
**Módulos:**
- `src/features/cashflow/dialogs.py` — Diálogos de cashflow
- `src/features/cashflow/service.py` — Serviço de cashflow

### 4.6. Busca (Search)

**Camada:** Core + UI  
**Módulos:**
- `src/features/search/controller.py` — Controlador de busca
- `src/features/search/view.py` — Interface de busca

### 4.7. Upload de Arquivos

**Camada:** Core + Adapter  
**Módulos:**
- `src/core/services/upload_service.py` — Serviço de upload
- `adapters/storage/supabase_storage.py` — Adapter Supabase Storage

### 4.8. Lixeira

**Camada:** Core + UI  
**Módulos:**
- `src/core/services/lixeira_service.py` — Serviço de lixeira
- `src/modules/lixeira/lixeira.py` — Interface de lixeira

---

## 5. Fluxo de Dados Típico

```
┌─────────────────────────────────────────────────────────────┐
│ UI Layer (src/ui, src/features/*/view.py)                   │
│ - Captura eventos do usuário                                 │
│ - Renderiza dados na interface Tkinter                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Layer (src/core, src/modules, src/features)            │
│ - Coordena lógica de negócio                                 │
│ - Valida regras de domínio                                   │
│ - Orquestra chamadas para Infra/Adapters                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Domain Layer (data/)                                         │
│ - Define modelos e tipos de dados                            │
│ - Repositórios de acesso a dados                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Infra Layer (infra/, security/)                              │
│ - Supabase client (auth, database, storage)                  │
│ - HTTP sessions com retry                                    │
│ - Health checks e network status                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Adapter Layer (adapters/)                                    │
│ - Implementa interfaces de storage                           │
│ - Traduz chamadas para APIs externas                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Próximos Passos de Modularização

Este documento é o **passo 1** do ModularPack. Próximos passos planejados:

1. **ModularPack-02:** Separar features em módulos isolados (SIFAP, Farmácia, Auditoria)
2. **ModularPack-03:** Refatorar dependências circulares entre camadas
3. **ModularPack-04:** Implementar dependency injection para desacoplar UI de Infra
4. **ModularPack-05:** Extrair interfaces (ports) para adapters
5. **ModularPack-06:** Testes de integração por camada

---

## 7. Convenções de Nomenclatura

| Camada  | Padrão de Arquivo        | Exemplo                         |
|---------|--------------------------|---------------------------------|
| UI      | `*_view.py`, `*_dialog.py`, `*_window.py` | `auditoria/view.py` |
| Core    | `*_service.py`, `*_controller.py`, `*_logic.py` | `upload_service.py` |
| Domain  | `*_types.py`, `*_repo.py`, `models.py` | `domain_types.py` |
| Infra   | `*_client.py`, `*_auth.py`, `settings.py` | `supabase_client.py` |
| Adapter | `*_storage.py`, `*_api.py`, `port.py` | `supabase_storage.py` |

---

## 8. Dependências Entre Camadas (Regra Geral)

**Direção permitida de dependências:**

```
UI → Core → Domain → Infra → Adapter
```

**Regras:**
- **UI** pode importar **Core** e **Domain**
- **Core** pode importar **Domain** e **Infra**
- **Domain** pode importar **Infra** (repositórios)
- **Infra** não deve importar **Core** ou **UI**
- **Adapter** não deve importar **Core**, **UI** ou **Domain**

**Nota:** Algumas violações existem atualmente e serão corrigidas em ModularPacks futuros.

---

## 9. Ferramentas de Análise

### 9.1. Análise de Módulos

```bash
python devtools/arch/analyze_modules.py
```

**Saída:** `devtools/arch/module_map.json`

**Conteúdo:**
- Classificação de todos os 183 módulos Python por camada
- Lista de imports principais de cada módulo
- Estatísticas por camada

### 9.2. Validação de Qualidade

```bash
# Linters
ruff check .
flake8 .

# Type checker
pyright

# Testes
pytest
```

---

## 10. Referências

- **Código-fonte:** `src/`, `adapters/`, `infra/`, `data/`
- **Documentação QA:** `docs/qa-history/QA-DELTA-*.md`
- **Scripts de análise:** `devtools/arch/`, `devtools/qa/`
- **Configurações:** `pyproject.toml`, `pyrightconfig.json`, `ruff.toml`

---

**Fim do MODULE-MAP v1**
