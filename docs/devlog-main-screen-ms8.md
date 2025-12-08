# DevLog MS-8 – Headless Main Screen: Protocol-Based State Design

**Data:** 01/12/2025  
**Branch:** `qa/fixpack-04`  
**Projeto:** RC Gestor de Clientes v1.3.28+  
**Fase:** Protocol-Based Design (Camada Headless)

---

## 📋 Objetivo da Microfase

Introduzir Protocols (PEP 544) para representar as interfaces de leitura do estado e dados computados da Main Screen, permitindo structural subtyping e facilitando testes com mocks, sem alterar comportamento da aplicação.

**Requisitos:**

1. ✅ Criar Protocol para interface de `MainScreenState`
2. ✅ Criar Protocol para interface de `MainScreenComputed`
3. ✅ Atualizar funções para aceitar Protocols onde apropriado
4. ✅ Garantir 100% de compatibilidade (todos os testes passando)
5. ✅ Manter strict mode sem novos erros

---

## 🎯 Resultados

### 1. Protocol para MainScreenState

Criado **`MainScreenStateLike`** em `src/modules/clientes/views/main_screen_state.py`:

```python
from typing import Protocol

class MainScreenStateLike(Protocol):
    """Interface de leitura para o estado da Main Screen.

    Qualquer objeto com esses atributos é considerado um 'estado' válido.
    Permite structural subtyping e facilita testes com mocks.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação atual
        filter_label: Label de filtro de status atual
        search_text: Texto de busca atual
        selected_ids: IDs dos clientes selecionados
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira
    """

    clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_online: bool
    is_trash_screen: bool
```

**Benefícios:**
- ✅ Define contrato de interface sem acoplamento à implementação
- ✅ Permite duck typing (qualquer objeto com esses atributos funciona)
- ✅ Facilita criação de mocks em testes
- ✅ Documenta expectativas de forma explícita

### 2. Protocol para MainScreenComputed

Criado **`MainScreenComputedLike`** em `src/modules/clientes/views/main_screen_controller.py`:

```python
from typing import Protocol

class MainScreenComputedLike(Protocol):
    """Interface de leitura para os dados computados da Main Screen.

    Permite structural subtyping e facilita testes com mocks.

    Attributes:
        visible_clients: Clientes visíveis após aplicar filtros e ordenação
        can_batch_delete: Se a ação de exclusão em massa está disponível
        can_batch_restore: Se a ação de restauração em massa está disponível
        can_batch_export: Se a ação de exportação em massa está disponível
        selection_count: Quantidade de itens selecionados
        has_selection: Se há pelo menos um item selecionado
    """

    visible_clients: Sequence[ClienteRow]
    can_batch_delete: bool
    can_batch_restore: bool
    can_batch_export: bool
    selection_count: int
    has_selection: bool
```

**Benefícios:**
- ✅ Permite funções consumidoras trabalharem com interface
- ✅ Facilita evolução da implementação sem quebrar contratos
- ✅ Testes podem usar objetos simples em vez de dataclasses completas

### 3. Uso de Protocols nas Funções

#### Antes (acoplado à implementação):
```python
def compute_main_screen_state(state: MainScreenState) -> MainScreenComputed:
    """Aplica filtros, ordenação e calcula disponibilidade de ações em lote."""
    # ... implementação
```

#### Depois (desacoplado via Protocol):
```python
def compute_main_screen_state(state: MainScreenStateLike) -> MainScreenComputed:
    """Aplica filtros, ordenação e calcula disponibilidade de ações em lote."""
    # ... implementação
```

**Vantagens:**
- ✅ Função aceita qualquer objeto que implemente a interface
- ✅ Testes podem passar mocks simples
- ✅ Retorno continua sendo a implementação concreta (dataclass)
- ✅ Backward compatible: `MainScreenState` satisfaz automaticamente `MainScreenStateLike`

### 4. Organização dos Módulos

#### `main_screen_state.py`
```python
# PROTOCOLS (INTERFACES)
class MainScreenStateLike(Protocol):
    ...

# CONCRETE IMPLEMENTATIONS
@dataclass
class MainScreenState:
    ...
```

#### `main_screen_controller.py`
```python
from src.modules.clientes.views.main_screen_state import (
    MainScreenState,  # noqa: F401 - usado em doctests
    MainScreenStateLike,
)

# PROTOCOLS (INTERFACES)
class MainScreenComputedLike(Protocol):
    ...

# CONCRETE IMPLEMENTATIONS
@dataclass
class MainScreenComputed:
    ...
```

**Decisão de design:**
- Protocols no mesmo módulo que as implementações concretas
- Facilita descoberta e manutenção
- Evita imports circulares

---

## ✅ Validação Completa

### Suite de Testes da Main Screen

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
====================== 234 passed in 25.81s =======================
```

✅ **100% dos testes passando** – Zero regressões

### Qualidade de Código (Ruff)

```bash
ruff check \
  src\modules\clientes\views\main_screen_state.py \
  src\modules\clientes\views\main_screen_controller.py \
  src\modules\clientes\views\main_screen_helpers.py
```

**Resultado:**
```
All checks passed!
```

✅ **Zero erros Ruff** (com noqa apropriado para doctest import)

### Type Checking (Pyright Strict)

Verificado via VS Code Pylance/Pyright com strict mode habilitado:

- ✅ `main_screen_state.py` – No errors found (strict)
- ✅ `main_screen_controller.py` – No errors found (strict)
- ✅ `main_screen_helpers.py` – No errors found (strict)

✅ **Zero erros de tipo em strict mode**

**Nota:** O warning "A importação 'MainScreenState' não foi acessada" é apenas informativo do Pylance. O import é necessário para doctests em runtime e está corretamente marcado com `# noqa: F401`.

---

## 📊 Resumo de Impacto

| Aspecto | Status |
|---------|--------|
| **Arquivos modificados** | 2 (state + controller) |
| **Protocols criados** | 2 (State + Computed) |
| **Funções atualizadas** | 1 (compute_main_screen_state) |
| **Campos em Protocols** | 13 (7 State + 6 Computed) |
| **Testes passando** | 234/234 ✅ |
| **Erros Ruff** | 0 ✅ |
| **Erros Pylance (strict)** | 0 ✅ |
| **Breaking changes** | 0 ✅ |
| **Regressões** | 0 ✅ |

---

## 🔍 Arquivos Modificados

### 1. `src/modules/clientes/views/main_screen_state.py`

**Mudanças:**
- Adicionado import `Protocol` de `typing`
- Criado `MainScreenStateLike` Protocol com 7 atributos
- Reorganizado com seções para Protocols e implementações concretas
- Atualizado docstring do módulo (menção à fase MS-8)

**Estatísticas:**
- Linhas antes: 39
- Linhas depois: 75
- Linhas adicionadas: +36 (Protocol + documentação)
- Type safety: ⭐⭐⭐⭐⭐

### 2. `src/modules/clientes/views/main_screen_controller.py`

**Mudanças:**
- Adicionado import `Protocol` de `typing`
- Importado `MainScreenStateLike` de `main_screen_state`
- Criado `MainScreenComputedLike` Protocol com 6 atributos
- Atualizada assinatura de `compute_main_screen_state()` para aceitar `MainScreenStateLike`
- Reorganizado com seções para Protocols e implementações concretas
- Adicionado `# noqa: F401` para import usado em doctests
- Atualizado docstring do módulo (menção à fase MS-8)

**Estatísticas:**
- Linhas antes: 317
- Linhas depois: 351
- Linhas adicionadas: +34 (Protocol + reorganização)
- Funções atualizadas: 1
- Type safety: ⭐⭐⭐⭐⭐

### 3. `src/modules/clientes/views/main_screen_helpers.py`

**Mudanças:** Nenhuma

**Motivo:** Os helpers não consomem `MainScreenState` ou `MainScreenComputed` diretamente, trabalham apenas com primitivos e sequências. Não há necessidade de atualização nesta fase.

---

## 🎓 Lições Aprendidas

### ✅ Boas Práticas Confirmadas

1. **Structural Subtyping com Protocols**
   - Protocols permitem duck typing tipado
   - Implementações concretas satisfazem automaticamente
   - Não requer herança explícita

2. **Organização de Protocols**
   - Protocols no mesmo módulo que implementações
   - Facilita descoberta e evolução
   - Evita imports circulares

3. **Uso Seletivo de Protocols**
   - Parâmetros read-only → Protocol
   - Retornos concretos → Dataclass
   - Mantém flexibilidade de entrada com garantia de saída

4. **Compatibilidade com Doctests**
   - Imports necessários para doctests marcados com `# noqa: F401`
   - Documenta razão do import aparentemente não usado
   - Mantém exemplos executáveis

### 📝 Decisões de Design

1. **Por que Protocols no mesmo módulo?**
   - Evita proliferação de arquivos
   - Facilita navegação (interface + implementação juntos)
   - Reduz complexidade de imports

2. **Por que aceitar Protocol mas retornar dataclass concreta?**
   - Input flexível: aceita mocks, objetos simples, etc.
   - Output garantido: retorna sempre implementação completa
   - Padrão comum em bibliotecas Python modernas

3. **Por que apenas `compute_main_screen_state()` foi atualizada?**
   - Outras funções não recebem state/computed como parâmetro
   - Foco em pontos de entrada principais
   - Expansão incremental conforme necessidade

4. **Por que não criar Protocols em módulo separado?**
   - Evita overhead de imports adicionais
   - Mantém relacionamento claro entre interface e implementação
   - Facilita refatoração futura (mudar ambos juntos)

### 🔧 Tratamento de Casos Especiais

#### Import usado em Doctest

**Problema:** Ruff reporta `MainScreenState` como não usado, mas é necessário para doctests.

**Solução:**
```python
from src.modules.clientes.views.main_screen_state import (
    MainScreenState,  # noqa: F401 - usado em doctests
    MainScreenStateLike,
)
```

**Alternativas consideradas:**
- ❌ `TYPE_CHECKING`: Não funciona porque doctests executam em runtime
- ❌ Remover doctest: Perde documentação valiosa
- ✅ `noqa` com comentário explicativo: Documenta intenção

---

## 🚀 Próximos Passos Sugeridos

### MS-9: Expandir Protocols para Camada UI
- [ ] Criar Protocol para callbacks da UI Tkinter
- [ ] Refatorar `main_screen.py` para usar `MainScreenStateLike` e `MainScreenComputedLike`
- [ ] Reduzir acoplamento entre UI e lógica de negócio
- [ ] Facilitar testes de integração com mocks

### MS-10: Refinar Protocol ClientWithCreatedAt
- [ ] Expandir Protocol para incluir mais operações comuns
- [ ] Criar Protocol para acesso a campos de cliente
- [ ] Remover `| Any` tornando tipos mais estritos
- [ ] Documentar padrões de uso de Protocols

### MS-11: Cache de Computed State
- [ ] Implementar cache baseado em hash de `MainScreenStateLike`
- [ ] Usar Protocols para estratégias de invalidação
- [ ] Benchmark de performance antes/depois
- [ ] Testes de cache com diferentes implementações de Protocol

### MS-12: Testes com Mocks Protocol-Based
- [ ] Criar fixtures que usam Protocols em vez de dataclasses
- [ ] Simplificar setup de testes com objetos mínimos
- [ ] Validar que Protocols realmente facilitam testes
- [ ] Documentar padrões de mock com Protocols

---

## 📌 Status Final

**Microfase MS-8: ✅ CONCLUÍDA COM SUCESSO**

- ✅ 2 Protocols criados (State + Computed)
- ✅ Structural subtyping habilitado
- ✅ Função principal usando Protocol para input
- ✅ 234/234 testes passando
- ✅ Zero erros de lint/type checking
- ✅ 100% backward compatible

**Benefícios alcançados:**

1. **Desacoplamento:** Lógica não depende de implementação concreta
2. **Flexibilidade:** Aceita qualquer objeto compatível
3. **Testabilidade:** Mocks mais simples e diretos
4. **Documentação:** Contratos de interface explícitos
5. **Type Safety:** Mantida com strict mode
6. **Evolução:** Facilita mudanças futuras na implementação

**Código está pronto para merge em `qa/fixpack-04`**

---

## 🔗 Referências

- **DevLog anterior:** `devlog-main-screen-ms7.md`
- **PEP 544:** Protocols (Structural Subtyping)
- **PEP 585:** Type Hinting Generics In Standard Collections
- **Python Typing Best Practices:** Protocol vs ABC
- **Branch:** `qa/fixpack-04`
- **Base de código:** v1.3.28.zip
- **Python:** 3.13

---

## 📈 Evolução da Arquitetura

### MS-6: State Extraction
```
MainScreen (UI + Logic + State)
    ↓
Controller (Logic) + State (Dataclass)
```

### MS-7: Strict Type Checking
```
Controller (Logic, Strict Typed)
State (Dataclass, Strict Typed)
```

### MS-8: Protocol-Based Design
```
Protocol (Interface)
    ↓
Controller (Logic, accepts Protocol)
    ↓
State (Dataclass, implements Protocol)
```

**Próxima evolução (MS-9):**
```
UI (Tkinter, uses Protocols)
    ↓
Protocol (Interface)
    ↓
Controller (Logic)
    ↓
State (Dataclass)
```

---

## 💡 Exemplo de Uso

### Antes (acoplado):
```python
def processar_tela(state: MainScreenState) -> None:
    # Função só funciona com MainScreenState exata
    computed = compute_main_screen_state(state)
    print(f"Clientes visíveis: {len(computed.visible_clients)}")
```

### Depois (flexível com Protocol):
```python
def processar_tela(state: MainScreenStateLike) -> None:
    # Função aceita qualquer objeto com a interface
    computed = compute_main_screen_state(state)
    print(f"Clientes visíveis: {len(computed.visible_clients)}")

# Agora funciona com mock simples em testes:
class MockState:
    clients = []
    order_label = "Razão Social (A→Z)"
    filter_label = "Todos"
    search_text = ""
    selected_ids = set()
    is_online = True
    is_trash_screen = False

processar_tela(MockState())  # ✅ Funciona!
```

---

**Assinatura:**  
Refatoração MS-8 completada com sucesso. Camada headless da Main Screen agora usa Protocols para interfaces, permitindo structural subtyping e facilitando testes, mantendo 100% de compatibilidade e zero regressões.
