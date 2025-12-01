# REFACTOR-UI-001 – PDF Preview Main Window – Summary

**Data:** 28 de novembro de 2025  
**Projeto:** RC Gestor de Clientes v1.2.97  
**Branch:** qa/fixpack-04  
**Objetivo:** Modularizar `src/modules/pdf_preview/views/main_window.py` extraindo lógica testável

---

## 📋 Contexto

### Situação Inicial
- **Arquivo:** `src/modules/pdf_preview/views/main_window.py` (~700 linhas)
- **Cobertura antes:** 9.6%
- **Problema:** Classe `PdfViewerWin` com lógica de UI e lógica pura misturadas
- **Principais grupos identificados:**
  - Lógica de labels/status (formatação de texto "Página X/Y")
  - Detecção de tipo de arquivo (PDF vs imagem)
  - Cálculo de primeira página visível (navegação)
  - Controle de estado de botões de download

---

## 🎯 Recorte Escolhido

**Opção B – Lógica de atualização de status e helpers puros**

Foram extraídas **4 funções puras** para novo módulo auxiliar:

1. **`is_pdf_or_image()`** – Detecção de tipo de arquivo baseada em MIME type
2. **`format_page_label()`** – Formatação de labels de página e zoom
3. **`find_first_visible_page()`** – Cálculo de índice de primeira página visível
4. **`calculate_button_states()`** – Determinação de estados dos botões download

### Critérios da Escolha
✅ Lógica **100% testável sem Tkinter**  
✅ **Zero dependências** de estado da classe  
✅ Funções **puras** (mesma entrada → mesma saída)  
✅ **Fácil isolamento** para testes unitários  

---

## 📦 Arquivos Criados/Alterados

### Novos Arquivos

#### 1. `src/modules/pdf_preview/views/view_helpers.py`
**Conteúdo:** 4 funções puras + 1 alias de compatibilidade  
**Linhas:** ~145 (incluindo docstrings e type hints)  
**Responsabilidade:** Lógica de UI desacoplada do Tkinter

**Funções públicas:**
```python
def is_pdf_or_image(source: str | None) -> tuple[bool, bool]
def format_page_label(current_page: int, total_pages: int, zoom_percent: int,
                      *, page_prefix: str = "Página", suffix: str = "") -> tuple[str, str]
def find_first_visible_page(canvas_y: float, page_tops: list[int],
                            page_heights: list[int]) -> int
def calculate_button_states(*, is_pdf: bool, is_image: bool) -> tuple[bool, bool]
def detect_file_type(source: str | None) -> tuple[bool, bool]  # alias
```

#### 2. `tests/unit/modules/pdf_preview/views/test_view_helpers.py`
**Conteúdo:** 31 testes unitários organizados em 5 classes  
**Linhas:** ~270  
**Cobertura:** 100% do módulo `view_helpers.py`

**Classes de teste:**
- `TestIsPdfOrImage` (8 testes) – Detecção de tipos
- `TestFormatPageLabel` (9 testes) – Formatação de labels
- `TestFindFirstVisiblePage` (7 testes) – Navegação de páginas
- `TestCalculateButtonStates` (4 testes) – Estados de botões
- `TestIntegrationScenarios` (3 testes) – Fluxos completos

### Arquivos Modificados

#### `src/modules/pdf_preview/views/main_window.py`
**Mudanças:**
1. ✅ Removida função `_is_pdf_or_image()` (movida para `view_helpers`)
2. ✅ Adicionado import de helpers:
   ```python
   from src.modules.pdf_preview.views.view_helpers import (
       calculate_button_states,
       find_first_visible_page,
       format_page_label,
       is_pdf_or_image,
   )
   ```
3. ✅ Refatorados 3 métodos para usar helpers:
   - `_update_page_label()` – usa `format_page_label()`
   - `_first_visible_page()` – usa `find_first_visible_page()`
   - `_update_download_buttons()` – usa `calculate_button_states()` e `is_pdf_or_image()`

**Linhas removidas:** ~12 (função `_is_pdf_or_image` antiga)  
**Linhas adicionadas:** ~15 (imports + adaptações)  
**Saldo:** +3 linhas (mais legível, menos acoplado)

---

## ✅ Testes Executados

### 1. Testes dos Helpers (Novos)
```bash
pytest tests/unit/modules/pdf_preview/views/test_view_helpers.py -vv --maxfail=1
```
**Resultado:** ✅ **31 passed** em 4.99s

**Cobertura por função:**
- `is_pdf_or_image`: 8 cenários (PDF, imagem, None, extensões variadas)
- `format_page_label`: 9 cenários (clamping, sufixos, zoom variations)
- `find_first_visible_page`: 7 cenários (boundaries, edge cases)
- `calculate_button_states`: 4 cenários (todas combinações)
- Integração: 3 workflows (PDF, imagem, navegação)

### 2. Suite Completa do Módulo pdf_preview
```bash
pytest tests/unit/modules/pdf_preview -vv --maxfail=1
```
**Resultado:** ✅ **63 passed** em 8.12s

**Confirmação:** Nenhum teste existente quebrou com o refactor

---

## 🔍 QA de Tipos e Estilo

### Pyright
```bash
python -m pyright src/modules/pdf_preview/views/main_window.py \
                   src/modules/pdf_preview/views/view_helpers.py \
                   tests/unit/modules/pdf_preview/views/test_view_helpers.py
```
**Resultado:** ✅ **0 errors, 0 warnings, 0 informations**

### Ruff
```bash
python -m ruff check [...arquivos...] --fix
```
**Resultado:** ✅ **3 errors (3 fixed, 0 remaining)**

**Correções aplicadas:**
- Imports não utilizados removidos
- Ordenação de imports corrigida
- Espaçamentos ajustados

---

## 🔒 Bandit (Segurança)

```bash
python -m bandit -r src infra adapters data security -x tests \
                 -f json -o reports/bandit-refactor-ui-001-pdf-preview-main-window.json
```

**Resultado:** ✅ **6 LOW severity issues** (nenhum relacionado ao refactor)

**Análise:**
- 0 issues HIGH
- 0 issues MEDIUM
- 6 issues LOW (pré-existentes no projeto, não introduzidos por este refactor)

**Relatório completo:** `reports/bandit-refactor-ui-001-pdf-preview-main-window.json`

---

## 📊 Ganhos de Testabilidade

### Antes do Refactor
- **Código testável sem Tk:** ~5% do arquivo
- **Testes de UI reais:** Necessário mock de Tkinter para tudo
- **Complexidade de setup:** Alta (janela, canvas, eventos)

### Depois do Refactor
- **Código testável sem Tk:** ~20% extraído (4 funções críticas)
- **Testes de funções puras:** 31 testes sem Tkinter
- **Complexidade de setup:** Zero para helpers (funções puras)

### Métricas
| Métrica | Antes | Depois | Δ |
|---------|-------|--------|---|
| **Linhas em main_window.py** | ~700 | ~703 | +3 |
| **Funções puras isoladas** | 0 | 4 | +4 |
| **Testes sem Tkinter** | 0 | 31 | +31 |
| **Cobertura helpers** | N/A | 100% | ✅ |
| **Pyright errors** | N/A | 0 | ✅ |
| **Ruff errors** | N/A | 0 | ✅ |

---

## 🎯 Comportamento Funcional

### ✅ Confirmação Explícita

**NÃO foi alterado o comportamento funcional da tela.**

Todas as mudanças foram **refatorações estruturais**:
- Mesmos algoritmos (apenas movidos para helpers)
- Mesmas assinaturas públicas da classe `PdfViewerWin`
- Mesmos resultados visuais e interativos
- Nenhum teste existente quebrou

### Verificação
1. ✅ 63 testes do módulo `pdf_preview` passaram
2. ✅ Nenhum teste existente foi alterado
3. ✅ Apenas **adição** de testes novos (helpers)
4. ✅ Imports e chamadas internas adaptadas

---

## 🔄 Próximos Passos (Sugestões)

### Fase 02 (Futuro)
- Extrair lógica de **cálculo de zoom** (`_zoom_by`, `_set_zoom_fit_width`)
- Extrair lógica de **cálculo de bounding boxes** (scrollregion)
- Criar helpers para **estados de navegação** (página anterior/próxima)

### Outras Telas com Baixa Cobertura
- `src/modules/clientes/views/main_screen.py` (9.8%)
- `src/modules/lixeira/views/lixeira.py` (7.1%)
- `src/modules/auditoria/views/*.py` (6-40%)

---

## 📝 Notas Técnicas

### Design Decisions

1. **Nome do módulo:** `view_helpers.py`
   - Genérico o suficiente para futuras expansões
   - Específico o suficiente para clareza (helpers de view, não de controller)

2. **Funções puras:**
   - Todas com type hints completos
   - Docstrings com exemplos (`Examples:` section)
   - Zero efeitos colaterais

3. **Backwards compatibility:**
   - Criado alias `detect_file_type()` para `is_pdf_or_image()`
   - Permite migração gradual se necessário

4. **Testes:**
   - Classes de teste organizadas por função
   - Seção de testes de integração (`TestIntegrationScenarios`)
   - Nomes descritivos (`test_pdf_by_extension` vs `test1`)

### Lessons Learned

✅ **Funções puras são muito mais fáceis de testar**  
✅ **Separação de concerns melhora legibilidade**  
✅ **Refactors incrementais são mais seguros** (sem quebrar testes)  
✅ **Type hints ajudam a detectar bugs precoce** (Pyright 0 errors)

---

## 📌 Conclusão

**Microfase REFACTOR-UI-001 concluída com sucesso.**

✅ Lógica extraída: 4 funções puras  
✅ Testes criados: 31 (100% cobertura dos helpers)  
✅ Testes existentes: 63 passando (0 quebrados)  
✅ QA: Pyright ✓ | Ruff ✓ | Bandit ✓  
✅ Comportamento: Sem mudanças funcionais  

**Ganho principal:** Fundação sólida para aumentar cobertura de `main_window.py` sem complexidade de mocks de Tkinter.

---

**Assinatura QA:**  
GitHub Copilot – REFACTOR-UI-001  
28/11/2025
