# MICROFASE 19.4 — CONSOLIDAÇÃO DE SKIPs E RESOLUÇÃO DE XFAIL OBSOLETO

**Data:** 15 de janeiro de 2026  
**Contexto:** Microfase 19.3 concluída (8738 passed, 45 skipped, 1 xfailed, 11 warnings)  
**Objetivo:** Centralizar skips Python 3.13 e resolver xfail obsoleto sem quebrar nada

---

## 📊 RESUMO EXECUTIVO

| Métrica | Antes (19.3) | Depois (19.4) | Mudança |
|---------|-------------|---------------|---------|
| **Testes Passed** | 8738 | 8738 | ✅ Mantido |
| **Testes Skipped** | 45 | **46** | +1 (xfail→skip) |
| **Testes XFailed** | 1 | **0** | ✅ Resolvido |
| **Warnings** | 11 | 11 | ✅ Mantido |
| **Tempo** | ~77-93 min | ~95 min | Dentro da variação |

**✅ Conquistas:**
- ✅ Decorator centralizado `SKIP_PY313_TKINTER` criado
- ✅ 33+ testes consolidados usando decorator reutilizável
- ✅ XFAIL obsoleto convertido para SKIP permanente
- ✅ Melhor manutenibilidade (quando bug for corrigido, trocar em 1 lugar)

---

## 🎯 OBJETIVOS CUMPRIDOS

### A) Centralizar Condição de Skip Python 3.13 ✅

**Criado:** [tests/helpers/skip_conditions.py](tests/helpers/skip_conditions.py)

```python
SKIP_PY313_TKINTER = pytest.mark.skipif(
    sys.version_info >= (3, 13) and sys.platform == "win32",
    reason=(
        "Tkinter/ttkbootstrap + pytest em Python 3.13 no Windows pode causar "
        "'Windows fatal exception: access violation' (bug do runtime CPython, "
        "ver issues #125179 e #118973)"
    ),
)
```

**Benefícios:**
- ✅ Reason padronizado e completo (inclui referências aos issues)
- ✅ Fácil de atualizar quando bug for corrigido
- ✅ Documentação inline (docstring explica quando remover)
- ✅ Reutilizável em múltiplos arquivos de teste

---

### B) Aplicar Decorator nos Testes Afetados ✅

**Arquivos modificados:** 5

| Arquivo | Testes Afetados | Mudança |
|---------|----------------|---------|
| `test_clientes_theme_smoke.py` | 1 | @pytest.mark.skip → @SKIP_PY313_TKINTER |
| `test_clientes_toolbar_ctk_smoke.py` | 1 | @pytest.mark.skip → @SKIP_PY313_TKINTER |
| `test_client_form_ui_builders.py` | 27 | skip_tk_windows_313 → SKIP_PY313_TKINTER |
| `test_editor_cliente.py` | 5 | pytestmark skipif → SKIP_PY313_TKINTER |
| `test_notifications_button_smoke.py` | 4 | _skip_tkinter_windows → SKIP_PY313_TKINTER |

**Total consolidado:** ~38 testes usando decorator centralizado

**Padrões aplicados:**

```python
# Padrão 1: Import único
from tests.helpers.skip_conditions import SKIP_PY313_TKINTER

# Padrão 2: Uso direto em decorator
@SKIP_PY313_TKINTER
def test_my_gui_test():
    ...

# Padrão 3: Alias local (quando precisar manter compatibilidade)
skip_tk_windows_313 = SKIP_PY313_TKINTER

# Padrão 4: pytestmark (aplica a todo módulo)
pytestmark = SKIP_PY313_TKINTER
```

---

### C) Resolver XFAIL Obsoleto do Actionbar ✅

**Arquivo:** [tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py](tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py)

**Teste:** `test_actionbar_fallback_when_ctk_unavailable`

**Mudança:**
```python
# ANTES (Microfase 19.3):
def test_actionbar_fallback_when_ctk_unavailable(tk_root, monkeypatch):
    pytest.xfail(
        reason="Teste de fallback complexo de mockar sem quebrar imports. "
               "CustomTkinter agora é dependência obrigatória do projeto."
    )

# DEPOIS (Microfase 19.4):
@pytest.mark.skip(
    reason=(
        "CustomTkinter é dependência obrigatória do projeto (requirements.txt). "
        "Teste de fallback quando CTK indisponível não é mais aplicável. "
        "Mock complexo causava 'halted; None in sys.modules'. "
        "Mantido como referência histórica (código comentado abaixo)."
    )
)
def test_actionbar_fallback_when_ctk_unavailable(tk_root, monkeypatch):
    """[OBSOLETO] Testa fallback quando CustomTkinter não disponível.

    HISTÓRICO:
    Este teste era relevante quando CustomTkinter era opcional.
    Desde a Microfase 3, CustomTkinter tornou-se dependência obrigatória.

    PROBLEMA:
    Mock de sys.modules["customtkinter"] = None causava erro:
    "ModuleNotFoundError: __import__ halted; None in sys.modules"

    DECISÃO:
    Marcado como skip permanente (Microfase 19.4).
    Código preservado abaixo como referência histórica.
    """
    pass  # Skip - código comentado abaixo para referência
```

**Justificativa:**

1. **Por que não remover o teste completamente?**
   - Preserva histórico do projeto (quando CTK era opcional)
   - Documenta decisão de tornar CTK obrigatório
   - Mantém código de referência caso precise reverter no futuro

2. **Por que converter xfail → skip (ao invés de manter xfail)?**
   - xfail = "esperamos que falhe, mas pode passar" (confuso)
   - skip = "não executamos, motivo claro" (mais honesto)
   - Cenário não é mais testável (CTK sempre presente)

3. **Por que não tentar consertar o mock?**
   - Mock de `sys.modules["customtkinter"] = None` é problemático
   - Causava erro `halted; None in sys.modules`
   - Esforço não vale o custo (CTK é obrigatório mesmo)

---

## 📋 ARQUIVOS MODIFICADOS

### Criados (1 arquivo)

1. **`tests/helpers/skip_conditions.py`** — Novo módulo
   - Decorator `SKIP_PY313_TKINTER`
   - Outros decorators úteis (SKIP_NOT_LINUX, etc.)
   - Documentação inline completa

### Modificados (5 arquivos)

1. **`tests/modules/test_clientes_theme_smoke.py`**
   - Adicionado import: `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Substituído: `@pytest.mark.skip(reason="...")` → `@SKIP_PY313_TKINTER`
   - Linhas: ~7, ~73

2. **`tests/modules/test_clientes_toolbar_ctk_smoke.py`**
   - Adicionado import: `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Substituído: `@pytest.mark.skip(reason="...")` → `@SKIP_PY313_TKINTER`
   - Linhas: ~5, ~86

3. **`tests/unit/modules/clientes/forms/test_client_form_ui_builders.py`**
   - Adicionado import: `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Substituído: `skip_tk_windows_313 = pytest.mark.skipif(...)` → `skip_tk_windows_313 = SKIP_PY313_TKINTER`
   - Atualizado reason no pytest.skip() da fixture
   - Linhas: ~17, ~32-35

4. **`tests/unit/modules/clientes/test_editor_cliente.py`**
   - Removido: `import sys`
   - Adicionado: `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Substituído: `pytestmark = pytest.mark.skipif(...)` → `pytestmark = SKIP_PY313_TKINTER`
   - Linhas: ~1-15

5. **`tests/unit/ui/test_notifications_button_smoke.py`**
   - Removido: `import sys`
   - Adicionado: `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Substituído: `_skip_tkinter_windows = pytest.mark.skipif(...)` → `_skip_tkinter_windows = SKIP_PY313_TKINTER`
   - Linhas: ~10-19

6. **`tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py`**
   - Convertido: `pytest.xfail()` → `@pytest.mark.skip(reason=...)`
   - Atualizada docstring com histórico completo
   - Código de teste substituído por `pass` (código original comentado)
   - Linhas: ~177-220

---

## ✅ VALIDAÇÃO

### Comando Executado

```bash
python -m pytest -c pytest_cov.ini --no-cov -ra
```

### Resultado

```
8738 passed, 46 skipped, 11 warnings in 5707.51s (1:35:07)
```

### Comparação com Microfase 19.3

| Métrica | 19.3 | 19.4 | Status |
|---------|------|------|--------|
| Passed | 8738 | 8738 | ✅ OK |
| Skipped | 45 | 46 | ✅ OK (+1 do xfail→skip) |
| XFailed | 1 | 0 | ✅ Resolvido |
| Warnings | 11 | 11 | ✅ Mantido |

### Verificação dos Skips

**46 skips detalhados:**

| Categoria | Quantidade | Reason Padrão |
|-----------|-----------|---------------|
| Python 3.13 + Tkinter (bug CPython) | 38 | `SKIP_PY313_TKINTER` (centralizado) |
| ANVISA-only mode | 7 | `Disabled in ANVISA-only mode` |
| Linux-only | 1 | `Linux-only` |
| **Novo:** CTK fallback obsoleto | 1 | `CustomTkinter é dependência obrigatória` |
| **Total** | **46** | — |

---

## 📝 BENEFÍCIOS DA CONSOLIDAÇÃO

### 1. Manutenibilidade ✅

**Antes (19.3):**
- 33+ testes com reason hardcoded individual
- Variações no texto do reason (inconsistente)
- Difícil atualizar quando bug for corrigido

**Depois (19.4):**
- 1 único decorator em `skip_conditions.py`
- Reason padronizado e completo
- Trocar em 1 lugar, propaga para todos os testes

### 2. Documentação ✅

**Antes:**
```python
@pytest.mark.skip(reason="Python 3.13 bug")  # Vago
```

**Depois:**
```python
@SKIP_PY313_TKINTER  # Auto-documentado + reason detalhado
```

O decorator tem docstring explicando:
- O que é o bug
- Quando ocorre (plataforma + versão)
- Referências aos issues (#125179, #118973)
- **Quando remover** (quando bug for corrigido)

### 3. Consistência ✅

Todos os 38 testes afetados pelo bug Python 3.13 agora mostram a **mesma reason**:

```
Tkinter/ttkbootstrap + pytest em Python 3.13 no Windows pode causar
'Windows fatal exception: access violation' (bug do runtime CPython,
ver issues #125179 e #118973)
```

### 4. Rastreabilidade ✅

Quando o bug for corrigido:

```bash
# Encontrar todos os usos:
git grep "SKIP_PY313_TKINTER"

# Remover o decorator:
# 1. Apagar/comentar definição em skip_conditions.py
# 2. Rodar testes para verificar se passam
# 3. Remover imports se tudo OK
```

---

## 🔍 DECISÕES TÉCNICAS

### Por que não usar `pytestmark` em todos os arquivos?

**pytestmark aplica skip a TODO o módulo.**

- ✅ **Usamos em:** `test_editor_cliente.py` (todos os testes afetados)
- ❌ **Não usamos em:** Arquivos com mix de testes (alguns GUI, alguns não-GUI)

**Exemplo:**
```python
# test_clientes_theme_smoke.py tem:
# - 5 testes de import (não precisam skip)
# - 1 teste GUI (precisa skip)

# Solução: aplicar @SKIP_PY313_TKINTER só no teste GUI
```

### Por que manter sys.platform == "win32" no fixture?

Algumas fixtures fazem skip programático dentro do código:

```python
@pytest.fixture()
def tk_root() -> tk.Tk:
    if sys.platform == "win32" and sys.version_info >= (3, 13):
        pytest.skip("...reason...")  # Skip dinâmico
```

**Por quê?**
- Fixture pode ser usada por testes com e sem decorator
- Skip na fixture = fallback adicional (defesa em profundidade)
- Documentação melhorada: agora referencia `skip_conditions.SKIP_PY313_TKINTER`

---

## 🎯 QUANDO REMOVER OS SKIPS?

### Checklist para Remoção

Quando o bug CPython for corrigido, seguir esta ordem:

1. **Verificar correção upstream:**
   - ✅ CPython issue #125179 marcado como "closed"
   - ✅ CPython issue #118973 marcado como "closed"
   - ✅ Nova versão Python 3.13.x lançada com fix

2. **Testar localmente:**
   ```bash
   # Comentar temporariamente o decorator
   # SKIP_PY313_TKINTER = pytest.mark.skipif(False, reason="...")

   # Rodar testes que antes falhavam
   python -m pytest tests/modules/test_clientes_theme_smoke.py::test_create_search_controls_with_palette -v
   ```

3. **Se passarem:**
   - Remover definição de `SKIP_PY313_TKINTER` em `skip_conditions.py`
   - Remover imports `from tests.helpers.skip_conditions import SKIP_PY313_TKINTER`
   - Remover decorators `@SKIP_PY313_TKINTER`
   - Commit: `"Remove SKIP_PY313_TKINTER: bug CPython #125179 corrigido em Python 3.13.x"`

4. **Atualizar documentação:**
   - Microfase 19.3 (referência histórica: "Bug existia até Python 3.13.x")
   - Microfase 19.4 (adicionar nota: "Decorator removido em [data] após correção")

---

## 📊 IMPACTO NO PROJETO

### Curto Prazo

- ✅ Código mais limpo e consistente
- ✅ Skips bem documentados
- ✅ 0 xfails (era 1 na 19.3)
- ✅ Warnings mantidos em 11 (apenas informativos)

### Médio Prazo

- ✅ Fácil de manter até correção do bug
- ✅ Código de referência preservado (actionbar fallback)
- ✅ Padrão estabelecido para futuros skips

### Longo Prazo

- ✅ Quando bug for corrigido: trocar em 1 lugar, remove de todos os 38 testes
- ✅ Histórico documentado para futuras decisões arquiteturais

---

## 🏁 CONCLUSÃO

### Objetivos Cumpridos

| Tarefa | Status | Observação |
|--------|--------|------------|
| Centralizar skip Py3.13 | ✅ | `SKIP_PY313_TKINTER` em `skip_conditions.py` |
| Aplicar em testes afetados | ✅ | 38 testes consolidados |
| Resolver xfail obsoleto | ✅ | Convertido para skip permanente |
| Validar sem coverage | ✅ | 8738 passed, 46 skipped, 0 xfailed |
| Documentar microfase | ✅ | Este documento |

### Métricas Finais

✅ **8738 testes passando** (100% mantido)  
✅ **46 skips** (45 + 1 do xfail)  
✅ **0 xfails** (era 1 na 19.3)  
✅ **11 warnings** (apenas informativos, mantido)  
✅ **6 arquivos alterados** (1 novo + 5 modificados)

### Próximos Passos

1. ✅ Monitorar CPython issues #125179 e #118973
2. ✅ Quando corrigido, usar checklist de remoção
3. ✅ Continuar com microfases de correção de type checking (1007 erros Pyright)

---

**Microfase 19.4 concluída com sucesso! 🎉**

**Documento gerado em:** 15 de janeiro de 2026  
**Versão do projeto:** v1.5.42  
**Python:** 3.13  
**Sistema:** Windows
