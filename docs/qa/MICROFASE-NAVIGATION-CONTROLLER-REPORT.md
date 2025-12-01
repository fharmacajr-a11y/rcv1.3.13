# MICROFASE: Cobertura + QA de `navigation_controller.py`

**Projeto:** RC - Gestor de Clientes v1.2.97  
**Data:** 28 de novembro de 2025  
**Responsável:** GitHub Copilot  
**Branch:** `qa/fixpack-04`

---

## 1. OBJETIVO DA MICROFASE

Elevar a cobertura de testes do módulo `src/core/navigation_controller.py` de **83.9%** para **≥70%** (meta ideal: ≥80-90%), garantindo validação de type hints (Pyright) e linting (Ruff) sem erros.

---

## 2. MÓDULOS TRABALHADOS

### 2.1 Módulo de Produção
- **Caminho:** `src/core/navigation_controller.py`
- **Linhas de código:** 79 linhas (46 statements, 10 branches)
- **Descrição:** Controlador de navegação entre frames Tkinter, com suporte a factory pattern para reutilização de frames

### 2.2 Módulo de Testes
- **Caminho:** `tests/core/test_navigation_controller.py`
- **Testes implementados:** 12 casos de teste

---

## 3. COBERTURA DE TESTES

### 3.1 Baseline vs Final

| Métrica           | Baseline (antes) | Final (depois) | Delta   |
|-------------------|------------------|----------------|---------|
| **Coverage %**    | 83.9%           | **100.0%**     | +16.1%  |
| **Statements**    | 46              | 46             | —       |
| **Miss**          | 8               | 0              | -8      |
| **Branches**      | 10              | 10             | —       |
| **BrPart**        | 1               | 0              | -1      |

### 3.2 Linhas/Branches Sem Cobertura

✅ **NENHUMA!** Cobertura de **100%** alcançada.

Todas as linhas anteriormente não cobertas foram testadas:
- **38-39:** Exceção em `lift()` quando frame é reutilizado
- **45:** Branch `hasattr(frame, "pack_info")` para decidir entre `pack()` e `place()`
- **48:** Exceção ao posicionar frame reutilizado
- **63-64:** Exceção ao destruir frame anterior
- **68-69:** Exceção ao fazer `pack()` no frame padrão

---

## 4. TESTES IMPLEMENTADOS

### 4.1 Quantidade de Testes

- **Antes:** 4 testes básicos
- **Depois:** 12 testes completos (+8 novos)

### 4.2 Principais Cenários Cobertos

#### **show_frame() - Modo sem factory (padrão)**
- ✅ Cria novo frame e destrói o anterior
- ✅ Posiciona frame com `pack(fill="both", expand=True)`
- ✅ Atualiza `_current` corretamente
- ✅ Trata exceção ao destruir frame anterior
- ✅ Trata exceção ao fazer `pack()` do novo frame
- ✅ Funciona quando frame anterior não tem método `destroy()`

#### **show_frame() - Modo com factory**
- ✅ Reutiliza frame retornado pela factory
- ✅ Faz `lift()` quando é o mesmo frame atual
- ✅ Posiciona novo frame reutilizado (diferentes do atual)
- ✅ Usa `pack()` quando frame tem `pack_info`
- ✅ Usa `place()` quando frame não tem `pack_info`
- ✅ Fallback para modo padrão quando factory retorna `None`
- ✅ Trata exceção em `lift()` do frame
- ✅ Trata exceção ao posicionar frame reutilizado
- ✅ Navegação entre frames diferentes usando factory

#### **current()**
- ✅ Retorna `None` inicialmente
- ✅ Retorna frame ativo após `show_frame()`

---

## 5. QA-003: TYPE HINTS + LINT

### 5.1 Pyright

**Comando executado:**
```bash
python -m pyright src/core/navigation_controller.py tests/core/test_navigation_controller.py
```

**Resultado:**
```
0 errors, 0 warnings, 0 informations
```

✅ **Status:** APROVADO

### 5.2 Ruff

**Comando executado:**
```bash
python -m ruff check src/core/navigation_controller.py tests/core/test_navigation_controller.py
```

**Resultado:**
```
All checks passed!
```

✅ **Status:** APROVADO

---

## 6. ALTERAÇÕES REALIZADAS

### 6.1 Código de Produção
- **Nenhuma alteração** foi necessária no módulo `navigation_controller.py`
- O código já estava bem estruturado com type hints completos e tratamento de exceções adequado

### 6.2 Código de Testes
- **Adicionados:** 8 novos casos de teste
- **Padrão utilizado:** Classes dummy de frames com comportamentos específicos para cada teste
- **Técnicas aplicadas:**
  - Frames com métodos que lançam exceções para testar tratamento de erros
  - Frames com e sem `pack_info` para testar diferentes caminhos de posicionamento
  - Frames sem método `destroy()` para testar verificação de `hasattr()`
  - Factory functions que retornam frames específicos ou `None`
  - Rastreamento de chamadas a métodos (`lift()`, `pack()`, `place()`)

---

## 7. ANÁLISE DO MÓDULO

### 7.1 NavigationController.__init__()
- **Parâmetros:**
  - `root`: Referência ao widget root Tkinter
  - `frame_factory`: Opcional, função para criar/reutilizar frames
- **Estado interno:**
  - `_root`: Root Tkinter
  - `_current`: Frame atualmente ativo (ou `None`)
  - `_factory`: Factory opcional

### 7.2 NavigationController.show_frame()
- **Estratégia com factory:**
  1. Chama `factory(frame_cls, kwargs)`
  2. Se retornar `None`, usa modo padrão
  3. Se retornar frame existente igual ao atual, apenas faz `lift()`
  4. Se retornar frame diferente, posiciona (`pack()` ou `place()`) e faz `lift()`
- **Estratégia sem factory (padrão):**
  1. Destrói frame anterior se existir
  2. Cria novo frame com `frame_cls(root, **kwargs)`
  3. Posiciona com `pack(fill="both", expand=True)`
  4. Atualiza `_current`

### 7.3 NavigationController._show_frame_default()
- **Comportamento:**
  - Método privado para criação "tradicional" de frames
  - Sempre destrói o frame anterior (se existir e tiver método `destroy()`)
  - Cria novo frame do zero
  - Ideal para navegação sem reutilização

### 7.4 NavigationController.current()
- **Retorno:** Frame atualmente visível ou `None`
- **Uso:** Permite verificar qual tela está ativa

---

## 8. DESAFIOS E SOLUÇÕES

### 8.1 Desafio: Testar branches de exceção
- **Problema:** Código tem múltiplos `try/except` defensivos
- **Solução:** Criadas classes dummy com métodos que lançam exceções controladas:
  - `FrameWithFailingLift`
  - `FrameWithFailingPack`
  - `FrameWithFailingDestroy`

### 8.2 Desafio: Testar branch `hasattr(frame, "pack_info")`
- **Problema:** Código decide entre `pack()` e `place()` baseado em `pack_info`
- **Solução:** Criado `FrameWithPlace` sem atributo `pack_info` para forçar uso de `place()`

### 8.3 Desafio: Testar factory com diferentes comportamentos
- **Problema:** Factory pode retornar frame novo, reutilizado ou `None`
- **Solução:** Implementadas factories customizadas para cada cenário:
  - Factory que sempre retorna mesma instância (reutilização)
  - Factory que retorna `None` (fallback)
  - Factory que retorna instâncias diferentes (navegação)

---

## 9. PADRÕES DE TESTE UTILIZADOS

### 9.1 Classe Dummy de Frame

```python
class DummyFrame:
    def __init__(self, root, **kwargs):
        self.root = root
        self.kwargs = kwargs
        self.packed = False
        self.destroyed = False

    def pack(self, **kwargs):
        self.packed = True

    def destroy(self):
        self.destroyed = True
```

### 9.2 Frame com Rastreamento de Chamadas

```python
lifted = {"count": 0}

class ReusableFrame(DummyFrame):
    def lift(self):
        lifted["count"] += 1
```

### 9.3 Factory Customizada

```python
def factory(cls, kwargs):
    if cls == Frame1:
        return frame1_instance
    elif cls == Frame2:
        return frame2_instance
    return None
```

---

## 10. CONCLUSÃO

### 10.1 Objetivos Alcançados

✅ **TEST-001:** Cobertura elevada de 83.9% para **100.0%** (meta: ≥70%, ideal: ≥80-90%)  
✅ **QA-003:** Pyright 0 erros / 0 warnings  
✅ **QA-003:** Ruff sem problemas  
✅ **Documentação:** Relatório técnico completo gerado

### 10.2 Métricas Finais

| Item                          | Valor      |
|-------------------------------|------------|
| Cobertura final               | **100.0%** |
| Testes implementados          | 12         |
| Pyright errors                | 0          |
| Pyright warnings              | 0          |
| Ruff issues                   | 0          |
| Linhas de produção alteradas  | 0          |

### 10.3 Próxima Sugestão

Com os módulos core principais cobertos, sugere-se focar em módulos de features/UI:

**📍 Próximas microfases sugeridas (em ordem de prioridade):**

1. **Módulos de features específicas:**
   - `src/features/*/services/` - Serviços de negócio
   - `src/modules/clientes/service.py` - Serviço de clientes
   - `src/modules/uploads/` - Sistema de uploads

2. **Módulos de infraestrutura:**
   - `src/infra/net_session.py` - Gerenciamento de sessão HTTP
   - `src/infra/healthcheck.py` - Health checks
   - `src/infra/settings.py` - Configurações

3. **Módulos de UI complexa (se viável sem GUI):**
   - `src/ui/dialogs/` - Diálogos específicos
   - `src/modules/*/views/` - Views de módulos

**Recomendação:** Atacar `src/modules/clientes/service.py` como próximo alvo, por ser um serviço crítico de negócio.

---

## 11. ANEXOS

### 11.1 Comando para Reproduzir Cobertura

```bash
python -m coverage erase
python -m coverage run -m pytest tests/core/test_navigation_controller.py -v
python -m coverage report -m src/core/navigation_controller.py
```

### 11.2 Testes Adicionados Nesta Microfase

1. `test_show_frame_with_factory_handles_lift_exception` - Exceção em lift()
2. `test_show_frame_with_factory_uses_place_when_no_pack_info` - Uso de place()
3. `test_show_frame_with_factory_handles_positioning_exception` - Exceção ao posicionar
4. `test_show_frame_default_handles_destroy_exception` - Exceção ao destruir
5. `test_show_frame_default_handles_pack_exception` - Exceção ao fazer pack()
6. `test_show_frame_without_destroy_method` - Frame sem destroy()
7. `test_show_frame_with_factory_different_frames` - Navegação entre frames
8. `test_show_frame_with_factory_reuses_and_positions` - Reutilização e posicionamento

### 11.3 Comparativo com Microfases Anteriores

| Módulo                    | Cobertura Baseline | Cobertura Final | Testes | Complexidade |
|---------------------------|-------------------|-----------------|--------|--------------|
| lixeira_service.py        | ~70%              | ~96%            | 30+    | Média        |
| notes_service.py          | ~85%              | ~98.6%          | 25+    | Média        |
| auth_bootstrap.py         | ~80%              | ~96%            | 20+    | Alta         |
| login_dialog.py           | ~60%              | ~97%            | 35+    | Alta         |
| app_actions.py            | 56.6%             | 96.6%           | 41     | Alta         |
| session_service.py        | 98.7%             | 100.0%          | 20     | Baixa        |
| **navigation_controller** | **83.9%**         | **100.0%**      | **12** | **Baixa**    |

**Observação:** NavigationController tinha boa cobertura inicial (83.9%) e estrutura simples, necessitando apenas 8 testes adicionais para alcançar 100%.

---

## 12. ARQUITETURA DO NAVIGATION CONTROLLER

### 12.1 Padrão de Design

O `NavigationController` implementa uma combinação de padrões:

- **Strategy Pattern:** A factory é injetada, permitindo diferentes estratégias de criação/reutilização
- **State Pattern:** Mantém estado do frame atual (`_current`)
- **Template Method:** `show_frame()` orquestra o fluxo, delegando para `_show_frame_default()` quando necessário

### 12.2 Vantagens da Arquitetura

1. **Desacoplamento:** Não conhece classes concretas de frames, trabalha com `Type[Any]`
2. **Flexibilidade:** Suporta tanto criação quanto reutilização de frames
3. **Resiliência:** Tratamento de exceções em todos os pontos críticos
4. **Testabilidade:** Fácil de testar com mocks e dummies

### 12.3 Casos de Uso

- **Sem factory:** Navegação tradicional com criação/destruição de frames
- **Com factory (singleton):** Reutilização de frames pesados (cache)
- **Com factory (pool):** Gerenciamento de múltiplas instâncias por tipo

---

**Status da Microfase:** ✅ **CONCLUÍDA COM SUCESSO**

**Aprovação para próxima fase:** Sim, pode-se iniciar trabalho em `src/modules/clientes/service.py` ou outro módulo prioritário
