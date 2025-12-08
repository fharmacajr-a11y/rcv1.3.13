# DevLog MS-6 – Main Screen: State Extraction & Test Builders

**Data:** 01/12/2025  
**Branch:** `qa/fixpack-04`  
**Projeto:** RC Gestor de Clientes v1.3.28+  
**Fase:** Headless Main Screen (State Extraction)

---

## 📋 Objetivo da Microfase

Extrair a definição de `MainScreenState` para um módulo dedicado e criar builders/factories tipados para construção de estados em testes, reduzindo duplicação e melhorando legibilidade.

**Requisitos:**

1. ✅ Extrair `MainScreenState` para módulo separado
2. ✅ Criar factory `make_main_screen_state()` para testes
3. ✅ Atualizar testes existentes para usar factory
4. ✅ Garantir 100% de compatibilidade (todos os testes passando)

---

## 🎯 Resultados

### 1. Novo Módulo: `main_screen_state.py`

Criado **`src/modules/clientes/views/main_screen_state.py`** com a definição extraída:

```python
from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from src.modules.clientes.viewmodel import ClienteRow


@dataclass
class MainScreenState:
    """Estado atual da tela principal de clientes.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação atual (ex.: "Razão Social (A→Z)")
        filter_label: Label de filtro de status atual (ex.: "Ativo", "Todos")
        search_text: Texto de busca atual
        selected_ids: IDs dos clientes selecionados (aceita list, tuple, set)
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira
    """

    clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_online: bool = True
    is_trash_screen: bool = False
```

**Benefícios:**
- Separação de responsabilidades (estado vs. lógica)
- Facilita reutilização em outros módulos
- Type hints preservados com `Collection[str]` para `selected_ids`

### 2. Atualização do Controller

Modificado **`src/modules/clientes/views/main_screen_controller.py`**:

```python
# Antes:
from collections.abc import Collection, Sequence
from dataclasses import dataclass

@dataclass
class MainScreenState:
    # ... definição local

# Depois:
from collections.abc import Sequence
from dataclasses import dataclass

from src.modules.clientes.views.main_screen_state import MainScreenState
```

- Removida definição local de `MainScreenState`
- Adicionado import do novo módulo
- Removido import não utilizado de `Collection`
- Zero impacto em funcionalidade

### 3. Factory para Testes

Criado **`tests/unit/modules/clientes/views/factories_main_screen_state.py`**:

```python
from collections.abc import Collection, Sequence

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_state import MainScreenState


def make_main_screen_state(
    *,
    clients: Sequence[ClienteRow] | None = None,
    order_label: str = "Razão Social (A→Z)",
    filter_label: str = "Todos",
    search_text: str = "",
    selected_ids: Collection[str] | None = None,
    is_online: bool = True,
    is_trash_screen: bool = False,
) -> MainScreenState:
    """Factory para criar MainScreenState com defaults sensatos."""
    if clients is None:
        clients = []

    if selected_ids is None:
        selected_ids = set()

    return MainScreenState(
        clients=clients,
        order_label=order_label,
        filter_label=filter_label,
        search_text=search_text,
        selected_ids=selected_ids,
        is_online=is_online,
        is_trash_screen=is_trash_screen,
    )
```

**Vantagens da Factory:**

- Defaults sensatos reduzem verbosidade nos testes
- Type hints explícitos facilitam IDE autocomplete
- Parâmetros nomeados melhoram legibilidade
- Permite sobrescrever apenas campos relevantes ao teste

### 4. Atualização dos Testes

Modificados:
- ✅ `test_main_screen_controller_ms1.py` (5 construções de estado)
- ✅ `test_main_screen_controller_filters_ms4.py` (1 construção via helper)

**Exemplo de simplificação:**

```python
# Antes:
state = ctrl.MainScreenState(
    clients=clients,
    order_label="Razão Social (A→Z)",
    filter_label="Todos",
    search_text="",
    selected_ids=[],
    is_online=True,
    is_trash_screen=False,
)

# Depois:
state = make_main_screen_state()
```

**Outro exemplo (override de campos específicos):**

```python
# Antes:
state = ctrl.MainScreenState(
    clients=clients,
    order_label="Razão Social (A→Z)",
    filter_label="Ativo",
    search_text="",
    selected_ids=["1"],
    is_online=True,
    is_trash_screen=False,
)

# Depois:
state = make_main_screen_state(
    clients=clients,
    filter_label="Ativo",
    selected_ids=["1"],
)
```

---

## ✅ Validação

### Suite de Testes Completa

```bash
pytest \
  tests\unit\modules\clientes\views\test_main_screen_controller_ms1.py \
  tests\unit\modules\clientes\views\test_main_screen_controller_filters_ms4.py \
  tests\unit\modules\clientes\views\test_main_screen_helpers_fase01.py \
  tests\unit\modules\clientes\views\test_main_screen_helpers_fase02.py \
  tests\unit\modules\clientes\views\test_main_screen_helpers_fase03.py \
  tests\unit\modules\clientes\views\test_main_screen_helpers_fase04.py \
  -v
```

**Resultado:**
```
====================== 234 passed in 26.12s =======================
```

✅ **100% dos testes passando** – Zero regressões

### Qualidade de Código

```bash
ruff check src\modules\clientes\views\main_screen_controller.py \
           src\modules\clientes\views\main_screen_state.py \
           tests\unit\modules\clientes\views\factories_main_screen_state.py
```

**Resultado:**
```
All checks passed!
```

✅ **Zero erros Ruff**

### Type Checking (Pylance)

Verificado via VS Code Pylance/Pyright:

- ✅ `main_screen_controller.py` – No errors found
- ✅ `main_screen_state.py` – No errors found
- ✅ `factories_main_screen_state.py` – No errors found

✅ **Zero erros de tipo**

---

## 📊 Resumo de Impacto

| Aspecto | Status |
|---------|--------|
| **Arquivos criados** | 2 (state module + factory) |
| **Arquivos modificados** | 3 (controller + 2 test files) |
| **Testes passando** | 234/234 ✅ |
| **Erros Ruff** | 0 ✅ |
| **Erros Pylance** | 0 ✅ |
| **Breaking changes** | 0 ✅ |
| **Regressões** | 0 ✅ |

---

## 🔍 Arquivos Modificados/Criados

### Criados:
1. `src/modules/clientes/views/main_screen_state.py` (39 linhas)
2. `tests/unit/modules/clientes/views/factories_main_screen_state.py` (85 linhas)

### Modificados:
1. `src/modules/clientes/views/main_screen_controller.py`
   - Removida definição local de `MainScreenState`
   - Adicionado import do módulo dedicado

2. `tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py`
   - Adicionado import da factory
   - Simplificadas 5 construções de estado

3. `tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py`
   - Adicionado import da factory
   - Simplificado helper `compute_visible_clients()`

---

## 🎓 Lições Aprendidas

### ✅ Boas Práticas Confirmadas

1. **Separação de Estado e Lógica**
   - Estado em módulo dedicado facilita composição
   - Controller foca apenas em transformações

2. **Factories Reduzem Duplicação**
   - Defaults sensatos eliminam boilerplate
   - Testes ficam mais legíveis e focados

3. **Type Hints Preservados**
   - `Collection[str]` para `selected_ids` continua funcionando
   - Pylance não reporta `set[Unknown]` mais

4. **Backward Compatibility**
   - Extração de definição não quebra código existente
   - Import bem estruturado mantém compatibilidade

### 📝 Decisões de Design

1. **Por que módulo separado para estado?**
   - Facilita reutilização em outros controllers/views
   - Permite evoluir definição de estado independentemente
   - Melhora testabilidade (mock de estado fica mais simples)

2. **Por que factory em vez de fixtures pytest?**
   - Factories são mais flexíveis (chamadas em qualquer ponto)
   - Não dependem de escopo de fixture
   - Type hints funcionam melhor com funções simples

3. **Por que defaults na factory?**
   - Casos de teste focam apenas no que importa
   - Reduz "noise" em testes simples
   - Mantém testes robustos a mudanças em defaults

---

## 🚀 Próximos Passos Sugeridos

### MS-7: Strict Type Checking
- [ ] Habilitar `strict = true` em `pyrightconfig.json` para o módulo `views`
- [ ] Resolver warnings de tipo (se houver)
- [ ] Adicionar `# pyright: strict` nos módulos novos

### MS-8: Protocol-Based Design
- [ ] Criar `Protocol` para estado da Main Screen (duck typing)
- [ ] Permitir diferentes implementações de estado (ex.: com cache)
- [ ] Melhorar testabilidade com mock objects

### MS-9: Computed State Caching
- [ ] Avaliar cache de `MainScreenComputed` para evitar recomputação
- [ ] Implementar estratégia de invalidação de cache
- [ ] Benchmark de performance antes/depois

### MS-10: Integration Tests
- [ ] Testes de integração entre controller e UI Tkinter
- [ ] Validar binding de estado com widgets
- [ ] Testes de cenários complexos (multi-step)

---

## 📌 Status Final

**Microfase MS-6: ✅ CONCLUÍDA COM SUCESSO**

- ✅ MainScreenState extraído para módulo dedicado
- ✅ Factory tipada criada para testes
- ✅ Testes atualizados e simplificados
- ✅ 234/234 testes passando
- ✅ Zero erros de lint/type checking
- ✅ 100% backward compatible

**Código está pronto para merge em `qa/fixpack-04`**

---

## 🔗 Referências

- **DevLog anterior:** `devlog-main-screen-ms5.md`
- **Branch:** `qa/fixpack-04`
- **Base de código:** v1.3.28.zip
- **Python:** 3.13
- **Framework:** Tkinter/ttkbootstrap (headless layer apenas)

---

**Assinatura:**  
Refatoração MS-6 completada com sucesso mantendo 100% de compatibilidade e qualidade de código.
