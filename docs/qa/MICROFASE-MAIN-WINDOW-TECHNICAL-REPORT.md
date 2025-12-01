# Relatório Técnico: Microfase ZUI-TEST-001 main_window.py

**Data:** 2025
**Módulo-alvo:** `src/modules/main_window/views/main_window.py`  
**Baseline:** 15.2% coverage (526 statements, 432 miss, 92 branches)  
**Meta original:** ≥85% coverage (ideal ≥90%)  
**Status final:** **IMPOSSÍVEL** sem ambiente GUI funcional

---

## 1. Sumário Executivo

A microfase para `main_window.py` **NÃO pôde ser concluída** com os mesmos critérios aplicados a `login_dialog.py` (96.9% coverage) devido a uma diferença fundamental:

- ✅ **login_dialog.py** → `tb.Toplevel` (diálogo) → Testável headless com mocks
- ❌ **main_window.py** → `tb.Window` (janela principal) → **Requer Tk root funcional**

### Tentativas Realizadas (Todas Falharam)

1. **Mock de tb.Window.__init__** → Falhou: `Style` object has no attribute `'theme'`
2. **Mock de todas as dependências** → Falhou: `ttk.Separator` requer tema válido
3. **Testes sem criar instância** → Conseguimos apenas 15.2% (import)
4. **Testes de inspeção de código** → Funcionou, mas não executa o código

---

## 2. Análise Técnica: Por Que main_window.py É Não-Testável?

###  Diagrama de Dependências

```
main_window.py (App class)
├── tb.Window (ttkbootstrap root window)
│   ├── tk.Tk() [REQUER DISPLAY/GUI]
│   ├── tb.Style(theme='cosmo')
│   │   └── theme.apply() [FALHA SE TEMA INVÁLIDO]
│   └── ttk.Separator [REQUER STYLE CONFIGURADO]
├── TopBar (componente GUI)
├── AppMenuBar (componente GUI)
├── NavigationController (com frames GUI)
├── StatusFooter (componente GUI)
├── StatusMonitor (threads + after())
├── SessionCache (OK - testável)
├── AuthController (OK - testável)
└── AppActions (OK - testável)
```

### Erro Root Cause

```python
# main_window.py linha ~182
self.sep_menu_toolbar = ttk.Separator(self, orient="horizontal")
# ↓
ttkbootstrap/style.py:726
if self.theme is None:  # ← FALHA: Style.theme não existe sem tema válido
    raise AttributeError('Style' object has no attribute 'theme')
```

**Conclusão:** `tb.Window` + `ttk.Separator` requerem tema válido → Mock não funciona.

---

## 3. Cobertura Alcançada

| Arquivo | Baseline | Final | Delta | Testes Criados |
|---------|----------|-------|-------|----------------|
| `main_window.py` | 15.2% | 15.2% | **+0.0pp** | 6 (inspeção) |

### Testes Criados (Limitados)

**Arquivo:** `tests/unit/modules/main_window/test_main_window_coverage.py`

```python
✅ test_import_app_class()  # Import bem-sucedido
✅ test_app_methods_exist()  # Métodos públicos existem
✅ test_constants_exist()  # Constantes existem
✅ test_app_navegacao_metodos_delegacao()  # Inspeção: delegam a nav
✅ test_app_acoes_metodos_delegacao()  # Inspeção: delegam a _actions
✅ test_app_cache_metodos_usam_session()  # Inspeção: usam _session
```

**Limitação:** Estes testes **não executam** o código do `__init__`, apenas inspecionam assinaturas.

---

## 4. Componentes TESTÁVEIS (Alternativas)

Embora `main_window.py` seja não-testável, os **componentes delegados** SÃO testáveis:

### 4.1 AppActions (`src/modules/main_window/app_actions.py`)

**Responsabilidade:** Lógica de ações (novo_cliente, editar_cliente, etc.)  
**Testável:** ✅ SIM (classe pura, sem GUI direta)  
**Cobertura potencial:** 85-95%  

```python
# Exemplo de teste
def test_app_actions_novo_cliente():
    mock_app = MagicMock()
    actions = AppActions(mock_app, logger=MagicMock())

    actions.novo_cliente()

    # Verificar que abre editor
    assert mock_app.show_main_screen.called
```

---

### 4.2 SessionCache (`src/modules/main_window/session_service.py`)

**Responsabilidade:** Cache de sessão (user, role, org_id)  
**Testável:** ✅ SIM (classe pura com `_session`)  
**Cobertura potencial:** 90-100%  

```python
# Exemplo de teste
def test_session_cache_get_user():
    mock_session = MagicMock()
    mock_session.get_user.return_value = {"uid": "123", "email": "test@example.com"}

    cache = SessionCache(mock_session)
    user = cache.get_user()

    assert user["uid"] == "123"
    mock_session.get_user.assert_called_once()
```

---

### 4.3 NavigationController (`src/core/navigation_controller.py`)

**Responsabilidade:** Navegação entre frames  
**Testável:** ⚠️ PARCIAL (depende de frames GUI, mas lógica é testável)  
**Cobertura potencial:** 60-75%  

---

## 5. Recomendações

### 5.1 CURTO PRAZO: Desistir de main_window.py

- ❌ **NÃO perseguir** 85-90% em `main_window.py`
- ✅ **Aceitar** 15.2% como baseline não-melhorável sem refatoração
- ✅ **Documentar** limitação técnica

### 5.2 MÉDIO PRAZO: Testar Componentes Delegados

**Microfases Alternativas (Ordenadas por Prioridade):**

1. ✅ **AppActions** (`app_actions.py`) → Meta: ≥85% coverage
2. ✅ **SessionCache** (`session_service.py`) → Meta: ≥90% coverage
3. ⚠️ **NavigationController** (`navigation_controller.py`) → Meta: ≥70% coverage

**Estimativa:** 3-4h para cobrir os 3 módulos com ≥80% médio

### 5.3 LONGO PRAZO: Refatorar main_window.py

Para tornar `main_window.py` testável, seria necessário:

1. **Extrair lógica de negócio** do `__init__` para métodos separados
2. **Injeção de dependências** para componentes GUI
3. **Factory pattern** para criar componentes mocáveis
4. **Separar** tb.Window em uma camada fina + controller testável

**Estimativa:** 8-12h de refatoração + testes

---

## 6. Pyright & Ruff nos Testes Criados

Embora a cobertura seja baixa, os testes criados são válidos:

### Pyright

```powershell
python -m pyright tests/unit/modules/main_window/test_main_window_coverage.py --outputjson
```

**Resultado Esperado:** 0 errors, 0 warnings

### Ruff

```powershell
python -m ruff check tests/unit/modules/main_window/test_main_window_coverage.py
```

**Resultado Esperado:** All checks passed

---

## 7. Comparação com login_dialog.py

| Aspecto | login_dialog.py | main_window.py |
|---------|-----------------|----------------|
| **Tipo** | tb.Toplevel (diálogo) | tb.Window (root window) |
| **Requer Tk root** | Não (usa parent) | **Sim (é o root)** |
| **Mock tb.__init__** | ✅ Funciona | ❌ Falha (tema) |
| **Baseline** | 12.5% | 15.2% |
| **Final** | 96.9% | 15.2% |
| **Testes** | 39 (executam código) | 6 (inspeção) |
| **Testável?** | ✅ SIM | ❌ NÃO (sem refatoração) |

---

## 8. Conclusão

**main_window.py não é testável com a abordagem headless** usada em `login_dialog.py` devido a:

1. ✅ `tb.Window` requer Tk root funcional
2. ✅ `ttk.Separator` + `tb.Style` requerem tema válido
3. ✅ Mock de `__init__` falha com `AttributeError: 'Style' object has no attribute 'theme'`

**Recomendação Final:**

- **Aceitar** 15.2% coverage em `main_window.py` como não-melhorável
- **Priorizar** AppActions e SessionCache para microfases futuras
- **Documentar** esta limitação para evitar perda de tempo futuro
- **Considerar** refatoração de longo prazo se cobertura de main_window for critical business requirement

---

## 9. Próximos Passos Sugeridos

1. ✅ **Microfase AppActions** (app_actions.py) → Meta: ≥85%
2. ✅ **Microfase SessionCache** (session_service.py) → Meta: ≥90%
3. ⚠️ **Avaliar** se main_window requer refatoração arquitetural

---

**Assinatura Técnica:**  
Este relatório documenta a tentativa de aplicar TEST-001 + QA-003 a `main_window.py` e as razões técnicas da impossibilidade sem refatoração.
