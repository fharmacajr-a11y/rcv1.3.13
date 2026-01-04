# 04 - Lista de Arquivos Grandes

> **Versão de referência:** v1.5.35  
> **Data:** 2025-01-02  
> **Última atualização:** 2025-01-02 (Recálculo via Python)  
> **Critério:** Arquivos .py com mais de 500 linhas

Este documento lista os maiores arquivos do projeto para auxiliar em futuras refatorações de quebra de código.

---

## 📊 Top 30 Arquivos por Número de Linhas

| # | Linhas | Arquivo | Sugestão de Quebra |
|---|--------|---------|-------------------|
| 1 | **1056** | `src/modules/clientes/views/main_screen_helpers.py` | Helpers por domínio (tree/form/data) |
| 2 | **1018** | `src/modules/pdf_preview/views/main_window.py` | UI vs Handlers vs Logic |
| 3 | **963** | `src/modules/hub/views/dashboard_center.py` | Widgets vs Data Loading vs Layout |
| 4 | **934** | `src/modules/anvisa/services/anvisa_service.py` | Service vs Repository vs Validators |
| 5 | **868** | `src/modules/anvisa/views/_anvisa_handlers_mixin.py` | Handlers por ação |
| 6 | **857** | `src/modules/hub/views/hub_screen.py` | Layout vs Logic vs Events |
| 7 | **846** | `src/modules/clientes/views/main_screen_controller.py` | Controller por feature |
| 8 | **834** | `src/modules/main_window/views/main_window_actions.py` | Actions por categoria |
| 9 | **812** | `src/modules/anvisa/views/anvisa_screen.py` | Screen vs Dialogs vs Widgets |
| 10 | **790** | `src/modules/hub/views/hub_dialogs.py` | Um dialog por arquivo |
| 11 | **745** | `infra/repositories/notifications_repository.py` | Repository puro vs Cache |
| 12 | **719** | `src/modules/hub/dashboard/service.py` | Service vs DTOs vs Helpers |
| 13 | **703** | `src/modules/main_window/views/main_window.py` | Window vs Menu vs Status |
| 14 | **681** | `data/supabase_repo.py` | Repository por entidade |
| 15 | **662** | `src/modules/uploads/views/browser.py` | Browser UI vs File Logic |
| 16 | **650** | `src/modules/hub/helpers/notes.py` | CRUD separado de UI |
| 17 | **643** | `src/modules/hub/recent_activity_store.py` | Store vs Serialization |
| 18 | **637** | `src/modules/uploads/uploader_supabase.py` | Uploader vs Progress vs Retry |
| 19 | **632** | `src/modules/hub/hub_screen_controller.py` | Controller vs Presenter |
| 20 | **618** | `src/modules/clientes/views/main_screen_dataflow.py` | Data vs Events |
| 21 | **600** | `src/modules/clientes/viewmodel.py` | ViewModel por concern |
| 22 | **588** | `src/core/services/notes_service.py` | Service vs Validators |
| 23 | **581** | `src/modules/hub/views/hub_screen_view.py` | View vs Subviews |
| 24 | **580** | `src/modules/passwords/views/passwords_screen.py` | Screen vs Form vs List |
| 25 | **558** | `src/modules/hub/services/hub_component_factory.py` | Factory vs Builders |
| 26 | **558** | `src/modules/hub/viewmodels/notes_vm.py` | ViewModel vs State |
| 27 | **550** | `src/core/notifications_service.py` | Service vs Scheduler |
| 28 | **523** | `src/modules/main_window/views/state_helpers.py` | Helpers por tipo de estado |
| 29 | **517** | `src/modules/lixeira/views/lixeira_helpers.py` | Helpers por funcionalidade |
| 30 | **505** | `src/ui/components/notifications/notifications_popup.py` | Popup vs Items |

---

## 📈 Estatísticas Atualizadas

| Métrica | Valor Anterior | Valor Atual |
|---------|----------------|-------------|
| Total de arquivos > 500 linhas | 14 | **30** |
| Maior arquivo | 891 linhas | **1056 linhas** |
| Média dos top 10 | ~715 linhas | **798 linhas** |
| Arquivos analisados | ~200 | **497** |

---

## 🔍 Análise Detalhada dos Maiores

### 1. `clientes/views/main_screen_helpers.py` (1056 linhas) ⚠️ CRÍTICO

**Problema:** Arquivo monolítico com helpers muito diversos.

**Sugestão de quebra:**
```
clientes/views/helpers/
├── __init__.py             # Reexporta helpers públicos
├── tree_helpers.py         # Manipulação de TreeView
├── form_helpers.py         # Validação de formulários
├── data_helpers.py         # Transformação de dados
└── ui_helpers.py           # Helpers de interface
```

---

### 2. `pdf_preview/views/main_window.py` (1018 linhas)

**Problema:** Mistura de UI, handlers e lógica de negócio.

**Sugestão de quebra:**
```
pdf_preview/views/
├── main_window.py          # Apenas definição de UI/layout
├── main_window_handlers.py # Event handlers
├── main_window_actions.py  # Ações de negócio
└── pdf_toolbar.py          # Barra de ferramentas
```

---

### 3. `hub/views/dashboard_center.py` (963 linhas)

**Problema:** Dashboard monolítico com muitos widgets.

**Sugestão de quebra:**
```
hub/views/
├── dashboard_center.py     # Container principal
├── widgets/
│   ├── activity_widget.py
│   ├── stats_widget.py
│   └── quick_actions_widget.py
```

---

### 4. `anvisa/services/anvisa_service.py` (934 linhas)

**Problema:** Service com muitas responsabilidades.

**Sugestão de quebra:**
```
anvisa/services/
├── anvisa_service.py       # Orquestração
├── anvisa_validator.py     # Validações
├── anvisa_repository.py    # Acesso a dados
└── anvisa_formatter.py     # Formatação de dados
```

---

### 5. `infra/repositories/notifications_repository.py` (745 linhas)

**Problema:** Repository com lógica de cache misturada.

**Sugestão de quebra:**
```
infra/repositories/
├── notifications_repository.py  # CRUD puro
├── notifications_cache.py       # Lógica de cache
└── notifications_dto.py         # DTOs/Models
```

---

### 6. `data/supabase_repo.py` (681 linhas)

**Problema:** Repository monolítico para todas as entidades.

**Sugestão de quebra:**
```
data/
├── supabase_repo.py            # Base/comum
├── repos/
│   ├── clients_repo.py
│   ├── passwords_repo.py
│   └── notes_repo.py
```

---

## ⚠️ Arquivos Fora de `src/` que Precisam de Atenção

| Arquivo | Linhas | Localização | Ação na Refatoração |
|---------|--------|-------------|---------------------|
| `notifications_repository.py` | 745 | `infra/repositories/` | Mover para `src/infra/` na Fase 1 |
| `supabase_repo.py` | 681 | `data/` | Mover para `src/data/` na Fase 2 |

Estes arquivos serão movidos para `src/` e são candidatos prioritários a refatoração adicional após a consolidação.

---

## 🎯 Priorização para Refatoração Futura

### Alta Prioridade (>800 linhas)
1. `main_screen_helpers.py` - 1056 linhas
2. `pdf_preview/main_window.py` - 1018 linhas
3. `dashboard_center.py` - 963 linhas
4. `anvisa_service.py` - 934 linhas
5. `_anvisa_handlers_mixin.py` - 868 linhas
6. `hub_screen.py` - 857 linhas
7. `main_screen_controller.py` - 846 linhas
8. `main_window_actions.py` - 834 linhas
9. `anvisa_screen.py` - 812 linhas

### Média Prioridade (600-800 linhas)
- 11 arquivos nesta faixa

### Baixa Prioridade (500-600 linhas)
- 10 arquivos nesta faixa

---

## 📋 Método de Coleta

```python
import os

DIRS = ['src', 'infra', 'data', 'adapters', 'security']
IGNORE = {'.venv', '__pycache__', 'dist', 'build', '.git', 'htmlcov', 'third_party'}

files_data = []

for dir_name in DIRS:
    if os.path.isdir(dir_name):
        for root, dirs, files in os.walk(dir_name):
            dirs[:] = [d for d in dirs if d not in IGNORE]
            for f in files:
                if f.endswith('.py'):
                    fpath = os.path.join(root, f)
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                        lines = len(fp.read().splitlines())
                    files_data.append((fpath, lines))

files_data.sort(key=lambda x: -x[1])
```

**Executado em:** 2025-01-02  
**Ambiente:** Python 3.11, Windows 11

---

## 🎯 Recomendação

**Para esta fase de refatoração:**
- NÃO quebrar arquivos agora
- Apenas mover as pastas (`infra/`, `data/`, etc.) para dentro de `src/`

**Para fases futuras:**
- Priorizar quebra dos arquivos > 800 linhas
- Começar pelos módulos com mais bugs/mudanças frequentes
- Aplicar padrões consistentes (um handler por arquivo, um widget por arquivo)
