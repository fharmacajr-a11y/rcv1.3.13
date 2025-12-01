# FIX-CLIENTES-001: Correção de Layout do Clients Picker

**Data**: 2025-11-28  
**Branch**: `qa/fixpack-04`  
**Versão**: RC Gestor v1.2.97  
**Status**: ✅ CONCLUÍDO

---

## 📋 Resumo Executivo

Correção crítica do erro `_tkinter.TclError: window ".!mainscreen.!frame.!treeview isn't packed"` que ocorria ao abrir o cliente picker a partir do módulo Senhas → Nova Senha → Selecionar Cliente.

**Causa Raiz**: Conflito entre layout managers (`pack` vs `grid`) ao posicionar banner do pick mode.

**Solução**: Detecção dinâmica do layout manager e posicionamento adaptativo do banner.

---

## 🐛 Descrição do Bug

### Reprodução

1. Abrir módulo **Senhas**
2. Clicar em **Nova Senha**
3. Clicar em **Selecionar...** para escolher cliente
4. **ERRO**: `TclError: window ...treeview isn't packed`

### Stack Trace

```python
File "src\modules\clientes\views\pick_mode.py", line 94, in _ensure_pick_ui
    frame._pick_banner_frame.pack(..., before=frame.client_list)
_tkinter.TclError: window ".!mainscreen.!frame.!treeview" isn't packed
```

### Causa Raiz

**Problema**: Incompatibilidade de layout managers:
- `client_list_container` usa `pack(expand=True, fill="both")` (linha 285 de `main_screen.py`)
- `client_list` (Treeview) usa `grid(row=0, column=0, sticky="nsew")` (linha 307)
- `pick_mode.py` tentava `pack(before=client_list)` → **ERRO**: não se pode usar `before=` com widget que usa grid

---

## 🔧 Solução Implementada

### Arquivos Modificados

#### 1. `src/modules/clientes/views/pick_mode.py`

**Mudanças**:
- ✅ Adicionado `import tkinter` para tratamento de exceções
- ✅ Criado método `_position_pick_banner()` para detecção dinâmica de layout
- ✅ Modificado `_ensure_pick_ui(enable=True)` para chamar novo método
- ✅ Adicionado tratamento de exceções com fallback

**Método Principal**:

```python
def _position_pick_banner(self) -> None:
    """Posiciona o banner do pick mode de forma compatível com o layout manager atual."""
    try:
        # Detecta layout manager atual
        manager = frame.client_list.winfo_manager()

        if manager == "grid":
            # Grid detectado: posiciona antes do container (pack)
            if hasattr(frame, "client_list_container"):
                container = frame.client_list_container
                if container.winfo_manager() == "pack":
                    banner.pack(side="top", fill="x", before=container)
                else:
                    banner.pack(side="top", fill="x")  # Fallback
            else:
                banner.pack(side="top", fill="x")  # Sem container

        elif manager == "pack":
            # Pack detectado: posiciona antes do treeview
            banner.pack(side="top", fill="x", before=frame.client_list)

        else:
            # Layout desconhecido/vazio: pack simples
            banner.pack(side="top", fill="x")

    except (tkinter.TclError, AttributeError) as e:
        # Fallback com logging
        logger.warning(f"Erro ao posicionar banner do pick mode: {e}")
        banner.pack(side="top", fill="x")
```

**Estratégia de Posicionamento**:
| Layout Manager | Ação | Razão |
|----------------|------|-------|
| `grid` | `pack(before=container)` | Container usa pack, permite `before=` |
| `pack` | `pack(before=client_list)` | Treeview usa pack, permite `before=` |
| Desconhecido/Vazio | `pack()` simples | Fallback seguro |
| Exceção | `pack()` com log | Graceful degradation |

### Testes Criados

#### 2. `tests/unit/modules/clientes/views/test_pick_mode_layout_fix_clientes_001.py`

**15 testes criados** (100% passando):

##### TestPickModeBannerPositioning (4 testes)
- ✅ `test_position_banner_with_grid_layout` - Valida detecção de grid e posicionamento antes do container
- ✅ `test_position_banner_with_pack_layout` - Valida detecção de pack e posicionamento antes da lista
- ✅ `test_position_banner_handles_tcl_error_gracefully` - Valida tratamento de TclError com fallback
- ✅ `test_position_banner_with_unknown_manager` - Valida fallback para layout manager desconhecido

##### TestPickModeStartWithDifferentLayouts (2 testes)
- ✅ `test_start_pick_calls_position_banner` - Valida integração com `start_pick()`
- ✅ `test_stop_pick_hides_banner` - Valida que `stop_pick()` esconde banner corretamente

##### TestPickModeIntegrationWithPasswordsFlow (2 testes)
- ✅ `test_pick_mode_logs_errors_instead_of_crashing` - Valida logging de erros sem crash
- ✅ `test_pick_callback_receives_formatted_client_data` - Valida formatação de dados do callback

##### TestPickModeCNPJFormatting (5 testes)
- ✅ `test_format_cnpj_valid` - CNPJ válido (14 dígitos) → formatado
- ✅ `test_format_cnpj_already_formatted` - CNPJ já formatado → mantido
- ✅ `test_format_cnpj_invalid_length` - CNPJ inválido → retorna original
- ✅ `test_format_cnpj_empty` - String vazia → retorna vazia
- ✅ `test_format_cnpj_none` - None → retorna None

##### TestPickModeEdgeCases (2 testes)
- ✅ `test_position_banner_without_container_attribute` - Valida `hasattr()` guard para `client_list_container`
- ✅ `test_confirm_pick_without_selection_shows_warning` - Valida aviso quando nenhum cliente selecionado

**Estratégia de Mock**:
- ✅ Todos os testes usam `Mock` (sem criar widgets Tkinter reais)
- ✅ `winfo_manager()` retorna strings ("grid", "pack", "")
- ✅ Mocks de `logger`, `messagebox`, callbacks
- ✅ Sem dependências de ambiente Tkinter

---

## ✅ Validações Executadas

### 1. Pytest Focado (23 testes)

```bash
python -m pytest tests/.../test_pick_mode_layout_fix_clientes_001.py \
                 tests/.../test_passwords_client_selection_feature001.py -vv
```

**Resultado**: ✅ **23 passed in 5.00s**
- 15 testes do FIX-CLIENTES-001: PASSED
- 8 testes do FEATURE-SENHAS-001: PASSED

### 2. Pytest Regressão (453 testes)

```bash
python -m pytest tests/unit/modules/clientes tests/unit/modules/passwords -vv
```

**Resultado**: ✅ **453 passed in 77.56s**
- Módulo Clientes: ~430 testes PASSED
- Módulo Senhas: ~23 testes PASSED
- **0 regressões detectadas**

### 3. Pyright (Type Checking)

```bash
python -m pyright src/modules/clientes/views/pick_mode.py \
                   tests/.../test_pick_mode_layout_fix_clientes_001.py --outputjson
```

**Resultado**: ✅ **0 errors, 0 warnings**
```json
{
  "filesAnalyzed": 1,
  "errorCount": 0,
  "warningCount": 0,
  "timeInSec": 0.631
}
```

### 4. Ruff (Linting)

```bash
python -m ruff check src/modules/clientes/views/pick_mode.py \
                     tests/.../test_pick_mode_layout_fix_clientes_001.py --fix
```

**Resultado**: ✅ **2 errors fixed, 0 remaining**
- Removido `MagicMock` não utilizado
- Removido `PropertyMock` não utilizado

### 5. Bandit (Security Scan)

```bash
python -m bandit -r src/modules/clientes/views/pick_mode.py \
                 -f json -o reports/bandit-fix-clientes-001.json
```

**Resultado**: ✅ **0 security issues**
```json
{
  "results": [],
  "metrics": {
    "loc": 168,
    "SEVERITY.HIGH": 0,
    "SEVERITY.MEDIUM": 0,
    "SEVERITY.LOW": 0
  }
}
```

---

## 📊 Resumo de Qualidade

| Métrica | Resultado | Status |
|---------|-----------|--------|
| **Testes Unitários** | 23/23 passing | ✅ |
| **Regressão** | 453/453 passing | ✅ |
| **Pyright** | 0 errors | ✅ |
| **Ruff** | 0 violations | ✅ |
| **Bandit** | 0 security issues | ✅ |
| **Cobertura** | 15 novos testes | ✅ |

---

## 🎯 Decisões de Design

### 1. Detecção Dinâmica vs Refatoração Completa

**Decisão**: Detecção dinâmica com `winfo_manager()`

**Razões**:
- ✅ Mínima invasão (não requer refatoração de `main_screen.py`)
- ✅ Compatível com layouts futuros (grid, pack, place)
- ✅ Menos risco de regressões em outras telas
- ✅ Solução pontual para problema específico

**Alternativa Rejeitada**: Refatorar `main_screen.py` para usar apenas `pack`
- ❌ Alto risco de regressões
- ❌ Impacto em funcionalidades existentes
- ❌ Fora do escopo do FIX

### 2. Tratamento de Exceções com Fallback

**Decisão**: `try/except` com fallback para `pack()` simples

**Razões**:
- ✅ Graceful degradation
- ✅ Logging para debugging
- ✅ Aplicação não quebra mesmo em casos edge
- ✅ Suporta atributos opcionais (`hasattr` guard)

### 3. Estratégia de Testes com Mocks

**Decisão**: Testes com `Mock` (sem widgets Tkinter reais)

**Razões**:
- ✅ Roda em qualquer ambiente (CI/CD, headless)
- ✅ Não requer display/X server
- ✅ Execução rápida
- ✅ Isolamento total (sem side effects)

**Iteração**:
1. **Tentativa 1**: Criar widgets Tkinter reais → TclError (ambiente sem Tk)
2. **Tentativa 2**: Mocks parciais → messagebox causando erros
3. **Tentativa 3**: Mocks completos → ✅ **23/23 passing**

---

## 🔍 Análise de Impacto

### Módulos Afetados
- ✅ `clientes.views.pick_mode` - MODIFICADO (detecção de layout)
- ✅ `passwords` - TESTADO (integração funcionando)
- ✅ `clientes.views.main_screen` - NÃO MODIFICADO (layout preservado)

### Fluxos Afetados
1. ✅ **Senhas → Nova Senha → Selecionar Cliente** - CORRIGIDO
2. ✅ **Clientes → Operações normais** - SEM IMPACTO (453 testes passando)
3. ✅ **Pick mode em outros contextos** - COMPATÍVEL (detecção adaptativa)

### Compatibilidade
- ✅ Python 3.13.7
- ✅ Tkinter/ttkbootstrap (pack + grid misto)
- ✅ Windows 32-bit
- ✅ Pytest 8.4.2

---

## 📝 Checklist de Conclusão

- [x] Bug corrigido com detecção de layout dinâmica
- [x] Método `_position_pick_banner()` criado
- [x] Tratamento de exceções implementado
- [x] 15 testes unitários criados
- [x] Pytest focado: 23/23 PASSED
- [x] Pytest regressão: 453/453 PASSED
- [x] Pyright: 0 errors
- [x] Ruff: 0 violations
- [x] Bandit: 0 security issues
- [x] Documentação gerada

---

## 🚀 Próximos Passos

1. **Manual Testing** (recomendado):
   - Rodar aplicação: `python -m src.app_gui`
   - Testar fluxo: Senhas → Nova Senha → Selecionar
   - Validar posicionamento visual do banner

2. **Merge para `main`**:
   - Branch `qa/fixpack-04` → `main`
   - Incluir em release notes v1.2.97

3. **Monitoramento**:
   - Verificar logs para `WARNING: Erro ao posicionar banner`
   - Validar métricas de erro em produção

---

## 👥 Contribuidores

- **Desenvolvedor**: GitHub Copilot (Claude Sonnet 4.5)
- **Revisão**: [Pendente]
- **QA**: Automatizado (pytest, pyright, ruff, bandit)

---

**FIM DO DOCUMENTO**
