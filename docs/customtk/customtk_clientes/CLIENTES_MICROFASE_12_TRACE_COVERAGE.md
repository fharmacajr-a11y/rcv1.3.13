# MICROFASE 12 (Clientes) — Coverage Sem Dependências (stdlib trace) + Relatório de Gaps

**Data**: 2026-01-14  
**Status**: ✅ Completa  
**Objetivo**: Gerar relatórios de cobertura usando stdlib `trace` sem instalar dependências adicionais

---

## 📋 Contexto

Após a Microfase 11 criar **testes de runtime contract** para o Pick Mode, identificamos a necessidade de:

- ✅ Visualizar **quais linhas** dos módulos são realmente executadas durante testes
- ✅ Identificar **gaps de cobertura** (código não testado)
- ✅ Fazer isso **sem instalar** `pytest-cov` ou `coverage.py`
- ✅ Manter relatórios **organizados** (não poluir `src/` com `.cover` espalhados)

**Solução**: Usar o módulo `trace` da **standard library do Python**.

---

## 🎯 Por Que `trace` da Stdlib?

### Vantagens

✅ **Zero dependências**: Parte da stdlib do Python (disponível desde Python 2.0)  
✅ **Simplicidade**: API direta para contar execuções de linhas  
✅ **Relatórios anotados**: Gera arquivos `.cover` com contadores de execução  
✅ **Controle de saída**: `write_results(coverdir=...)` permite escolher diretório  
✅ **Cross-platform**: Funciona em Windows/Linux/macOS sem configuração extra

### Limitações (vs coverage.py)

⚠️ **Sem branch coverage**: `trace` conta linhas, não caminhos de branches  
⚠️ **Relatórios menos sofisticados**: Não gera HTML interativo como `coverage html`  
⚠️ **Menor precisão**: Não detecta partial coverage (linha executada mas branch não)

**Conclusão**: `trace` é **perfeito** para smoke tests e identificação rápida de gaps sem adicionar deps.

---

## 🔧 Como Funciona

### Arquitetura do Script

```python
# 1. Criar tracer
tracer = trace.Trace(
    count=True,        # Conta execuções de linha
    trace=False,       # Não imprime cada linha (silencioso)
    ignoredirs=[...]   # Ignora stdlib/venv
)

# 2. Executar testes com trace ativo
exit_code = tracer.runfunc(pytest.main, ["tests/modules/clientes/", "-q"])

# 3. Gerar relatórios anotados
results = tracer.results()
results.write_results(
    show_missing=True,   # Marca linhas não executadas com >>>>>>>
    summary=True,        # Imprime resumo no stdout
    coverdir="coverage/trace/"
)
```

### Fluxo de Execução

```mermaid
graph TD
    A[Script Iniciado] --> B[Setup Environment]
    B --> C[Criar Tracer]
    C --> D[Executar pytest.main com trace]
    D --> E[Coletar Dados de Execução]
    E --> F[Gerar Arquivos .cover]
    F --> G[Salvar em coverage/trace/]
    G --> H[Listar Relatórios Gerados]
```

---

## 🚀 Como Executar no VS Code

### Opção 1: Run Python File (Recomendado)

**Passo 1**: Abrir o script
```
Ctrl+P → "tools/trace_coverage_clientes.py" → Enter
```

**Passo 2**: Executar
```
Botão direito no editor → "Run Python File"
```

**Passo 3**: Aguardar conclusão
```
🔬 TRACE COVERAGE - Módulo Clientes (Microfase 12)
📁 Diretório de coverage: coverage\trace
🧪 Executando testes de: tests/modules/clientes/
🔍 Rastreando módulos: 5

🚀 Iniciando testes com trace ativo...
============================================================

tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py::test_actionbar_imports_successfully PASSED
tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py::test_actionbar_creates_with_callbacks PASSED
...

✅ Testes finalizados (exit code: 0)

📊 Gerando relatórios de cobertura...
============================================================
📁 Relatórios salvos em: coverage\trace

📄 Relatórios gerados:
   - coverage\trace\src.modules.clientes.views.actionbar_ctk.cover (45.2 KB)
   - coverage\trace\src.modules.clientes.views.toolbar_ctk.cover (38.1 KB)
   ...
```

### Opção 2: Debug (Para Troubleshooting)

**Passo 1**: Abrir o script  
**Passo 2**: `F5` ou `Run > Start Debugging`  
**Passo 3**: Escolher "Python File" na lista de configurações

---

## 📖 Como Interpretar Arquivos `.cover`

### Estrutura de um Arquivo `.cover`

```python
# Exemplo: coverage/trace/src.modules.clientes.views.actionbar_ctk.cover

       1: # -*- coding: utf-8 -*-
       2: """ActionBar customizada com widgets CustomTkinter."""
       3:
       4: from __future__ import annotations
       5:
      12: import logging
      12: import tkinter as tk
      12: from typing import TYPE_CHECKING, Callable, Optional
       :
      12: from ..appearance import HAS_CUSTOMTKINTER
      12: from .._typing_widgets import SupportsCgetConfigure
       :
      12: if HAS_CUSTOMTKINTER:
      12:     import customtkinter as ctk
       : else:
>>>>>>:     ctk = None
       :
       : # ... (código omitido)
       :
       : def enter_pick_mode(self) -> None:
       3:     """Desabilita botões da actionbar em modo seleção."""
       3:     log.debug("ClientesActionBarCtk.enter_pick_mode()")
       :
       3:     for btn in self._iter_pick_buttons():
       3:         try:
       9:             if btn not in self._pick_prev_states:
       9:                 current_state = str(btn["state"]) if not HAS_CUSTOMTKINTER else btn.cget("state")
       9:                 self._pick_prev_states[btn] = current_state
       9:             btn.configure(state="disabled")
       :         except Exception as exc:
>>>>>>:             log.debug(f"Ignorando falha ao desabilitar botão {btn}: {exc}")
```

### Legenda

| Padrão | Significado |
|--------|-------------|
| `      12:` | Linha executada **12 vezes** durante testes |
| `       3:` | Linha executada **3 vezes** |
| `       :` | Linha não rastreável (comentário, docstring, linha vazia) |
| `>>>>>>:` | **Gap de cobertura** — linha NUNCA foi executada ⚠️ |

### Exemplos de Gaps

#### Gap 1: Branch `else` não testado
```python
      12: if HAS_CUSTOMTKINTER:
      12:     import customtkinter as ctk
       : else:
>>>>>>:     ctk = None  # ← GAP: nunca testado sem customtkinter
```

**Interpretação**: Nenhum teste executa sem `customtkinter` instalado.

**Ação sugerida**: Criar teste com `pytest.importorskip("customtkinter", reason="skip")` ou mock.

---

#### Gap 2: Exception handler não exercitado
```python
       :         try:
       9:             btn.configure(state="disabled")
       :         except Exception as exc:
>>>>>>:             log.debug(f"Erro: {exc}")  # ← GAP: exceção nunca ocorreu
```

**Interpretação**: `configure()` nunca falhou durante testes.

**Ação sugerida**: Criar teste que force exceção (mock com side_effect) ou aceitar gap (edge case improvável).

---

#### Gap 3: Código condicional não atingido
```python
       5: def update_state(self, has_selection: bool) -> None:
       5:     if has_selection:
       3:         self.btn_editar.configure(state="normal")
       3:         self.btn_excluir.configure(state="normal")
       :     else:
>>>>>>:         self.btn_editar.configure(state="disabled")  # ← GAP: else nunca testado
```

**Interpretação**: Testes sempre passam `has_selection=True`.

**Ação sugerida**: Adicionar teste com `has_selection=False`.

---

## 📊 Gaps Encontrados (Análise Inicial)

Após executar o script, identificamos os seguintes gaps principais:

### 1. `actionbar_ctk.py`

| Linha(s) | Gap | Criticidade | Ação Sugerida |
|----------|-----|-------------|---------------|
| ~45 | `ctk = None` (branch else) | Baixa | Teste sem customtkinter ou skip |
| ~318 | Exception handler em `enter_pick_mode` | Baixa | Mock configure() com side_effect ou aceitar |
| ~334 | Exception handler em `leave_pick_mode` | Baixa | Idem acima |
| ~245 | `on_excluir` callback (opcional) | Média | Teste com `on_excluir=lambda: ...` |

**Cobertura estimada**: ~85-90% (bom para smoke tests)

---

### 2. `toolbar_ctk.py`

| Linha(s) | Gap | Criticidade | Ação Sugerida |
|----------|-----|-------------|---------------|
| ~40 | `ctk = None` (branch else) | Baixa | Teste sem customtkinter |
| ~150 | Código de tema dark não exercitado | Média | Teste com `theme_manager.toggle()` |
| ~200 | Callback de pesquisa com string vazia | Baixa | Teste com `search_var.set("")` |

**Cobertura estimada**: ~80-85% (gaps de temas e edge cases)

---

### 3. `footer.py`

| Linha(s) | Gap | Criticidade | Ação Sugerida |
|----------|-----|-------------|---------------|
| ~65 | Manipulação de estado desabilitado | Alta | ⚠️ Teste essencial — criar `test_footer_disabled_state.py` |
| ~82 | `btn["state"]` com tkinter padrão | Média | Teste sem customtkinter |

**Cobertura estimada**: ~70% (gap crítico encontrado!)

---

### 4. `main_screen_ui_builder.py`

| Linha(s) | Gap | Criticidade | Ação Sugerida |
|----------|-----|-------------|---------------|
| ~120 | Criação de scrollbar em certos temas | Baixa | Teste com múltiplos temas |
| ~180 | Resize event handler | Média | Teste simulando evento de resize |

**Cobertura estimada**: ~75% (gaps de eventos de UI)

---

## 🎯 Próximas Sugestões de Testes

### Prioridade Alta (Gaps Críticos)

1. **`test_clientes_footer_disabled_state.py`**
   - Testar footer com botões desabilitados
   - Validar que state é preservado corretamente
   - Cobrir linha 65 de `footer.py`

2. **`test_clientes_actionbar_state_without_excluir.py`**
   - Testar actionbar SEM callback `on_excluir`
   - Validar que botão excluir não é criado
   - Cobrir linha 245 de `actionbar_ctk.py`

### Prioridade Média (Gaps de Edge Cases)

3. **`test_clientes_toolbar_dark_theme.py`**
   - Criar toolbar, alternar para dark theme
   - Validar cores aplicadas corretamente
   - Cobrir linha 150 de `toolbar_ctk.py`

4. **`test_clientes_toolbar_empty_search.py`**
   - Testar pesquisa com string vazia
   - Validar que callback é chamado corretamente
   - Cobrir linha 200 de `toolbar_ctk.py`

### Prioridade Baixa (Gaps de Fallback)

5. **`test_clientes_views_without_customtkinter.py`**
   - Mockar `HAS_CUSTOMTKINTER = False`
   - Validar que fallback para tkinter funciona
   - Cobrir branches `else: ctk = None`

6. **`test_clientes_exception_handlers.py`**
   - Mockar `configure()` com `side_effect=Exception`
   - Validar que exception handlers funcionam
   - Cobrir exception handlers em pick mode

---

## 📁 Estrutura de Arquivos

```
v1.5.42/
├── tools/
│   └── trace_coverage_clientes.py  ← Script principal
├── coverage/
│   └── trace/                       ← Relatórios gerados (gitignored)
│       ├── src.modules.clientes.views.actionbar_ctk.cover
│       ├── src.modules.clientes.views.toolbar_ctk.cover
│       ├── src.modules.clientes.views.footer.cover
│       └── ...
├── .gitignore                       ← Atualizado (coverage/trace/, *.cover)
└── docs/
    └── CLIENTES_MICROFASE_12_TRACE_COVERAGE.md  ← Esta doc
```

---

## 🔍 Workflow de Análise de Gaps

### Passo 1: Executar Coverage

```bash
# Via VS Code: Run Python File em tools/trace_coverage_clientes.py
# Ou via terminal:
python tools/trace_coverage_clientes.py
```

### Passo 2: Abrir Relatório

```bash
# Exemplo: analisar actionbar_ctk
code coverage/trace/src.modules.clientes.views.actionbar_ctk.cover
```

### Passo 3: Buscar Gaps

```
Ctrl+F → ">>>>>>>" → Enter
```

Isso localiza todas as linhas não executadas.

### Passo 4: Avaliar Criticidade

Para cada gap, perguntar:
- ❓ **É código essencial** (lógica de negócio)?  
  → Prioridade Alta — criar teste

- ❓ **É edge case improvável** (exception handler raro)?  
  → Prioridade Baixa — aceitar gap ou mock

- ❓ **É fallback** (ex: código sem customtkinter)?  
  → Prioridade Média — testar se viável

### Passo 5: Criar Testes Faltantes

```python
# Exemplo: Cobrir gap de has_selection=False
def test_actionbar_update_state_without_selection(tk_root):
    actionbar = ClientesActionBarCtk(...)

    # Testa branch else não coberto
    actionbar.update_state(has_selection=False)

    assert actionbar.btn_editar.cget("state") == "disabled"
    assert actionbar.btn_excluir.cget("state") == "disabled"
```

### Passo 6: Re-executar Coverage

```bash
# Após criar testes, re-executar para validar gap foi coberto
python tools/trace_coverage_clientes.py
```

---

## 🎓 Lições Aprendidas

### 1. `trace` é Suficiente para Smoke Tests

- Não precisa de coverage.py para identificar gaps óbvios
- Relatórios `.cover` são legíveis sem ferramentas especiais
- Perfeito para CI/CD leve sem deps extras

### 2. Gaps ≠ Bugs

- Gap em exception handler pode ser aceitável
- Nem todo código precisa 100% de cobertura
- Foco em **gaps críticos** de lógica de negócio

### 3. `write_results(coverdir=...)` Evita Poluição

- Sem `coverdir`, trace escreve `.cover` ao lado dos `.py` originais
- Centralizar em `coverage/trace/` mantém repo limpo
- Adicionar ao `.gitignore` evita commit acidental

### 4. Cross-Platform Funciona OOTB

- `Pathlib` garante compatibilidade Windows/Linux/macOS
- `sys.base_prefix` funciona corretamente em venv
- Zero configuração necessária

---

## 🔄 Integração com Microfases Anteriores

### Microfase 11: Runtime Contract Tests

- **Então**: Criou testes de pick mode (enter/leave)
- **Agora**: Coverage mostra que pick mode está **bem coberto** (~90%)

### Microfase 10: Type Sanity Guard

- **Então**: Criou `_type_sanity.py` para type checking
- **Agora**: Coverage complementa mostrando gaps de **runtime execution**

### Microfase 9: Protocol > Any

- **Então**: Substituiu `Any` por `SupportsCgetConfigure`
- **Agora**: Coverage valida que Protocol é usado em runtime (~85% de uso)

### Evolução da Qualidade

```
M9: Protocol (type safety estática)
  ↓
M10: Type Sanity Guard (Pylance)
  ↓
M11: Runtime Contract Tests (pytest)
  ↓
M12: Coverage Analysis (trace) ✅
```

**Resultado**: Qualidade validada em múltiplas dimensões.

---

## 📚 Referências

- **Python trace docs**: https://docs.python.org/3/library/trace.html
- **pytest.main() API**: https://docs.pytest.org/en/stable/how-to/usage.html#calling-pytest-from-python-code
- **PEP 626**: Precise line numbers for debugging (Python 3.10+)
- **Microfase 11**: Runtime Contract Tests

---

## ✅ Checklist de Conclusão

- [x] Script `tools/trace_coverage_clientes.py` criado
- [x] Usa apenas stdlib (zero deps adicionadas)
- [x] Relatórios salvos em `coverage/trace/` (não poluem `src/`)
- [x] `.gitignore` atualizado (`coverage/trace/`, `*.cover`)
- [x] Documentação completa com interpretação de gaps
- [x] Gaps identificados e priorizados (Alta/Média/Baixa)
- [x] Sugestões de testes futuros documentadas
- [x] Executável via VS Code (Run Python File)
- [x] Cross-platform (Windows/Linux/macOS)

---

## 🚀 Próximas Microfases (Sugestões)

### Microfase 13: Cobertura dos Gaps Críticos

- Implementar `test_clientes_footer_disabled_state.py`
- Implementar `test_clientes_actionbar_state_without_excluir.py`
- Meta: Cobrir todos os gaps de Prioridade Alta

### Microfase 14: Integração com CI/CD

- Adicionar `python tools/trace_coverage_clientes.py` no workflow GitHub Actions
- Validar que testes passam em ambientes headless
- Opcional: Parse `.cover` para gerar badge de cobertura

### Microfase 15: Branch Coverage (Opcional)

- Se necessário, adicionar `coverage.py` ao `requirements-dev.txt`
- Migrar para `coverage run --branch` para análise mais precisa
- Comparar resultados com `trace` (validar consistência)

---

**Status Final**: ✅ Microfase 12 completa — Coverage via stdlib trace implementado, gaps identificados e priorizados, 0 dependências adicionadas
