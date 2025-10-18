# Relatório de Módulos Duplicados
**Data:** 2025-10-18 08:32:40
**Total de grupos duplicados:** 3
---

## 📦 Grupo: `__init__.py`
**Total de arquivos:** 22
**✅ Canônico eleito:** `adapters\__init__.py`
**Justificativa:** mais importado (6 refs) + 1 linhas

### Arquivos no grupo:
| Caminho | Linhas | Imports | SHA-256 (6) | Modificado | Centralidade |
|---------|--------|---------|-------------|------------|-------------|
|  `application\__init__.py` | 1 | [] | `540752...` | 2025-10-18 | 0 |
|  `gui\__init__.py` | 8 | [] | `d7b3d7...` | 2025-10-18 | 0 |
|  `ui\__init__.py` | 3 | ['ui.components'] | `f781c1...` | 2025-10-18 | 0 |
|  `ui\dialogs\__init__.py` | 0 | [] | `b23c34...` | 2025-10-18 | 0 |
|  `ui\forms\__init__.py` | 1 | [] | `462c39...` | 2025-10-11 | 0 |
|  `ui\lixeira\__init__.py` | 4 | [] | `580d48...` | 2025-10-18 | 0 |
|  `ui\login\__init__.py` | 1 | [] | `8b20c0...` | 2025-10-11 | 0 |
|  `ui\widgets\__init__.py` | 6 | ['ui.components'] | `b1c1ec...` | 2025-10-18 | 0 |
|  `core\__init__.py` | 9 | [] | `a7e619...` | 2025-10-18 | 0 |
|  `core\auth\__init__.py` | 7 | [] | `2fd5c0...` | 2025-10-18 | 0 |
|  `core\db_manager\__init__.py` | 28 | [] | `dd1ea0...` | 2025-10-18 | 0 |
|  `core\logs\__init__.py` | 0 | [] | `527c66...` | 2025-10-11 | 0 |
|  `core\search\__init__.py` | 1 | [] | `0185f7...` | 2025-10-11 | 0 |
|  `core\session\__init__.py` | 1 | [] | `05c948...` | 2025-10-11 | 0 |
|  `utils\__init__.py` | 0 | [] | `e3b0c4...` | 2025-10-11 | 0 |
|  `utils\file_utils\__init__.py` | 1 | [] | `6af4e5...` | 2025-10-11 | 0 |
|  `utils\helpers\__init__.py` | 4 | ['utils.hash_utils'] | `21324c...` | 2025-10-18 | 0 |
| **✅** `adapters\__init__.py` | 1 | [] | `000901...` | 2025-10-18 | 6 |
|  `adapters\storage\__init__.py` | 1 | [] | `59a8c7...` | 2025-10-18 | 0 |
|  `shared\__init__.py` | 1 | [] | `b2a875...` | 2025-10-18 | 5 |
|  `shared\config\__init__.py` | 1 | [] | `8b1f8e...` | 2025-10-18 | 0 |
|  `shared\logging\__init__.py` | 1 | [] | `c641dd...` | 2025-10-18 | 0 |


## 📦 Grupo: `api.py`
**Total de arquivos:** 2
**✅ Canônico eleito:** `application\api.py`
**Justificativa:** mais importado (2 refs) + 317 linhas

### Arquivos no grupo:
| Caminho | Linhas | Imports | SHA-256 (6) | Modificado | Centralidade |
|---------|--------|---------|-------------|------------|-------------|
| **✅** `application\api.py` | 317 | ['utils.hash_utils', 'adapters.__init__', 'core.models'] | `c7dcd6...` | 2025-10-18 | 2 |
|  `adapters\storage\api.py` | 73 | [] | `7b8813...` | 2025-10-18 | 0 |


## 📦 Grupo: `audit.py`
**Total de arquivos:** 2
**✅ Canônico eleito:** `core\logs\audit.py`
**Justificativa:** 1 linhas

### Arquivos no grupo:
| Caminho | Linhas | Imports | SHA-256 (6) | Modificado | Centralidade |
|---------|--------|---------|-------------|------------|-------------|
| **✅** `core\logs\audit.py` | 1 | ['shared.__init__'] | `ef93b4...` | 2025-10-18 | 0 |
|  `shared\logging\audit.py` | 26 | [] | `0f9f9b...` | 2025-10-18 | 0 |
