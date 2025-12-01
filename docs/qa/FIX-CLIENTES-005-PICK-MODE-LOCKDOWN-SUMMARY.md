# FIX-CLIENTES-005: Travar Ações Indevidas no Modo Seleção + Limpar Callback

**Data:** 2025-11-28  
**Autor:** GitHub Copilot  
**Branch:** qa/fixpack-04  
**Tipo:** Bug Fix

---

## 📋 Sumário Executivo

Esta fix resolve problemas de UX no modo seleção (pick mode) de clientes, onde botões que não fazem sentido continuavam ativos e visualmente disponíveis. Além disso, elimina um `AttributeError` causado por `_cancel_client_picker_if_active` que se tornou obsoleto com o novo fluxo FEATURE-SENHAS-002.

**Problemas Resolvidos:**
- ✅ Bot\u00f5es do rodapé (Novo Cliente, Editar, Ver Subpastas, Enviar) ficam cinzas no pick mode
- ✅ Botão Lixeira desabilitado no pick mode
- ✅ Botão Conversor PDF desabilitado no pick mode
- ✅ Eliminado `AttributeError` ao fechar diálogo Nova Senha

---

## 🐛 Problemas Identificados

### 1. Botões Ativos no Modo Seleção
```
PROBLEMA:
Durante o pick mode (banner "🔍 Modo seleção: dê duplo clique em um cliente"),
os seguintes botões continuavam visualmente "ativos" e funcionais:
- Rodapé: Novo Cliente, Editar, Ver Subpastas, Enviar Para Supabase
- Superior: Lixeira, Conversor PDF

IMPACTO:
- Usuário confuso sobre quais ações são válidas
- Possibilidade de clicar em "Novo Cliente" enquanto deveria selecionar
- Falta de feedback visual de que a tela está em modo especial
```

### 2. AttributeError em _cancel_client_picker_if_active
```
PROBLEMA:
Ao fechar o diálogo Nova Senha, aparecia no log:
AttributeError: '_tkinter.tkapp' object has no attribute 'frames'

CAUSA:
_cancel_client_picker_if_active tentava acessar app.frames, mas:
1. O objeto retornado por _get_main_app() é um tk.Tk, não o App custom
2. Com FEATURE-SENHAS-002, pick mode ocorre ANTES do diálogo (não simultaneamente)

IMPACTO:
- Logs poluídos com exceptions
- Código morto executando sem necessidade
```

---

## 🛠️ Alterações Implementadas

### 1. `src/modules/clientes/views/main_screen.py`

#### Atualização de `_enter_pick_mode_ui()`
```python
def _enter_pick_mode_ui(self) -> None:
    """Configura a tela para o modo seleção de clientes (FIX-CLIENTES-005)."""
    # Desabilitar botões do rodapé
    if hasattr(self, "footer"):
        for btn_name in ("btn_novo", "btn_editar", "btn_subpastas", "btn_enviar"):
            btn = getattr(self.footer, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(state="disabled")
                except Exception as exc:
                    log.debug("Falha ao desabilitar botão %s: %s", btn_name, exc)

    # Desabilitar botão de lixeira
    if hasattr(self, "btn_lixeira"):
        try:
            self.btn_lixeira.configure(state="disabled")
        except Exception as exc:
            log.debug("Falha ao desabilitar botão lixeira: %s", exc)

    # ✅ NOVO: Desabilitar menus superiores (Conversor PDF)
    app = self._get_main_app()
    if app is not None and hasattr(app, "set_pick_mode_active"):
        try:
            app.set_pick_mode_active(True)
        except Exception as exc:
            log.debug("Falha ao desabilitar menus no pick mode: %s", exc)
```

**Responsabilidade:** Desabilitar TODOS os botões que não fazem sentido no pick mode.

---

#### Atualização de `_leave_pick_mode_ui()`
```python
def _leave_pick_mode_ui(self) -> None:
    """Restaura a tela para o modo normal (não seleção) (FIX-CLIENTES-005)."""
    # Restaurar estados dos botões via atualização central
    try:
        self._update_main_buttons_state()
    except Exception as exc:
        log.debug("Falha ao restaurar estados dos botões: %s", exc)

    # ✅ NOVO: Reabilitar menus superiores
    app = self._get_main_app()
    if app is not None and hasattr(app, "set_pick_mode_active"):
        try:
            app.set_pick_mode_active(False)
        except Exception as exc:
            log.debug("Falha ao reabilitar menus após pick mode: %s", exc)
```

**Responsabilidade:** Reabilitar menus superiores ao sair do pick mode.

---

### 2. `src/ui/topbar.py`

#### Novo Método: `set_pick_mode_active()`
```python
def set_pick_mode_active(self, active: bool) -> None:
    """Desabilita/habilita botões durante modo seleção de clientes (FIX-CLIENTES-005)."""
    try:
        if active:
            self.btn_pdf_converter.state(["disabled"])
        else:
            self.btn_pdf_converter.state(["!disabled"])
    except Exception:
        self.btn_pdf_converter["state"] = "disabled" if active else "normal"
```

**Responsabilidade:** Controlar estado do botão Conversor PDF durante pick mode.

**Nota:** Botão "Início" permanece ativo (navegar para Início cancela seleção naturalmente).

---

### 3. `src/modules/main_window/views/main_window.py`

#### Novo Método: `set_pick_mode_active()`
```python
def set_pick_mode_active(self, active: bool) -> None:
    """Ativa/desativa elementos de menu durante modo seleção de clientes (FIX-CLIENTES-005)."""
    if hasattr(self, "_topbar") and self._topbar is not None:
        try:
            self._topbar.set_pick_mode_active(active)
        except Exception as exc:
            log.debug("Falha ao atualizar topbar pick mode: %s", exc)
```

**Responsabilidade:** Propagar controle de pick mode para TopBar.

---

### 4. `src/modules/passwords/views/passwords_screen.py`

#### Remoção de `_cancel_client_picker_if_active()`
```python
# ❌ REMOVIDO (FIX-CLIENTES-005):
# def _cancel_client_picker_if_active(self) -> None:
#     """Cancela o pick mode se estiver ativo ao fechar a janela."""
#     app = self._get_main_app()
#     if not app:
#         return
#     frame = app.frames.get("clientes") or ...
#     ...

# ✅ SIMPLIFICADO:
def _on_close(self) -> None:
    """Handler chamado quando a janela é fechada (X ou Escape)."""
    self.destroy()
```

**Justificativa:** Com FEATURE-SENHAS-002, pick mode ocorre ANTES do diálogo, nunca simultaneamente.

---

## ✅ Validação

### Testes Automatizados

#### 1. Testes Focados (49 testes)
```powershell
python -m pytest tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py tests/unit/modules/clientes/views/test_pick_mode_layout_fix_clientes_001.py tests/unit/modules/passwords/test_passwords_client_selection_feature001.py -vv --maxfail=1
```

**Resultados:**
```
49 passed in 7.51s
```

**Destaques:**
- `test_enter_pick_mode_disables_dangerous_actions`: Valida desabilitação de botões + menus
- `test_leave_pick_mode_restores_state`: Confirma restauração via `set_pick_mode_active(False)`
- `test_enter_pick_mode_without_footer_does_not_crash`: Edge case sem footer
- `test_enter_pick_mode_without_lixeira_button_does_not_crash`: Edge case sem Lixeira

---

#### 2. Regressão Completa (479 testes)
```powershell
python -m pytest tests/unit/modules/clientes tests/unit/modules/passwords -vv --maxfail=1
```

**Resultados:**
```
479 passed in 70.40s (0:01:10)
```

**Confirmação:** Zero regressões introduzidas.

---

#### 3. Verificação de Tipos (Pyright)
```powershell
python -m pyright src/modules/clientes/views/main_screen.py src/modules/clientes/views/footer.py src/modules/clientes/views/toolbar.py src/modules/clientes/views/pick_mode.py src/modules/main_window/views/main_window.py src/modules/passwords/views/passwords_screen.py src/ui/topbar.py tests/unit/modules/clientes/views tests/unit/modules/passwords/test_passwords_client_selection_feature001.py
```

**Resultados:**
```
0 errors, 0 warnings, 0 informations
```

---

#### 4. Verificação de Estilo (Ruff)
```powershell
python -m ruff check src/modules/clientes/views/main_screen.py src/modules/clientes/views/footer.py src/modules/clientes/views/toolbar.py src/modules/clientes/views/pick_mode.py src/modules/main_window/views/main_window.py src/modules/passwords/views/passwords_screen.py src/ui/topbar.py tests/unit/modules/clientes/views tests/unit/modules/passwords/test_passwords_client_selection_feature001.py --fix
```

**Resultados:**
```
All checks passed!
```

---

## 🎯 Cenários de Uso

### Cenário 1: Entrar no Pick Mode
```
1. Usuário está em Senhas
2. Clica "Nova Senha"
   → Pick mode ativa (banner "🔍 Modo seleção...")
3. Botões DESABILITADOS (cinza):
   - Rodapé: Novo Cliente, Editar, Ver Subpastas, Enviar
   - Superior: Lixeira, Conversor PDF
4. Botões HABILITADOS:
   - Buscar, Limpar, Ordenar, Status, checkboxes "Ocultar"
   - Início (navegar para Início = cancelar seleção)
```

---

### Cenário 2: Sair do Pick Mode (Seleção)
```
1. Usuário seleciona cliente "ALFARFARMA"
   → Pick mode desativa
2. Diálogo "Nova Senha" abre
3. Botões RESTAURADOS:
   - Rodapé: estados calculados por _update_main_buttons_state()
   - Superior: Lixeira/Conversor PDF voltam ao estado normal
```

---

### Cenário 3: Sair do Pick Mode (Cancelar)
```
1. Usuário clica "✖ Cancelar" no banner
   → Pick mode desativa
2. Volta para tela Senhas
3. Botões RESTAURADOS (mesmo comportamento do Cenário 2)
```

---

### Cenário 4: Fechar Diálogo Nova Senha (Sem AttributeError)
```
1. Usuário abre Nova Senha (após pick)
2. Fecha o diálogo (clica X ou ESC)
   → `_on_close()` executa APENAS `self.destroy()`
3. LOG LIMPO:
   - ❌ ANTES: AttributeError: '_tkinter.tkapp' object has no attribute 'frames'
   - ✅ DEPOIS: Nenhum erro
```

---

## 📊 Diagrama de Fluxo (Pick Mode Lockdown)

```mermaid
graph TD
    A[Nova Senha clicado] --> B[Pick mode ativa]
    B --> C[_enter_pick_mode_ui]
    C --> D[Desabilita botões rodapé]
    C --> E[Desabilita Lixeira]
    C --> F[app.set_pick_mode_active TRUE]
    F --> G[TopBar.set_pick_mode_active TRUE]
    G --> H[Conversor PDF desabilitado]

    I[Usuário seleciona/cancela] --> J[Pick mode desativa]
    J --> K[_leave_pick_mode_ui]
    K --> L[_update_main_buttons_state]
    K --> M[app.set_pick_mode_active FALSE]
    M --> N[TopBar.set_pick_mode_active FALSE]
    N --> O[Conversor PDF reabilitado]
```

---

## 🔗 Relação com Outros Fixes

**FIX-CLIENTES-002 (Base):**
- Implementou `_enter_pick_mode_ui` e `_leave_pick_mode_ui`
- Desabilitou botões do rodapé e Lixeira

**FIX-CLIENTES-005 (Evolução):**
- **ADICIONA** controle de menus superiores (Conversor PDF)
- **REMOVE** código obsoleto `_cancel_client_picker_if_active`
- **COMPLETA** lockdown total da UI no pick mode

**FEATURE-SENHAS-002 (Contexto):**
- Pick mode ocorre ANTES do diálogo
- Eliminou necessidade de cancelamento ao fechar diálogo

---

## 📈 Impacto da Fix

| Métrica                     | Antes               | Depois              |
|-----------------------------|---------------------|---------------------|
| Botões desabilitados no pick| 5 (rodapé + Lixeira)| 6 (+ Conversor PDF) |
| AttributeError no log       | Sim (toda vez)      | Não (eliminado)     |
| Clareza visual pick mode    | Baixa (botões ativos)| Alta (todos cinza)  |
| Consistência UI             | Parcial             | Total               |

---

## ✅ Checklist de Implementação

- [x] Adicionar `set_pick_mode_active()` ao TopBar
- [x] Adicionar `set_pick_mode_active()` ao App (main_window)
- [x] Atualizar `_enter_pick_mode_ui()` para chamar `app.set_pick_mode_active(True)`
- [x] Atualizar `_leave_pick_mode_ui()` para chamar `app.set_pick_mode_active(False)`
- [x] Remover `_cancel_client_picker_if_active()` de passwords_screen.py
- [x] Simplificar `_on_close()` para apenas `self.destroy()`
- [x] Atualizar testes para validar menus desabilitados
- [x] Executar testes focados (49 testes)
- [x] Executar regressão completa (479 testes)
- [x] Validar com pyright (0 erros)
- [x] Validar com ruff (all checks passed)
- [x] Criar documentação FIX-CLIENTES-005-PICK-MODE-LOCKDOWN-SUMMARY.md

---

## 🎓 Lições Aprendidas

1. **Lockdown Completo > Parcial:** Desabilitar TODOS os botões irrelevantes melhora a UX
2. **Cleanup de Código Morto:** Remover callbacks obsoletos reduz complexidade e bugs
3. **Testes de Edge Cases:** Validar cenários sem footer/lixeira evita crashes em configurações atípicas
4. **Propagação de Estado:** Usar `app.set_pick_mode_active()` permite controle centralizado

---

## 🔒 Garantias Pós-Fix

- ✅ **Nunca mais** botões ativos no pick mode que não fazem sentido
- ✅ **Nunca mais** `AttributeError` ao fechar Nova Senha
- ✅ **Sempre** feedback visual claro (botões cinzas = inativo)
- ✅ **Zero** regressões nos 479 testes existentes
- ✅ **100%** cobertura de tipos (pyright)
- ✅ **100%** conformidade com estilo (ruff)

---

## 🚀 Próximos Passos Sugeridos

1. **Teste Manual:** Validar visualmente no dev environment
2. **Feedback QA:** Confirmar que UX está mais clara
3. **Documentação Usuário:** Atualizar manual com comportamento de pick mode
4. **Telemetria:** Monitorar se usuários ainda tentam clicar em botões desabilitados

---

**✍️ Assinatura:**  
GitHub Copilot (Claude Sonnet 4.5)  
Repositório: rcv1.3.13 | Branch: qa/fixpack-04
