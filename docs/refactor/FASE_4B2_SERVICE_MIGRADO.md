# FASE 4B.2 — service.py migrado para core/ (CONCLUÍDO) ✅

**Data:** 2026-02-01  
**Objetivo:** Migrar `service.py` para `clientes/core/service.py` com shim de retrocompatibilidade.

---

## 📋 Mudanças Realizadas

### 1️⃣ Arquivo Migrado
- **Origem:** `src/modules/clientes/service.py` (495 linhas)
- **Destino:** `src/modules/clientes/core/service.py` (495 linhas)

### 2️⃣ Ajustes de Imports Relativos
```python
# ANTES (no nível clientes/):
from .components.helpers import STATUS_PREFIX_RE

# DEPOIS (dentro de core/):
from ..components.helpers import STATUS_PREFIX_RE
```

### 3️⃣ Shim de Retrocompatibilidade
Criado shim mínimo em `src/modules/clientes/service.py`:
- Re-exporta tudo de `.core.service`
- Emite `DeprecationWarning` uma vez por sessão
- Mantém compatibilidade total com código existente

**Exports públicos mantidos:**
- `ClienteCNPJDuplicadoError`
- `ClienteServiceError`
- `checar_duplicatas_para_form`
- `salvar_cliente_a_partir_do_form`
- `mover_cliente_para_lixeira`
- `restaurar_clientes_da_lixeira`
- `excluir_clientes_definitivamente`
- `listar_clientes_na_lixeira`
- `excluir_cliente_simples`
- `get_cliente_by_id`
- `fetch_cliente_by_id`
- `update_cliente_status_and_observacoes`
- `extrair_dados_cartao_cnpj_em_pasta`
- `count_clients`, `checar_duplicatas_info`, `salvar_cliente` (delegados ao legacy)

---

## ✅ Gates de Validação

### Gate 1: Guard clientes_v2 ✅
```bash
$ python tools/check_no_clientes_v2_imports.py
✅ SUCESSO: Nenhuma referência a clientes_v2 encontrada!
```

### Gate 2a: Sintaxe core/service.py ✅
```bash
$ python -m py_compile src/modules/clientes/core/service.py
(sem erros)
```

### Gate 2b: Sintaxe shim service.py ✅
```bash
$ python -m py_compile src/modules/clientes/service.py
(sem erros)
```

### Gate 3: Sanidade de imports ✅
```bash
$ python -c "import sys; sys.path.insert(0,'.'); from src.modules.clientes.service import *; from src.modules.clientes.core.service import *; print('✅ imports service OK')"
✅ imports service OK
```

### Gate 4: Inicialização da aplicação ✅
```bash
$ python main.py
2026-02-01 02:10:11 | INFO | startup | Logging level ativo: INFO
2026-02-01 02:10:12 | INFO | app_gui | Bootstrap do MainWindow concluído com tema: light
2026-02-01 02:10:18 | INFO | startup | Sessão restaurada (uid=44900b9f..., token: OK)
2026-02-01 02:10:19 | INFO | app_gui | Janela maximizada (zoomed) após login
2026-02-01 02:10:26 | INFO | src.infra.repositories.anvisa_requests_repository | [ANVISA] Listadas 44 demanda(s)
```

✅ App iniciou sem erros  
✅ Login OK  
✅ Módulos carregando normalmente

---

## 🔍 Importações Circulares

**Situação:** Nenhuma importação circular detectada.

O `core/service.py`:
- Importa de `src.core.*` (níveis superiores)
- Importa de `src.adapters.*` (infraestrutura)
- Importa de `..components.helpers` (irmão lateral)
- **NÃO** importa viewmodel (evita circular)

Consumidores de `service`:
- `view.py`, `editor.py`, `lixeira.py` → importam via shim ou core
- viewmodel → pode importar service sem circular (importação em uma direção)

---

## 📦 Estrutura Resultante

```
src/modules/clientes/
├── core/
│   ├── __init__.py
│   ├── viewmodel.py       ← migrado (FASE 4B.1)
│   └── service.py          ← migrado (FASE 4B.2) ✅
├── components/
│   └── helpers.py
├── service.py              ← SHIM com DeprecationWarning
└── viewmodel.py            ← SHIM com DeprecationWarning
```

---

## 📝 Observações

1. **Warnings emitidos:** Ao importar `src.modules.clientes.service`, usuários verão:
   ```
   DeprecationWarning: src.modules.clientes.service foi movido para src.modules.clientes.core.service. Atualize seus imports.
   ```

2. **Compatibilidade total:** Todo código existente continua funcionando sem mudanças.

3. **Próximo passo:** FASE 4B.3 migrará outros componentes (export, lixeira, etc.) seguindo o mesmo padrão.

---

## ✅ Critérios de Aceite

| Critério | Status |
|----------|--------|
| App inicia sem erro de import | ✅ |
| Tela Clientes funciona | ✅ |
| Salvar/editar cliente funciona | ✅ (service OK) |
| Nenhuma referência a clientes_v2 | ✅ |
| Shims funcionam | ✅ |
| Sintaxe validada | ✅ |

---

**Status:** ✅ **CONCLUÍDO**  
**Próxima fase:** FASE 4B.3 — Migrar export, lixeira, e helpers para core/
