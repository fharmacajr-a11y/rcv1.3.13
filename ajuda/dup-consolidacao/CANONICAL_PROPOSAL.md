# Proposta de Módulos Canônicos
**Data:** 2025-10-18 09:56:34
**Grupos analisados:** 4
---

## 📦 Grupo: `api`

### ✅ Canônico Sugerido

**Arquivo:** `application\api.py`

**Justificativa:** camada prioritária (100) + mais referenciado (12 importers) + 462 linhas

**Score:** 1646.20

### Arquivos no Grupo

| Arquivo | Camada | In-Degree | Linhas | Funções | Classes |
|---------|--------|-----------|--------|---------|----------|
| **✅** `application\api.py` | application | 12 | 462 | 14 | 0 |
|  `adapters\storage\api.py` | adapters | 10 | 101 | 10 | 0 |

### Similaridades

| Par | AST Sim % | Sig Overlap % |
|-----|-----------|---------------|
| `application\api.py` ↔ `adapters\storage\api.py` | 2.4 | 0.0 |

### 🎯 Consolidação

**Viável:** ⚠️ NÃO

**Razões:**
- Similaridade de nome insuficiente (0.0 < 85)
- Similaridade AST baixa (2.4% < 60%)
- Overlap de assinaturas baixo (0.0% < 60%)
- ❌ Critérios não atendidos para consolidação automática
- Custo de reescrita aceitável (22 importers)

**Riscos:**
- ⚠️ Camadas diferentes (application vs adapters) - podem ter propósitos distintos

---

## 📦 Grupo: `__init__`

### ✅ Canônico Sugerido

**Arquivo:** `core\db_manager\__init__.py`

**Justificativa:** camada prioritária (90) + mais referenciado (30 importers) + 31 linhas

**Score:** 2403.10

### Arquivos no Grupo

| Arquivo | Camada | In-Degree | Linhas | Funções | Classes |
|---------|--------|-----------|--------|---------|----------|
|  `application\__init__.py` | application | 12 | 1 | 0 | 0 |
|  `gui\__init__.py` | gui | 5 | 10 | 0 | 0 |
|  `ui\__init__.py` | ui | 21 | 5 | 0 | 0 |
|  `ui\dialogs\__init__.py` | ui | 21 | 1 | 0 | 0 |
|  `ui\forms\__init__.py` | ui | 21 | 3 | 0 | 0 |
|  `ui\lixeira\__init__.py` | ui | 21 | 8 | 1 | 0 |
|  `ui\login\__init__.py` | ui | 21 | 3 | 0 | 0 |
|  `ui\widgets\__init__.py` | ui | 21 | 9 | 0 | 0 |
|  `core\__init__.py` | core | 30 | 14 | 1 | 0 |
|  `core\auth\__init__.py` | core | 30 | 9 | 0 | 0 |
| **✅** `core\db_manager\__init__.py` | core | 30 | 31 | 0 | 0 |
|  `core\logs\__init__.py` | core | 30 | 1 | 0 | 0 |
|  `core\search\__init__.py` | core | 30 | 3 | 0 | 0 |
|  `core\session\__init__.py` | core | 30 | 3 | 0 | 0 |
|  `infra\__init__.py` | infra | 18 | 2 | 0 | 0 |
|  `adapters\__init__.py` | adapters | 10 | 1 | 0 | 0 |
|  `adapters\storage\__init__.py` | adapters | 10 | 1 | 0 | 0 |
|  `shared\__init__.py` | shared | 6 | 1 | 0 | 0 |
|  `shared\config\__init__.py` | shared | 6 | 1 | 0 | 0 |
|  `shared\logging\__init__.py` | shared | 6 | 1 | 0 | 0 |
|  `utils\__init__.py` | utils | 34 | 0 | 0 | 0 |
|  `utils\file_utils\__init__.py` | utils | 34 | 3 | 0 | 0 |
|  `utils\helpers\__init__.py` | utils | 34 | 6 | 0 | 0 |
|  `detectors\__init__.py` | detectors | 0 | 2 | 0 | 0 |
|  `config\__init__.py` | config | 11 | 2 | 0 | 0 |

### Similaridades

| Par | AST Sim % | Sig Overlap % |
|-----|-----------|---------------|
| `application\__init__.py` ↔ `gui\__init__.py` | 73.88 | 0 |
| `application\__init__.py` ↔ `ui\__init__.py` | 71.48 | 0 |
| `application\__init__.py` ↔ `ui\dialogs\__init__.py` | 14.95 | 0 |
| `application\__init__.py` ↔ `ui\forms\__init__.py` | 39.72 | 0 |
| `application\__init__.py` ↔ `ui\lixeira\__init__.py` | 29.4 | 0.0 |
| `application\__init__.py` ↔ `ui\login\__init__.py` | 39.72 | 0 |
| `application\__init__.py` ↔ `ui\widgets\__init__.py` | 46.94 | 0 |
| `application\__init__.py` ↔ `core\__init__.py` | 32.11 | 0.0 |
| `application\__init__.py` ↔ `core\auth\__init__.py` | 69.96 | 0 |
| `application\__init__.py` ↔ `core\db_manager\__init__.py` | 39.68 | 0 |
| `application\__init__.py` ↔ `core\logs\__init__.py` | 14.95 | 0 |
| `application\__init__.py` ↔ `core\search\__init__.py` | 39.72 | 0 |
| `application\__init__.py` ↔ `core\session\__init__.py` | 39.72 | 0 |
| `application\__init__.py` ↔ `infra\__init__.py` | 39.06 | 0 |
| `application\__init__.py` ↔ `adapters\__init__.py` | 82.14 | 0 |
| `application\__init__.py` ↔ `adapters\storage\__init__.py` | 100.0 | 0 |
| `application\__init__.py` ↔ `shared\__init__.py` | 91.8 | 0 |
| `application\__init__.py` ↔ `shared\config\__init__.py` | 82.14 | 0 |
| `application\__init__.py` ↔ `shared\logging\__init__.py` | 91.8 | 0 |
| `application\__init__.py` ↔ `utils\__init__.py` | 14.95 | 0 |
| `application\__init__.py` ↔ `utils\file_utils\__init__.py` | 39.72 | 0 |
| `application\__init__.py` ↔ `utils\helpers\__init__.py` | 61.76 | 0 |
| `application\__init__.py` ↔ `detectors\__init__.py` | 39.06 | 0 |
| `application\__init__.py` ↔ `config\__init__.py` | 39.06 | 0 |
| `gui\__init__.py` ↔ `ui\__init__.py` | 88.76 | 0 |
| `gui\__init__.py` ↔ `ui\dialogs\__init__.py` | 9.04 | 0 |
| `gui\__init__.py` ↔ `ui\forms\__init__.py` | 38.86 | 0 |
| `gui\__init__.py` ↔ `ui\lixeira\__init__.py` | 27.49 | 0.0 |
| `gui\__init__.py` ↔ `ui\login\__init__.py` | 38.86 | 0 |
| `gui\__init__.py` ↔ `ui\widgets\__init__.py` | 56.59 | 0 |
| `gui\__init__.py` ↔ `core\__init__.py` | 25.69 | 0.0 |
| `gui\__init__.py` ↔ `core\auth\__init__.py` | 83.29 | 0 |
| `gui\__init__.py` ↔ `core\db_manager\__init__.py` | 51.67 | 0 |
| `gui\__init__.py` ↔ `core\logs\__init__.py` | 9.04 | 0 |
| `gui\__init__.py` ↔ `core\search\__init__.py` | 38.86 | 0 |
| `gui\__init__.py` ↔ `core\session\__init__.py` | 38.86 | 0 |
| `gui\__init__.py` ↔ `infra\__init__.py` | 29.29 | 0 |
| `gui\__init__.py` ↔ `adapters\__init__.py` | 57.98 | 0 |
| `gui\__init__.py` ↔ `adapters\storage\__init__.py` | 73.88 | 0 |
| `gui\__init__.py` ↔ `shared\__init__.py` | 66.4 | 0 |
| `gui\__init__.py` ↔ `shared\config\__init__.py` | 57.98 | 0 |
| `gui\__init__.py` ↔ `shared\logging\__init__.py` | 66.4 | 0 |
| `gui\__init__.py` ↔ `utils\__init__.py` | 9.04 | 0 |
| `gui\__init__.py` ↔ `utils\file_utils\__init__.py` | 38.86 | 0 |
| `gui\__init__.py` ↔ `utils\helpers\__init__.py` | 81.29 | 0 |
| `gui\__init__.py` ↔ `detectors\__init__.py` | 29.29 | 0 |
| `gui\__init__.py` ↔ `config\__init__.py` | 29.29 | 0 |
| `ui\__init__.py` ↔ `ui\dialogs\__init__.py` | 8.6 | 0 |
| `ui\__init__.py` ↔ `ui\forms\__init__.py` | 37.27 | 0 |
| `ui\__init__.py` ↔ `ui\lixeira\__init__.py` | 26.96 | 0.0 |
| `ui\__init__.py` ↔ `ui\login\__init__.py` | 37.27 | 0 |
| `ui\__init__.py` ↔ `ui\widgets\__init__.py` | 55.23 | 0 |
| `ui\__init__.py` ↔ `core\__init__.py` | 25.24 | 0.0 |
| `ui\__init__.py` ↔ `core\auth\__init__.py` | 86.19 | 0 |
| `ui\__init__.py` ↔ `core\db_manager\__init__.py` | 53.98 | 0 |
| `ui\__init__.py` ↔ `core\logs\__init__.py` | 8.6 | 0 |
| `ui\__init__.py` ↔ `core\search\__init__.py` | 37.27 | 0 |
| `ui\__init__.py` ↔ `core\session\__init__.py` | 37.27 | 0 |
| `ui\__init__.py` ↔ `infra\__init__.py` | 28.02 | 0 |
| `ui\__init__.py` ↔ `adapters\__init__.py` | 55.87 | 0 |
| `ui\__init__.py` ↔ `adapters\storage\__init__.py` | 71.48 | 0 |
| `ui\__init__.py` ↔ `shared\__init__.py` | 64.12 | 0 |
| `ui\__init__.py` ↔ `shared\config\__init__.py` | 55.87 | 0 |
| `ui\__init__.py` ↔ `shared\logging\__init__.py` | 64.12 | 0 |
| `ui\__init__.py` ↔ `utils\__init__.py` | 8.6 | 0 |
| `ui\__init__.py` ↔ `utils\file_utils\__init__.py` | 37.27 | 0 |
| `ui\__init__.py` ↔ `utils\helpers\__init__.py` | 89.46 | 0 |
| `ui\__init__.py` ↔ `detectors\__init__.py` | 28.02 | 0 |
| `ui\__init__.py` ↔ `config\__init__.py` | 28.02 | 0 |
| `ui\dialogs\__init__.py` ↔ `ui\forms\__init__.py` | 32.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `ui\lixeira\__init__.py` | 4.83 | 0.0 |
| `ui\dialogs\__init__.py` ↔ `ui\login\__init__.py` | 32.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `ui\widgets\__init__.py` | 7.88 | 0 |
| `ui\dialogs\__init__.py` ↔ `core\__init__.py` | 4.06 | 0.0 |
| `ui\dialogs\__init__.py` ↔ `core\auth\__init__.py` | 8.33 | 0 |
| `ui\dialogs\__init__.py` ↔ `core\db_manager\__init__.py` | 3.43 | 0 |
| `ui\dialogs\__init__.py` ↔ `core\logs\__init__.py` | 100.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `core\search\__init__.py` | 32.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `core\session\__init__.py` | 32.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `infra\__init__.py` | 43.24 | 0 |
| `ui\dialogs\__init__.py` ↔ `adapters\__init__.py` | 20.78 | 0 |
| `ui\dialogs\__init__.py` ↔ `adapters\storage\__init__.py` | 14.95 | 0 |
| `ui\dialogs\__init__.py` ↔ `shared\__init__.py` | 17.39 | 0 |
| `ui\dialogs\__init__.py` ↔ `shared\config\__init__.py` | 20.78 | 0 |
| `ui\dialogs\__init__.py` ↔ `shared\logging\__init__.py` | 17.39 | 0 |
| `ui\dialogs\__init__.py` ↔ `utils\__init__.py` | 100.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `utils\file_utils\__init__.py` | 32.0 | 0 |
| `ui\dialogs\__init__.py` ↔ `utils\helpers\__init__.py` | 8.84 | 0 |
| `ui\dialogs\__init__.py` ↔ `detectors\__init__.py` | 43.24 | 0 |
| `ui\dialogs\__init__.py` ↔ `config\__init__.py` | 43.24 | 0 |
| `ui\forms\__init__.py` ↔ `ui\lixeira\__init__.py` | 24.69 | 0.0 |
| `ui\forms\__init__.py` ↔ `ui\login\__init__.py` | 100.0 | 0 |
| `ui\forms\__init__.py` ↔ `ui\widgets\__init__.py` | 34.6 | 0 |
| `ui\forms\__init__.py` ↔ `core\__init__.py` | 21.11 | 0.0 |
| `ui\forms\__init__.py` ↔ `core\auth\__init__.py` | 37.17 | 0 |
| `ui\forms\__init__.py` ↔ `core\db_manager\__init__.py` | 18.55 | 0 |
| `ui\forms\__init__.py` ↔ `core\logs\__init__.py` | 32.0 | 0 |
| `ui\forms\__init__.py` ↔ `core\search\__init__.py` | 100.0 | 0 |
| `ui\forms\__init__.py` ↔ `core\session\__init__.py` | 100.0 | 0 |
| `ui\forms\__init__.py` ↔ `infra\__init__.py` | 56.34 | 0 |
| `ui\forms\__init__.py` ↔ `adapters\__init__.py` | 50.45 | 0 |
| `ui\forms\__init__.py` ↔ `adapters\storage\__init__.py` | 42.55 | 0 |
| `ui\forms\__init__.py` ↔ `shared\__init__.py` | 46.03 | 0 |
| `ui\forms\__init__.py` ↔ `shared\config\__init__.py` | 50.45 | 0 |
| `ui\forms\__init__.py` ↔ `shared\logging\__init__.py` | 46.03 | 0 |
| `ui\forms\__init__.py` ↔ `utils\__init__.py` | 32.0 | 0 |
| `ui\forms\__init__.py` ↔ `utils\file_utils\__init__.py` | 100.0 | 0 |
| `ui\forms\__init__.py` ↔ `utils\helpers\__init__.py` | 38.14 | 0 |
| `ui\forms\__init__.py` ↔ `detectors\__init__.py` | 56.34 | 0 |
| `ui\forms\__init__.py` ↔ `config\__init__.py` | 56.34 | 0 |
| `ui\lixeira\__init__.py` ↔ `ui\login\__init__.py` | 25.93 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `ui\widgets\__init__.py` | 42.77 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\__init__.py` | 70.76 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\auth\__init__.py` | 46.35 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\db_manager\__init__.py` | 18.18 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\logs\__init__.py` | 5.52 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\search\__init__.py` | 25.93 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `core\session\__init__.py` | 25.93 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `infra\__init__.py` | 16.08 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `adapters\__init__.py` | 39.32 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `adapters\storage\__init__.py` | 36.22 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `shared\__init__.py` | 37.7 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `shared\config\__init__.py` | 39.32 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `shared\logging\__init__.py` | 37.7 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `utils\__init__.py` | 5.52 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `utils\file_utils\__init__.py` | 25.93 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `utils\helpers\__init__.py` | 52.75 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `detectors\__init__.py` | 16.08 | 0.0 |
| `ui\lixeira\__init__.py` ↔ `config\__init__.py` | 16.08 | 0.0 |
| `ui\login\__init__.py` ↔ `ui\widgets\__init__.py` | 34.6 | 0 |
| `ui\login\__init__.py` ↔ `core\__init__.py` | 21.11 | 0.0 |
| `ui\login\__init__.py` ↔ `core\auth\__init__.py` | 37.17 | 0 |
| `ui\login\__init__.py` ↔ `core\db_manager\__init__.py` | 18.55 | 0 |
| `ui\login\__init__.py` ↔ `core\logs\__init__.py` | 32.0 | 0 |
| `ui\login\__init__.py` ↔ `core\search\__init__.py` | 100.0 | 0 |
| `ui\login\__init__.py` ↔ `core\session\__init__.py` | 100.0 | 0 |
| `ui\login\__init__.py` ↔ `infra\__init__.py` | 56.34 | 0 |
| `ui\login\__init__.py` ↔ `adapters\__init__.py` | 50.45 | 0 |
| `ui\login\__init__.py` ↔ `adapters\storage\__init__.py` | 42.55 | 0 |
| `ui\login\__init__.py` ↔ `shared\__init__.py` | 46.03 | 0 |
| `ui\login\__init__.py` ↔ `shared\config\__init__.py` | 50.45 | 0 |
| `ui\login\__init__.py` ↔ `shared\logging\__init__.py` | 46.03 | 0 |
| `ui\login\__init__.py` ↔ `utils\__init__.py` | 32.0 | 0 |
| `ui\login\__init__.py` ↔ `utils\file_utils\__init__.py` | 100.0 | 0 |
| `ui\login\__init__.py` ↔ `utils\helpers\__init__.py` | 38.14 | 0 |
| `ui\login\__init__.py` ↔ `detectors\__init__.py` | 56.34 | 0 |
| `ui\login\__init__.py` ↔ `config\__init__.py` | 56.34 | 0 |
| `ui\widgets\__init__.py` ↔ `core\__init__.py` | 49.62 | 0.0 |
| `ui\widgets\__init__.py` ↔ `core\auth\__init__.py` | 53.83 | 0 |
| `ui\widgets\__init__.py` ↔ `core\db_manager\__init__.py` | 33.95 | 0 |
| `ui\widgets\__init__.py` ↔ `core\logs\__init__.py` | 7.88 | 0 |
| `ui\widgets\__init__.py` ↔ `core\search\__init__.py` | 34.6 | 0 |
| `ui\widgets\__init__.py` ↔ `core\session\__init__.py` | 34.6 | 0 |
| `ui\widgets\__init__.py` ↔ `infra\__init__.py` | 24.11 | 0 |
| `ui\widgets\__init__.py` ↔ `adapters\__init__.py` | 52.27 | 0 |
| `ui\widgets\__init__.py` ↔ `adapters\storage\__init__.py` | 46.94 | 0 |
| `ui\widgets\__init__.py` ↔ `shared\__init__.py` | 49.46 | 0 |
| `ui\widgets\__init__.py` ↔ `shared\config\__init__.py` | 52.27 | 0 |
| `ui\widgets\__init__.py` ↔ `shared\logging\__init__.py` | 49.46 | 0 |
| `ui\widgets\__init__.py` ↔ `utils\__init__.py` | 7.88 | 0 |
| `ui\widgets\__init__.py` ↔ `utils\file_utils\__init__.py` | 34.6 | 0 |
| `ui\widgets\__init__.py` ↔ `utils\helpers\__init__.py` | 55.98 | 0 |
| `ui\widgets\__init__.py` ↔ `detectors\__init__.py` | 24.11 | 0 |
| `ui\widgets\__init__.py` ↔ `config\__init__.py` | 24.11 | 0 |
| `core\__init__.py` ↔ `core\auth\__init__.py` | 51.06 | 0.0 |
| `core\__init__.py` ↔ `core\db_manager\__init__.py` | 27.41 | 0.0 |
| `core\__init__.py` ↔ `core\logs\__init__.py` | 4.64 | 0.0 |
| `core\__init__.py` ↔ `core\search\__init__.py` | 22.16 | 0.0 |
| `core\__init__.py` ↔ `core\session\__init__.py` | 22.16 | 0.0 |
| `core\__init__.py` ↔ `infra\__init__.py` | 15.85 | 0.0 |
| `core\__init__.py` ↔ `adapters\__init__.py` | 33.99 | 0.0 |
| `core\__init__.py` ↔ `adapters\storage\__init__.py` | 42.66 | 0.0 |
| `core\__init__.py` ↔ `shared\__init__.py` | 39.9 | 0.0 |
| `core\__init__.py` ↔ `shared\config\__init__.py` | 33.99 | 0.0 |
| `core\__init__.py` ↔ `shared\logging\__init__.py` | 39.9 | 0.0 |
| `core\__init__.py` ↔ `utils\__init__.py` | 4.64 | 0.0 |
| `core\__init__.py` ↔ `utils\file_utils\__init__.py` | 22.16 | 0.0 |
| `core\__init__.py` ↔ `utils\helpers\__init__.py` | 46.27 | 0.0 |
| `core\__init__.py` ↔ `detectors\__init__.py` | 15.85 | 0.0 |
| `core\__init__.py` ↔ `config\__init__.py` | 15.85 | 0.0 |
| `core\auth\__init__.py` ↔ `core\db_manager\__init__.py` | 63.01 | 0 |
| `core\auth\__init__.py` ↔ `core\logs\__init__.py` | 8.33 | 0 |
| `core\auth\__init__.py` ↔ `core\search\__init__.py` | 37.17 | 0 |
| `core\auth\__init__.py` ↔ `core\session\__init__.py` | 37.17 | 0 |
| `core\auth\__init__.py` ↔ `infra\__init__.py` | 25.35 | 0 |
| `core\auth\__init__.py` ↔ `adapters\__init__.py` | 54.55 | 0 |
| `core\auth\__init__.py` ↔ `adapters\storage\__init__.py` | 69.96 | 0 |
| `core\auth\__init__.py` ↔ `shared\__init__.py` | 62.69 | 0 |
| `core\auth\__init__.py` ↔ `shared\config\__init__.py` | 54.55 | 0 |
| `core\auth\__init__.py` ↔ `shared\logging\__init__.py` | 62.69 | 0 |
| `core\auth\__init__.py` ↔ `utils\__init__.py` | 8.33 | 0 |
| `core\auth\__init__.py` ↔ `utils\file_utils\__init__.py` | 37.17 | 0 |
| `core\auth\__init__.py` ↔ `utils\helpers\__init__.py` | 75.63 | 0 |
| `core\auth\__init__.py` ↔ `detectors\__init__.py` | 25.35 | 0 |
| `core\auth\__init__.py` ↔ `config\__init__.py` | 25.35 | 0 |
| `core\db_manager\__init__.py` ↔ `core\logs\__init__.py` | 3.92 | 0 |
| `core\db_manager\__init__.py` ↔ `core\search\__init__.py` | 19.0 | 0 |
| `core\db_manager\__init__.py` ↔ `core\session\__init__.py` | 19.0 | 0 |
| `core\db_manager\__init__.py` ↔ `infra\__init__.py` | 12.59 | 0 |
| `core\db_manager\__init__.py` ↔ `adapters\__init__.py` | 29.42 | 0 |
| `core\db_manager\__init__.py` ↔ `adapters\storage\__init__.py` | 39.68 | 0 |
| `core\db_manager\__init__.py` ↔ `shared\__init__.py` | 34.71 | 0 |
| `core\db_manager\__init__.py` ↔ `shared\config\__init__.py` | 29.42 | 0 |
| `core\db_manager\__init__.py` ↔ `shared\logging\__init__.py` | 34.71 | 0 |
| `core\db_manager\__init__.py` ↔ `utils\__init__.py` | 3.92 | 0 |
| `core\db_manager\__init__.py` ↔ `utils\file_utils\__init__.py` | 19.0 | 0 |
| `core\db_manager\__init__.py` ↔ `utils\helpers\__init__.py` | 47.12 | 0 |
| `core\db_manager\__init__.py` ↔ `detectors\__init__.py` | 12.59 | 0 |
| `core\db_manager\__init__.py` ↔ `config\__init__.py` | 12.59 | 0 |
| `core\logs\__init__.py` ↔ `core\search\__init__.py` | 32.0 | 0 |
| `core\logs\__init__.py` ↔ `core\session\__init__.py` | 32.0 | 0 |
| `core\logs\__init__.py` ↔ `infra\__init__.py` | 43.24 | 0 |
| `core\logs\__init__.py` ↔ `adapters\__init__.py` | 20.78 | 0 |
| `core\logs\__init__.py` ↔ `adapters\storage\__init__.py` | 14.95 | 0 |
| `core\logs\__init__.py` ↔ `shared\__init__.py` | 17.39 | 0 |
| `core\logs\__init__.py` ↔ `shared\config\__init__.py` | 20.78 | 0 |
| `core\logs\__init__.py` ↔ `shared\logging\__init__.py` | 17.39 | 0 |
| `core\logs\__init__.py` ↔ `utils\__init__.py` | 100.0 | 0 |
| `core\logs\__init__.py` ↔ `utils\file_utils\__init__.py` | 32.0 | 0 |
| `core\logs\__init__.py` ↔ `utils\helpers\__init__.py` | 8.84 | 0 |
| `core\logs\__init__.py` ↔ `detectors\__init__.py` | 43.24 | 0 |
| `core\logs\__init__.py` ↔ `config\__init__.py` | 43.24 | 0 |
| `core\search\__init__.py` ↔ `core\session\__init__.py` | 100.0 | 0 |
| `core\search\__init__.py` ↔ `infra\__init__.py` | 56.34 | 0 |
| `core\search\__init__.py` ↔ `adapters\__init__.py` | 50.45 | 0 |
| `core\search\__init__.py` ↔ `adapters\storage\__init__.py` | 42.55 | 0 |
| `core\search\__init__.py` ↔ `shared\__init__.py` | 46.03 | 0 |
| `core\search\__init__.py` ↔ `shared\config\__init__.py` | 50.45 | 0 |
| `core\search\__init__.py` ↔ `shared\logging\__init__.py` | 46.03 | 0 |
| `core\search\__init__.py` ↔ `utils\__init__.py` | 32.0 | 0 |
| `core\search\__init__.py` ↔ `utils\file_utils\__init__.py` | 100.0 | 0 |
| `core\search\__init__.py` ↔ `utils\helpers\__init__.py` | 38.14 | 0 |
| `core\search\__init__.py` ↔ `detectors\__init__.py` | 56.34 | 0 |
| `core\search\__init__.py` ↔ `config\__init__.py` | 56.34 | 0 |
| `core\session\__init__.py` ↔ `infra\__init__.py` | 56.34 | 0 |
| `core\session\__init__.py` ↔ `adapters\__init__.py` | 50.45 | 0 |
| `core\session\__init__.py` ↔ `adapters\storage\__init__.py` | 42.55 | 0 |
| `core\session\__init__.py` ↔ `shared\__init__.py` | 46.03 | 0 |
| `core\session\__init__.py` ↔ `shared\config\__init__.py` | 50.45 | 0 |
| `core\session\__init__.py` ↔ `shared\logging\__init__.py` | 46.03 | 0 |
| `core\session\__init__.py` ↔ `utils\__init__.py` | 32.0 | 0 |
| `core\session\__init__.py` ↔ `utils\file_utils\__init__.py` | 100.0 | 0 |
| `core\session\__init__.py` ↔ `utils\helpers\__init__.py` | 38.14 | 0 |
| `core\session\__init__.py` ↔ `detectors\__init__.py` | 56.34 | 0 |
| `core\session\__init__.py` ↔ `config\__init__.py` | 56.34 | 0 |
| `infra\__init__.py` ↔ `adapters\__init__.py` | 53.06 | 0 |
| `infra\__init__.py` ↔ `adapters\storage\__init__.py` | 40.62 | 0 |
| `infra\__init__.py` ↔ `shared\__init__.py` | 46.02 | 0 |
| `infra\__init__.py` ↔ `shared\config\__init__.py` | 53.06 | 0 |
| `infra\__init__.py` ↔ `shared\logging\__init__.py` | 46.02 | 0 |
| `infra\__init__.py` ↔ `utils\__init__.py` | 43.24 | 0 |
| `infra\__init__.py` ↔ `utils\file_utils\__init__.py` | 56.34 | 0 |
| `infra\__init__.py` ↔ `utils\helpers\__init__.py` | 28.71 | 0 |
| `infra\__init__.py` ↔ `detectors\__init__.py` | 100.0 | 0 |
| `infra\__init__.py` ↔ `config\__init__.py` | 100.0 | 0 |
| `adapters\__init__.py` ↔ `adapters\storage\__init__.py` | 82.14 | 0 |
| `adapters\__init__.py` ↔ `shared\__init__.py` | 90.2 | 0 |
| `adapters\__init__.py` ↔ `shared\config\__init__.py` | 100.0 | 0 |
| `adapters\__init__.py` ↔ `shared\logging\__init__.py` | 90.2 | 0 |
| `adapters\__init__.py` ↔ `utils\__init__.py` | 20.78 | 0 |
| `adapters\__init__.py` ↔ `utils\file_utils\__init__.py` | 50.45 | 0 |
| `adapters\__init__.py` ↔ `utils\helpers\__init__.py` | 57.02 | 0 |
| `adapters\__init__.py` ↔ `detectors\__init__.py` | 51.02 | 0 |
| `adapters\__init__.py` ↔ `config\__init__.py` | 51.02 | 0 |
| `adapters\storage\__init__.py` ↔ `shared\__init__.py` | 91.8 | 0 |
| `adapters\storage\__init__.py` ↔ `shared\config\__init__.py` | 82.14 | 0 |
| `adapters\storage\__init__.py` ↔ `shared\logging\__init__.py` | 91.8 | 0 |
| `adapters\storage\__init__.py` ↔ `utils\__init__.py` | 14.95 | 0 |
| `adapters\storage\__init__.py` ↔ `utils\file_utils\__init__.py` | 39.72 | 0 |
| `adapters\storage\__init__.py` ↔ `utils\helpers\__init__.py` | 61.76 | 0 |
| `adapters\storage\__init__.py` ↔ `detectors\__init__.py` | 39.06 | 0 |
| `adapters\storage\__init__.py` ↔ `config\__init__.py` | 39.06 | 0 |
| `shared\__init__.py` ↔ `shared\config\__init__.py` | 90.2 | 0 |
| `shared\__init__.py` ↔ `shared\logging\__init__.py` | 100.0 | 0 |
| `shared\__init__.py` ↔ `utils\__init__.py` | 17.39 | 0 |
| `shared\__init__.py` ↔ `utils\file_utils\__init__.py` | 44.44 | 0 |
| `shared\__init__.py` ↔ `utils\helpers\__init__.py` | 65.37 | 0 |
| `shared\__init__.py` ↔ `detectors\__init__.py` | 44.25 | 0 |
| `shared\__init__.py` ↔ `config\__init__.py` | 44.25 | 0 |
| `shared\config\__init__.py` ↔ `shared\logging\__init__.py` | 90.2 | 0 |
| `shared\config\__init__.py` ↔ `utils\__init__.py` | 20.78 | 0 |
| `shared\config\__init__.py` ↔ `utils\file_utils\__init__.py` | 50.45 | 0 |
| `shared\config\__init__.py` ↔ `utils\helpers\__init__.py` | 57.02 | 0 |
| `shared\config\__init__.py` ↔ `detectors\__init__.py` | 51.02 | 0 |
| `shared\config\__init__.py` ↔ `config\__init__.py` | 51.02 | 0 |
| `shared\logging\__init__.py` ↔ `utils\__init__.py` | 17.39 | 0 |
| `shared\logging\__init__.py` ↔ `utils\file_utils\__init__.py` | 44.44 | 0 |
| `shared\logging\__init__.py` ↔ `utils\helpers\__init__.py` | 65.37 | 0 |
| `shared\logging\__init__.py` ↔ `detectors\__init__.py` | 44.25 | 0 |
| `shared\logging\__init__.py` ↔ `config\__init__.py` | 44.25 | 0 |
| `utils\__init__.py` ↔ `utils\file_utils\__init__.py` | 32.0 | 0 |
| `utils\__init__.py` ↔ `utils\helpers\__init__.py` | 8.84 | 0 |
| `utils\__init__.py` ↔ `detectors\__init__.py` | 43.24 | 0 |
| `utils\__init__.py` ↔ `config\__init__.py` | 43.24 | 0 |
| `utils\file_utils\__init__.py` ↔ `utils\helpers\__init__.py` | 38.14 | 0 |
| `utils\file_utils\__init__.py` ↔ `detectors\__init__.py` | 56.34 | 0 |
| `utils\file_utils\__init__.py` ↔ `config\__init__.py` | 56.34 | 0 |
| `utils\helpers\__init__.py` ↔ `detectors\__init__.py` | 28.71 | 0 |
| `utils\helpers\__init__.py` ↔ `config\__init__.py` | 28.71 | 0 |
| `detectors\__init__.py` ↔ `config\__init__.py` | 100.0 | 0 |

### 🎯 Consolidação

**Viável:** ⚠️ NÃO

**Razões:**
- Similaridade de nome insuficiente (0.0 < 85)
- Similaridade AST suficiente (100.0%)
- Overlap de assinaturas baixo (0.0% < 60%)
- ❌ Critérios não atendidos para consolidação automática
- 1 arquivo(s) órfão(s) - pode(m) ser removido(s)

**Riscos:**
- ⚠️ Camadas diferentes (application vs adapters) - podem ter propósitos distintos
- ⚠️ Muitos importers (492 > 40) - custo alto de reescrita

---

## 📦 Grupo: `theme`

### ✅ Canônico Sugerido

**Arquivo:** `utils\themes.py`

**Justificativa:** camada prioritária (20) + mais referenciado (34 importers) + 187 linhas

**Score:** 1918.70

### Arquivos no Grupo

| Arquivo | Camada | In-Degree | Linhas | Funções | Classes |
|---------|--------|-----------|--------|---------|----------|
|  `ui\theme.py` | ui | 21 | 44 | 1 | 0 |
| **✅** `utils\themes.py` | utils | 34 | 187 | 6 | 0 |

### Similaridades

| Par | AST Sim % | Sig Overlap % |
|-----|-----------|---------------|
| `ui\theme.py` ↔ `utils\themes.py` | 6.66 | 0.0 |

### 🎯 Consolidação

**Viável:** ⚠️ NÃO

**Razões:**
- Similaridade de nome insuficiente (0.0 < 85)
- Similaridade AST baixa (6.7% < 60%)
- Overlap de assinaturas baixo (0.0% < 60%)
- ❌ Critérios não atendidos para consolidação automática

**Riscos:**
- ⚠️ Camadas diferentes (utils, ui) - verificar propósito
- ⚠️ Muitos importers (55 > 40) - custo alto de reescrita

---

## 📦 Grupo: `audit`

### ✅ Canônico Sugerido

**Arquivo:** `core\logs\audit.py`

**Justificativa:** camada prioritária (90) + mais referenciado (30 importers) + 2 linhas

**Score:** 2400.20

### Arquivos no Grupo

| Arquivo | Camada | In-Degree | Linhas | Funções | Classes |
|---------|--------|-----------|--------|---------|----------|
| **✅** `core\logs\audit.py` | core | 30 | 2 | 0 | 0 |
|  `shared\logging\audit.py` | shared | 6 | 38 | 4 | 0 |

### Similaridades

| Par | AST Sim % | Sig Overlap % |
|-----|-----------|---------------|
| `core\logs\audit.py` ↔ `shared\logging\audit.py` | 6.98 | 0.0 |

### 🎯 Consolidação

**Viável:** ⚠️ NÃO

**Razões:**
- Similaridade de nome insuficiente (0.0 < 85)
- Similaridade AST baixa (7.0% < 60%)
- Overlap de assinaturas baixo (0.0% < 60%)
- ❌ Critérios não atendidos para consolidação automática
- Custo de reescrita aceitável (36 importers)

**Riscos:**
- ⚠️ Camadas diferentes (shared, core) - verificar propósito

---
