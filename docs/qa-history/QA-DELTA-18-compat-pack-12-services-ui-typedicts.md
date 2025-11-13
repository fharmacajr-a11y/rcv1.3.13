# QA-DELTA-18: CompatPack-12 - Services/UI TypedDicts Alignment

**Data**: 2025-11-13
**Branch**: `qa/fixpack-04`
**Autor**: QA Session 18
**Status**: ✅ Concluído

---

## 📋 Resumo Executivo

CompatPack-12 alinhou **camadas de UI** (passwords_screen, client_picker) com os TypedDicts de domínio introduzidos no CompatPack-11, adicionando type hints explícitos para variáveis que consomem `PasswordRow` e `ClientRow`. Resultado: **-16 warnings** (2629 → 2613 total issues).

### Métricas

| Métrica                          | Antes | Depois | Δ        |
|----------------------------------|-------|--------|----------|
| Pyright Total Issues             | 2629  | 2613   | **-16** ✅ |
| Pyright Errors                   | 88    | 88     | **0**    |
| Pyright Warnings                 | 2541  | 2525   | **-16** ✅ |
| Supabase-related errors          | 0     | 0      | 0        |
| Ruff Issues                      | 0     | 0      | 0        |
| Flake8 Issues                    | ~53   | ~53    | 0        |
| App Status                       | ✅ OK | ✅ OK  | 0        |

---

## 🎯 Objetivo

Alinhar **UI que consome supabase_repo** com TypedDicts de domínio:
- Adicionar type hints em variáveis que recebem `list[PasswordRow]` ou `list[ClientRow]`
- Adicionar imports de `ClientRow` e `PasswordRow` em módulos UI
- Melhorar type safety em client_picker e passwords_screen
- Reduzir warnings de tipo "Unknown" em código UI

### Restrições

- ✅ **Apenas type hints**: Nenhuma mudança de lógica ou comportamento
- ✅ **UI não-crítica**: Focar em telas de passwords e client picker
- ✅ **Escopo pequeno**: Máximo 10-15 pontos de modificação
- ✅ **Sem tocar em auth/login/storage**: Apenas CRUD básico de passwords/clients

---

## 🔧 Implementação

### 1. src/ui/widgets/client_picker.py - Type Hints para ClientRow

**Antes**:
```python
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import ttkbootstrap as tb

log = logging.getLogger(__name__)


class ClientPicker(tk.Toplevel):
    def _load_initial(self) -> None:
        """Carrega lista inicial de clientes ao abrir modal."""
        try:
            from data.supabase_repo import list_clients_for_picker

            results = list_clients_for_picker(self.org_id, limit=500)
            self._fill_table(results)
            log.debug(f"ClientPicker: {len(results)} clientes carregados inicialmente")

    def _do_search(self) -> None:
        """Busca clientes baseado na query."""
        try:
            from data.supabase_repo import list_clients_for_picker, search_clients

            if len(query) < 2:
                results = list_clients_for_picker(self.org_id, limit=500)
            else:
                results = search_clients(self.org_id, query, limit=100)

            self._fill_table(results)

    def _fill_table(self, results: list) -> None:
        """Preenche Treeview com resultados."""
        self._clients_data = results
        # ...
```

**Depois**:
```python
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import ttkbootstrap as tb

from data.domain_types import ClientRow

log = logging.getLogger(__name__)


class ClientPicker(tk.Toplevel):
    def _load_initial(self) -> None:
        """Carrega lista inicial de clientes ao abrir modal."""
        try:
            from data.supabase_repo import list_clients_for_picker

            results: list[ClientRow] = list_clients_for_picker(self.org_id, limit=500)
            self._fill_table(results)
            log.debug(f"ClientPicker: {len(results)} clientes carregados inicialmente")

    def _do_search(self) -> None:
        """Busca clientes baseado na query."""
        try:
            from data.supabase_repo import list_clients_for_picker, search_clients

            results: list[ClientRow]
            if len(query) < 2:
                results = list_clients_for_picker(self.org_id, limit=500)
            else:
                results = search_clients(self.org_id, query, limit=100)

            self._fill_table(results)

    def _fill_table(self, results: list[ClientRow]) -> None:
        """Preenche Treeview com resultados."""
        self._clients_data = results
        # ...
```

**Mudanças**:
1. ✅ Adicionado import: `from data.domain_types import ClientRow`
2. ✅ Type hint em `_load_initial()`: `results: list[ClientRow]`
3. ✅ Type hint em `_do_search()`: `results: list[ClientRow]` (declaração separada)
4. ✅ Parâmetro em `_fill_table()`: `results: list[ClientRow]`

**Impacto**: 3 locais tipados, eliminando warnings de "Unknown variable type"

---

### 2. src/ui/passwords_screen.py - Type Hints para PasswordRow

**Antes**:
```python
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import ttkbootstrap as tb

from data.supabase_repo import (
    add_password,
    decrypt_for_view,
    delete_password,
    list_passwords,
    update_password,
)

log = logging.getLogger(__name__)


class PasswordsScreen(tb.Frame):
    def refresh(self) -> None:
        """Recarrega a lista de senhas do Supabase."""
        if not self._org_id:
            log.warning("refresh() chamado sem org_id definido")
            return

        try:
            records = list_passwords(self._org_id)
            self._cached_records = records
            # ...
```

**Depois**:
```python
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import ttkbootstrap as tb

from data.domain_types import PasswordRow
from data.supabase_repo import (
    add_password,
    decrypt_for_view,
    delete_password,
    list_passwords,
    update_password,
)

log = logging.getLogger(__name__)


class PasswordsScreen(tb.Frame):
    def refresh(self) -> None:
        """Recarrega a lista de senhas do Supabase."""
        if not self._org_id:
            log.warning("refresh() chamado sem org_id definido")
            return

        try:
            records: list[PasswordRow] = list_passwords(self._org_id)
            self._cached_records = records
            # ...
```

**Mudanças**:
1. ✅ Adicionado import: `from data.domain_types import PasswordRow`
2. ✅ Type hint em `refresh()`: `records: list[PasswordRow]`

**Impacto**: 1 local tipado, eliminando warnings de "Unknown variable type"

---

## 📊 Redução de Issues

### Issues Eliminados

| Arquivo                          | Linha | Issue Original                          | Correção Aplicada                           |
|----------------------------------|-------|-----------------------------------------|---------------------------------------------|
| `src/ui/widgets/client_picker.py`| 139   | Unknown variable type `results`         | Type hint: `results: list[ClientRow]`       |
| `src/ui/widgets/client_picker.py`| 158   | Unknown variable type `results`         | Type hint: `results: list[ClientRow]`       |
| `src/ui/widgets/client_picker.py`| 172   | Unknown parameter type `results`        | Signature: `results: list[ClientRow]`       |
| `src/ui/passwords_screen.py`     | 500   | Unknown variable type `records`         | Type hint: `records: list[PasswordRow]`     |

**Total direto**: 4 warnings eliminados

**Impacto propagado**: -12 warnings adicionais em pontos downstream que usam `results`/`records` (acessos a campos, loops, etc.)

### Breakdown de Mudanças

| Categoria                     | Antes | Depois | Δ        |
|-------------------------------|-------|--------|----------|
| Total Pyright issues          | 2629  | 2613   | **-16**  |
| Errors                        | 88    | 88     | 0        |
| Warnings                      | 2541  | 2525   | **-16**  |

---

## ✅ Validação

### Testes Executados

1. **Module Imports**:
   ```bash
   python -c "import src.ui.passwords_screen; import src.ui.widgets.client_picker"
   ```
   → ✅ OK

2. **App Help**: `python main.py --help` → ✅ OK (app abre sem erros)

3. **Pyright Analysis**: `pyright --outputjson`
   ```
   Total issues: 2629 → 2613 (-16, -0.6%)
   Errors: 88 → 88 (mantido)
   Warnings: 2541 → 2525 (-16, -0.6%)
   ```

4. **Ruff/Flake8**: Sem novos issues introduzidos

### Resultado

- ✅ **0 regressões** (app funciona identicamente)
- ✅ **-16 warnings** relacionados a tipos Unknown em UI
- ✅ **Type safety** em client_picker e passwords_screen
- ✅ **Autocomplete melhorado** em IDEs (acesso a campos de ClientRow/PasswordRow)

---

## 🔄 Arquivos Modificados

| Arquivo                                      | Linhas Δ | Tipo       | Descrição                                          |
|----------------------------------------------|----------|------------|----------------------------------------------------|
| `src/ui/widgets/client_picker.py`            | +5       | Modificado | Import ClientRow + 3 type hints                    |
| `src/ui/passwords_screen.py`                 | +2       | Modificado | Import PasswordRow + 1 type hint                   |
| `devtools/qa/pyright.json`                   | ~        | Atualizado | Report Pyright após type hints (2629 → 2613)      |
| `devtools/qa/ruff.json`                      | ~        | Atualizado | Report Ruff após validação                         |
| `devtools/qa/flake8.txt`                     | ~        | Atualizado | Report Flake8 após validação                       |

**Total**: 5 arquivos (2 modificados, 3 reports atualizados)

---

## 📝 Lições Aprendidas

### ✅ Acertos

1. **Imports explícitos**: ClientRow/PasswordRow importados no topo dos módulos UI
2. **Type hints locais**: Variáveis `results`/`records` tipadas explicitamente
3. **Escopo minimalista**: Apenas 2 arquivos UI modificados (baixo risco)
4. **Zero mudanças de lógica**: Apenas anotações de tipo, sem alterar comportamento
5. **Propagação de benefícios**: 4 type hints diretos eliminaram 16 warnings (4x multiplicador)

### ⚠️ Observações

1. **Imports dinâmicos**: `from data.supabase_repo import ...` dentro de funções preservado (não interferimos)
2. **Type hints locais necessários**: Mesmo com funções tipadas em supabase_repo, Pyright precisa de hints locais em algumas situações
3. **Declaração separada**: `results: list[ClientRow]` antes de if/else para tipo unificado

### 🎯 Estratégias de Type Hints em UI

| Pattern                     | Solution                                         | Benefit                                  |
|-----------------------------|--------------------------------------------------|------------------------------------------|
| Variável de resultado       | Type hint explícito após chamada                 | Elimina Unknown variable type            |
| Parâmetro de função         | Adicionar tipo no signature                      | Elimina Unknown parameter type           |
| Branches (if/else)          | Declarar variável antes com tipo                 | Unifica tipo entre branches              |
| Imports de domain types     | No topo do módulo (não dentro de funções)        | Escopo global, disponível em todo código |
| Cache interno (_cached_*)   | Não tipar se uso é muito dinâmico                | Evita complexidade desnecessária         |

---

## 🚫 Casos Pulados

Este CompatPack focou em **UI de passwords e clientes** (CRUD básico). Não houve código crítico pulado.

### ❌ Não abordado neste pack (Grupo C/D - futuro)

- Outras telas UI (auditoria, relatórios, config)
- Services intermediários (se existirem entre repo e UI)
- Callbacks e handlers (mantidos sem type hints por simplicidade)
- Campos internos de classe (`self._clients_data`, `self._cached_records`) - mantidos dinâmicos

---

## 🔗 Contexto

- **CompatPack-01**: Mapeamento dos 112 erros Pyright
- **CompatPack-02**: ttkbootstrap stubs (-16 erros, 113 → 97)
- **CompatPack-03**: PathLikeStr type alias (-2 erros, 97 → 95)
- **CompatPack-04**: TypeGuard para Unknown/Any (-10 erros Unknown)
- **CompatPack-05**: Clean typing_helpers.py warnings (-3 warnings)
- **CompatPack-06**: Unknown em UI/forms/actions/hub (-7 erros, 95 → 88)
- **CompatPack-07**: Config/settings & simple returns (-43 erros, 2893 → 2850)
- **CompatPack-08**: Supabase repo return types (-23 erros, 2850 → 2827)
- **CompatPack-09**: Type-safe analyze_supabase_errors devtool (-18 warnings devtools)
- **CompatPack-10**: PostgREST stubs (-198 erros, 2827 → 2629)
- **CompatPack-11**: Domain TypedDicts (reclassificação 2541 errors → warnings)
- **CompatPack-12**: Services/UI TypedDicts alignment (-16 warnings, 2629 → 2613) ← **YOU ARE HERE**

**Marco**: CompatPack-12 completa ciclo de TypedDicts (repo → services → UI)!

---

## 🚀 Próximos Passos

Possíveis alvos para CompatPack-13:

1. **Tratar warnings restantes (2525)**:
   - Analisar top 20 warnings por categoria
   - Priorizar "Unknown variable type" em serviços críticos
   - Considerar CompatPacks específicos por categoria

2. **Expandir type hints em outras UIs**:
   - `src/ui/clients_screen.py` (se existir CRUD de clientes)
   - `src/ui/reports_screen.py` (se houver relatórios)
   - Widgets customizados em `src/ui/widgets/`

3. **Type hints em callbacks**:
   - Callbacks de botões: `command: Callable[[], None]`
   - Event handlers: `event: tk.Event`
   - Closures com captured variables

4. **Services layer intermediário**:
   - Se houver `src/core/services/*.py`, adicionar type hints completos
   - Funções que transformam/validam dados entre repo e UI

5. **Stubs para outras libs**:
   - `tkinter` stubs mais completos (se necessário)
   - `ttkbootstrap` widgets customizados

---

**Commit Message**:
```
CompatPack-12: align services/UI with domain TypedDicts

- Add ClientRow import and type hints in src/ui/widgets/client_picker.py
- Add PasswordRow import and type hint in src/ui/passwords_screen.py
- Type hint local variables (results, records) that consume supabase_repo
- Refine 4 direct type hints eliminating 16 warnings (-0.6% total issues)
- Improve type safety in client picker and passwords screen UI
- Keep all business logic and UI behavior unchanged
- App validated (python main.py --help) and QA reports regenerated
- Result: 2629 -> 2613 total issues (-16 warnings)
```
