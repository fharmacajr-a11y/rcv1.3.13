# REFACTOR-UI-005 – PDF Preview views/main_window.py – Fase 02

**Data**: 2025-11-28  
**Autor**: GitHub Copilot (Claude Sonnet 4.5)  
**Projeto**: RC Gestor de Clientes v1.2.97  
**Branch**: `qa/fixpack-04`  

---

## 📋 Resumo Executivo

Segunda fase de refatoração do módulo `pdf_preview` (`src/modules/pdf_preview/views/main_window.py`), focada em **lógica de cálculos de zoom**. Extraídas **4 funções puras** para `view_helpers.py` com **52 testes** abrangentes em `test_view_helpers_fase02.py`.

**Total acumulado do módulo**: 31 testes (Fase 01) + 52 testes (Fase 02) = **83 testes** em `view_helpers`.

---

## 🎯 Objetivos da Fase 02

1. ✅ Extrair lógica pura de **cálculos de zoom** de `main_window.py`
2. ✅ Criar funções testáveis sem dependências de Tkinter
3. ✅ Desenvolver **52 testes** cobrindo cenários de zoom (steps, fit-width, anchor, threshold)
4. ✅ Validar com Pyright, Ruff e Bandit (0 erros)
5. ✅ Manter **zero mudanças de comportamento** (regressão: 115 passed)

---

## 🔧 Recorte Escolhido: Zoom Calculations

### Funções Extraídas (4 novas)

| Função | Responsabilidade | LOC |
|--------|-----------------|-----|
| `calculate_zoom_step` | Calcula novo zoom após scroll/wheel steps (com clamp) | ~15 |
| `calculate_zoom_fit_width` | Calcula zoom para fit-to-width no canvas | ~12 |
| `calculate_zoom_anchor` | Calcula fração de ancoragem (fx, fy) para zoom centrado no cursor | ~18 |
| `should_apply_zoom_change` | Determina se mudança de zoom é significativa (threshold) | ~5 |

**Total**: ~50 LOC de lógica pura extraída.

---

## 🧪 Testes Desenvolvidos

### Arquivo: `tests/unit/modules/pdf_preview/views/test_view_helpers_fase02.py`

**Total de testes**: 52

#### Distribuição por função:

1. **TestCalculateZoomStep** (11 testes):
   - Zoom in/out (single/multiple steps)
   - Clamp em min/max zoom
   - Custom min/max/step
   - Steps fracionários
   - Precisão de arredondamento

2. **TestCalculateZoomFitWidth** (13 testes):
   - Fit exato (com/sem gap)
   - Zoom out (página grande)
   - Zoom in (página pequena)
   - Clamp em min/max
   - Custom gap/min/max
   - Edge cases: page_width zero/negativo, gap > canvas

3. **TestCalculateZoomAnchor** (11 testes):
   - Ancoragem em centro, cantos (0,0 / 1,1)
   - BBox offset (não começa em 0,0)
   - BBox degenerado (largura/altura zero)
   - Cursor fora do BBox (clamp em 0.0/1.0)
   - BBox com coordenadas negativas

4. **TestShouldApplyZoomChange** (10 testes):
   - Mudanças significativas/insignificantes
   - Custom threshold
   - Boundary exato no threshold

5. **TestZoomIntegrationScenarios** (7 testes):
   - Workflow completo: wheel zoom in/out
   - Fit-width workflow
   - Clamp limits workflow
   - Negligible change workflow
   - Resize window + fit-width
   - Anchor at edge cases
   - Multi-step zoom sequence

---

## ✅ Validações

### Pytest

```bash
python -m pytest tests\unit\modules\pdf_preview\views\test_view_helpers_fase02.py -v --maxfail=1
# ========== 52 passed in 7.78s ==========
```

### Regressão (Módulo Completo)

```bash
python -m pytest tests\unit\modules\pdf_preview -v --maxfail=1
# ========== 115 passed in 15.52s ==========
```

**Breakdown**:
- `test_pdf_download_service_fase50.py`: 8 passed
- `test_pdf_preview_utils.py`: 14 passed
- `test_pdf_raster_service_fase51.py`: 10 passed
- `test_view_helpers.py` (Fase 01): 31 passed
- `test_view_helpers_fase02.py` (Fase 02): 52 passed

### Pyright

```bash
python -m pyright src\modules\pdf_preview\views\view_helpers.py tests\unit\modules\pdf_preview\views\test_view_helpers_fase02.py
# 0 errors, 0 warnings, 0 informations
```

### Ruff

```bash
python -m ruff check src\modules\pdf_preview\views\view_helpers.py tests\unit\modules\pdf_preview\views\test_view_helpers_fase02.py
# All checks passed!
```

### Bandit

```bash
python -m bandit -c .bandit -r src\modules\pdf_preview\views\view_helpers.py
# No issues identified. (222 LOC)
```

---

## 📊 Métricas

| Métrica | Valor |
|---------|-------|
| **Funções extraídas** | 4 (Fase 02) + 5 (Fase 01) = **9 totais** |
| **Testes criados** | 52 (Fase 02) |
| **Testes acumulados** | 83 (31 F01 + 52 F02) |
| **Testes módulo total** | 115 |
| **LOC helpers (total)** | ~222 |
| **Taxa de sucesso** | 100% (115/115) |
| **Erros Pyright** | 0 |
| **Erros Ruff** | 0 |
| **Issues Bandit** | 0 |

---

## 🔄 Padrão de Nomenclatura

**Diferença em relação a fases anteriores**:
- **Lixeira** (REFACTOR-UI-004): usou sufixos `_fase01.py` / `_fase02.py` para separar arquivos de testes.
- **PDF Preview** (REFACTOR-UI-001 + UI-005): usa `test_view_helpers.py` (Fase 01) e `test_view_helpers_fase02.py` (Fase 02).

**Decisão**: Manter consistência dentro do módulo `pdf_preview` (helpers compartilham `view_helpers.py`, testes separados por fase).

---

## 🧩 Funções Detalhadas

### 1. `calculate_zoom_step`

**Assinatura**:
```python
def calculate_zoom_step(
    current_zoom: float,
    wheel_steps: int | float,
    *,
    min_zoom: float = 0.2,
    max_zoom: float = 6.0,
    step: float = 0.1,
) -> float:
```

**Uso em main_window.py**: `_zoom_by`, `_zoom_image_by`

**Testes**: 11 (incluindo clamp, custom params, rounding)

---

### 2. `calculate_zoom_fit_width`

**Assinatura**:
```python
def calculate_zoom_fit_width(
    canvas_width: int,
    page_width: int,
    *,
    min_zoom: float = 0.2,
    max_zoom: float = 6.0,
    gap: int = 16,
) -> float:
```

**Uso em main_window.py**: `_set_zoom_fit_width`

**Testes**: 13 (incluindo edge cases: gap > canvas, page_width zero/negativo)

---

### 3. `calculate_zoom_anchor`

**Assinatura**:
```python
def calculate_zoom_anchor(
    event_x: float,
    event_y: float,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
```

**Uso em main_window.py**: `_zoom_by` (cálculo de `fx`, `fy` para manter ponto sob cursor)

**Testes**: 11 (incluindo bbox degenerado, cursor fora do bbox)

---

### 4. `should_apply_zoom_change`

**Assinatura**:
```python
def should_apply_zoom_change(
    old_zoom: float,
    new_zoom: float,
    *,
    threshold: float = 1e-9,
) -> bool:
```

**Uso em main_window.py**: `_zoom_by` (evitar reflow desnecessário)

**Testes**: 10 (incluindo custom threshold, boundary cases)

---

## 🎨 Exemplos de Testes

### Teste de Clamp (Zoom Step)

```python
def test_clamp_at_max_zoom(self):
    """Deve clampar no máximo (6.0) quando exceder."""
    result = calculate_zoom_step(5.9, 5)
    assert result == 6.0
```

### Teste de Edge Case (Fit Width)

```python
def test_zero_page_width_returns_min(self):
    """Deve retornar min_zoom quando page_width = 0 (evita divisão por zero)."""
    result = calculate_zoom_fit_width(800, 0)
    assert result == 0.2
```

### Teste de Integração (Workflow)

```python
def test_wheel_zoom_in_workflow(self):
    """Simula zoom in com mouse wheel."""
    old_zoom = 1.0
    new_zoom = calculate_zoom_step(old_zoom, 3)
    assert new_zoom == 1.3

    should_apply = should_apply_zoom_change(old_zoom, new_zoom)
    assert should_apply is True

    fx, fy = calculate_zoom_anchor(400, 300, (0, 0, 800, 600))
    assert fx == 0.5
    assert fy == 0.5
```

---

## 🔍 Observações Técnicas

### Decisões de Design

1. **Clamp embutido**: Todas as funções de cálculo incluem clamp interno para evitar valores fora dos limites.
2. **Threshold para float comparison**: `should_apply_zoom_change` usa `1e-9` para evitar floating-point precision issues.
3. **Anchor clamp**: `calculate_zoom_anchor` clamp fx/fy em [0.0, 1.0] para evitar valores negativos ou > 1.

### Casos Degenerados Tratados

- **BBox com largura/altura zero** (evita divisão por zero)
- **page_width zero/negativo** (retorna min_zoom)
- **gap > canvas_width** (garante largura efetiva >= 1)
- **Cursor fora do BBox** (clamp em 0.0/1.0)

---

## 🚀 Próximas Fases Potenciais

### Recortes não extraídos (candidatos para Fase 03):

1. **Page Navigation Logic**:
   - `_on_page_up`, `_on_page_down`, `_on_home`, `_on_end`
   - Lógica de navegação de páginas (next/prev/first/last)

2. **Page List Transformations**:
   - Construção de lista de thumbnails
   - Ordenação/filtro de páginas

3. **Scroll/Pan Calculations**:
   - Cálculo de viewport bounds
   - Pan delta calculations

---

## ✅ Conclusão

✅ **Fase 02 concluída com sucesso**:
- 4 funções puras extraídas
- 52 testes criados (100% passing)
- 0 erros de QA (Pyright/Ruff/Bandit)
- Regressão limpa (115 passed)

**Total acumulado `view_helpers.py`**: 9 funções, 83 testes, 222 LOC.

**Status**: ✅ Pronto para merge/commit.

---

## 📚 Referências

- **REFACTOR-UI-001**: PDF Preview Fase 01 (31 testes)
- **REFACTOR-UI-002**: Clientes main_screen_helpers (35 testes)
- **REFACTOR-UI-003**: Hub hub_screen_helpers (42 testes)
- **REFACTOR-UI-004**: Lixeira Fase 01+02 (93 testes totais)

---

**Documento gerado automaticamente**  
**Timestamp**: 2025-11-28 18:46 UTC-3
