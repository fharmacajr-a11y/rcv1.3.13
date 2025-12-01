# FIX-CLIENTES-006: Garantir Texto Correto e Botões Desativados no Modo Seleção

**Status**: ✅ Concluído  
**Branch**: `qa/fixpack-04`  
**Data**: 2025-01-XX  
**Autor**: GitHub Copilot  

---

## 📋 Resumo

Correção de problemas de encoding (mojibake) nos textos do banner e botões do modo seleção de clientes, garantindo que:
1. O banner exiba corretamente: **"🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter"**
2. Os botões exibam **"✓ Selecionar"** e **"✖ Cancelar"** sem caracteres corrompidos
3. Todos os botões (footer + lixeira + menus superiores) estejam visivelmente desabilitados durante pick mode
4. Haja cobertura de testes para prevenir regressão

---

## 🐛 Problema Original

### Mojibake Detectado

O usuário reportou textos com caracteres corrompidos:

```
❌ Banner: "Òÿ' Modo seleÃ§ÃƒO: dÃª duplo clique..."
❌ Botão:  "âœ" Selecionar"
```

**Causa raiz**: Os textos estavam **hardcoded** no construtor de `MainScreenFrame.__init__()` em vez de usar as constantes UTF-8 corretas que já existiam no arquivo.

### Código Problemático

```python
# Linha 626 (ANTES - com mojibake)
self._pick_label: ttk.Label = tb.Label(
    self._pick_banner_frame,
    text="ðŸ" Modo seleÃ§Ã£o: dÃª duplo clique em um cliente ou pressione Enter",
    font=("", 10, "bold"),
    bootstyle="info-inverse",
)

# Linha 643 (ANTES - com mojibake)
self.btn_select: ttk.Button = tb.Button(
    self._pick_banner_frame,
    text="âœ" Selecionar",
    command=self._pick_controller.confirm_pick,
    state="disabled",
    bootstyle="success",
)
```

---

## ✅ Solução Implementada

### 1. Correção dos Textos Hardcoded

**Arquivo**: `src/modules/clientes/views/main_screen.py`

Substituímos os textos hardcoded pelas constantes UTF-8 que já existiam:

```python
# Constantes (já definidas nas linhas 101-103)
PICK_MODE_BANNER_TEXT = "🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter"
PICK_MODE_CANCEL_TEXT = "✖ Cancelar"
PICK_MODE_SELECT_TEXT = "✓ Selecionar"

# Linha 626 (DEPOIS - usando constante)
self._pick_label: ttk.Label = tb.Label(
    self._pick_banner_frame,
    text=PICK_MODE_BANNER_TEXT,  # ✅ Agora usa constante
    font=("", 10, "bold"),
    bootstyle="info-inverse",
)

# Linha 643 (DEPOIS - usando constante)
self.btn_select: ttk.Button = tb.Button(
    self._pick_banner_frame,
    text=PICK_MODE_SELECT_TEXT,  # ✅ Agora usa constante
    command=self._pick_controller.confirm_pick,
    state="disabled",
    bootstyle="success",
)

# Linha 634 (já estava correto - mantido)
btn_cancel_pick = tb.Button(
    self._pick_banner_frame,
    text=PICK_MODE_CANCEL_TEXT,  # ✅ Já usava constante
    bootstyle="danger-outline",
    command=self._pick_controller.cancel_pick,
)
```

**Método de Correção**:
- Criamos um script Python temporário que usou regex para encontrar e substituir os textos hardcoded pelas constantes
- O script foi executado e depois removido

---

### 2. Adição de Testes Abrangentes

**Arquivo**: `tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py`

Adicionamos duas novas classes de teste:

#### A. `TestPickModeBannerTextUsage` (3 testes)

Valida que o código-fonte usa as constantes corretas:

```python
def test_pick_label_source_code_uses_banner_text_constant(self) -> None:
    """Código-fonte do banner label deve usar PICK_MODE_BANNER_TEXT."""
    import inspect
    from src.modules.clientes.views.main_screen import MainScreenFrame

    source = inspect.getsource(MainScreenFrame.__init__)

    # Verificar que PICK_MODE_BANNER_TEXT é usado (não hardcoded)
    assert "text=PICK_MODE_BANNER_TEXT" in source

    # Verificar que NÃO há mojibake no código
    mojibake_patterns = [
        'text="ðŸ"',  # Emoji corrompido
        'text="Ã',    # Caracteres acentuados corrompidos
        'text="â',    # Checkmark corrompido
    ]
    for pattern in mojibake_patterns:
        assert pattern not in source
```

#### B. `TestPickModeButtonStatesInPickMode` (3 testes)

Valida que botões estão desabilitados durante pick mode:

```python
def test_footer_buttons_are_disabled_in_pick_mode(self) -> None:
    """Botões do footer devem estar desabilitados em pick mode."""
    frame = Mock(spec=["footer", "btn_lixeira", "_update_main_buttons_state", "_get_main_app"])
    footer = Mock()
    footer.btn_novo = Mock()
    footer.btn_editar = Mock()
    footer.btn_subpastas = Mock()
    footer.btn_enviar = Mock()
    # ... (setup completo)

    MainScreenFrame._enter_pick_mode_ui(frame)

    # Assert - todos os botões do footer devem estar desabilitados
    footer.btn_novo.configure.assert_called_with(state="disabled")
    footer.btn_editar.configure.assert_called_with(state="disabled")
    footer.btn_subpastas.configure.assert_called_with(state="disabled")
    footer.btn_enviar.configure.assert_called_with(state="disabled")
```

---

## 📊 Resultado dos Testes

### Testes do Pick Mode

```bash
$ python -m pytest tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py -v

====================== 26 passed in 4.34s ======================
```

**26 testes** incluindo os 6 novos testes de FIX-CLIENTES-006.

### Testes Completos do Módulo Clientes

```bash
$ python -m pytest tests/unit/modules/clientes/ -v

===================== 445 passed in 58.01s =====================
```

### Suite Completa de Testes

```bash
$ python -m pytest --maxfail=3 -x

2989 passed, 14 skipped, 1 warning in 855.57s (0:14:15)
Required test coverage of 25% reached. Total coverage: 57.14%
```

### Análise Estática

```bash
$ python -m pyright
0 errors, 0 warnings, 0 informations

$ python -m ruff check
All checks passed!
```

---

## 🔍 Arquivos Modificados

1. **`src/modules/clientes/views/main_screen.py`**
   - Linha 626: `text=PICK_MODE_BANNER_TEXT` (substituiu hardcoded)
   - Linha 643: `text=PICK_MODE_SELECT_TEXT` (substituiu hardcoded)

2. **`tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py`**
   - Adicionada classe `TestPickModeBannerTextUsage` (3 testes)
   - Adicionada classe `TestPickModeButtonStatesInPickMode` (3 testes)
   - Atualizado `__all__` para exportar novas classes

---

## 🎯 Cobertura de Testes

### Novos Testes Adicionados

| Classe de Teste | Testes | Objetivo |
|----------------|--------|----------|
| `TestPickModeBannerTextUsage` | 3 | Validar uso de constantes UTF-8 corretas |
| `TestPickModeButtonStatesInPickMode` | 3 | Validar desabilitação de botões em pick mode |
| **Total** | **6** | **Prevenir regressão de mojibake e UX** |

### Testes Existentes (mantidos)

| Classe de Teste | Testes | Status |
|----------------|--------|--------|
| `TestPickModeEnterExitUI` | 4 | ✅ Passando |
| `TestPickModeDoubleClickAndSelectButton` | 4 | ✅ Passando |
| `TestPickModeCancelButton` | 3 | ✅ Passando |
| `TestPickModeUIIntegration` | 4 | ✅ Passando |
| `TestPickModeTextConstants` | 3 | ✅ Passando |

**Total do arquivo**: 26 testes (20 existentes + 6 novos)

---

## 🔒 Garantias de Qualidade

### Anti-Regressão

1. **Testes de Código-Fonte**:
   - Validam que `text=PICK_MODE_BANNER_TEXT` está no código
   - Detectam se hardcoded é reintroduzido
   - Bloqueiam merge se mojibake for detectado

2. **Testes de Estado**:
   - Validam que `state="disabled"` é aplicado em pick mode
   - Verificam que `btn_novo`, `btn_editar`, `btn_subpastas`, `btn_enviar`, `btn_lixeira` são desabilitados
   - Confirmam que `app.set_pick_mode_active(True)` é chamado

3. **Testes de Constantes**:
   - Validam conteúdo UTF-8 correto (emoji 🔍, acentos corretos)
   - Detectam presença de mojibake (`Ã`, `Â`, etc.)
   - Garantem que constantes estão exportadas em `__all__`

---

## 📝 Checklist de Verificação

- [x] Textos do banner e botões corrigidos (sem mojibake)
- [x] Constantes UTF-8 aplicadas em todos os widgets
- [x] Botões do footer desabilitados em pick mode (`btn_novo`, `btn_editar`, `btn_subpastas`, `btn_enviar`)
- [x] Botão Lixeira desabilitado em pick mode
- [x] Menu Conversor PDF desabilitado em pick mode
- [x] Testes de código-fonte adicionados (3 testes)
- [x] Testes de estado de botões adicionados (3 testes)
- [x] Todos os 26 testes do pick mode passando
- [x] Todos os 445 testes do módulo clientes passando
- [x] Todos os 2989 testes da suite completa passando
- [x] Pyright: 0 erros, 0 warnings
- [x] Ruff: All checks passed
- [x] Cobertura de testes: 57.14% (acima de 25% requerido)

---

## 🎓 Lições Aprendidas

### 1. Encoding UTF-8 em Tkinter

**Problema**: Hardcoding de strings UTF-8 em código Python pode resultar em mojibake quando o arquivo é salvo/lido com encoding inconsistente.

**Solução**: Sempre usar constantes definidas uma vez no topo do módulo, garantindo encoding correto.

### 2. Testes de Código-Fonte

**Descoberta**: Usar `inspect.getsource()` permite validar que constantes estão sendo usadas, sem necessidade de instanciar widgets complexos.

**Vantagem**: Testes mais rápidos e menos frágeis (não dependem de Tk root, patches complexos, etc.)

### 3. Substituição Programática

**Método**: Usar scripts Python temporários com regex para substituir textos corrompidos é mais confiável que edição manual, especialmente quando o editor pode não mostrar os caracteres corrompidos corretamente.

---

## 🚀 Próximos Passos

1. ✅ Merge para `qa/fixpack-04` (quando aprovado)
2. ⏭️ Testar visualmente no app (confirmar emojis e acentos)
3. ⏭️ Considerar adicionar teste de integração visual (screenshot comparison) se regressões recorrentes forem detectadas

---

## 📚 Referências

- **FIX-CLIENTES-005**: Desabilitar botões durante pick mode (pré-requisito)
- **FEATURE-SENHAS-002**: Fluxo simplificado de senhas com pick mode
- **Constants definidas**: `src/modules/clientes/views/main_screen.py` linhas 101-103
- **Testes**: `tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py`

---

## ✅ Aprovação

**Validado por**: Testes automatizados (2989 testes passando, 0 erros pyright, ruff clean)  
**Pronto para merge**: ✅ Sim

---

**Fim do documento FIX-CLIENTES-006**
