# GUI Tests - Notas de Execução

**Versão:** v1.4.72  
**Data:** 20 de dezembro de 2025

---

## 🎯 Como Habilitar GUI Tests

Por padrão, os testes de interface gráfica (GUI) ficam **skipped** (pulados) para evitar crashes durante a execução da suíte de testes.

### Variáveis de Ambiente

Para executar os GUI tests, defina as seguintes variáveis de ambiente:

```bash
# Windows PowerShell
$env:RC_RUN_GUI_TESTS = "1"
$env:RC_RUN_PDF_UI_TESTS = "1"

# Linux/macOS
export RC_RUN_GUI_TESTS=1
export RC_RUN_PDF_UI_TESTS=1
```

### Execução

```bash
# Com variáveis de ambiente definidas
pytest tests/gui_legacy/
pytest tests/unit/modules/pdf_preview/views/
```

---

## ⚠️ Problemas Conhecidos

### Python 3.13 + Windows + Tkinter/ttkbootstrap

**Sintoma:** Access violation (crash fatal) durante execução de testes GUI  
**Plataforma:** Windows  
**Python:** 3.13+  
**Bibliotecas:** tkinter, ttkbootstrap

**Detalhes Técnicos:**
- Bug conhecido do runtime Python 3.13 em Windows
- Ocorre especialmente com `element_create` do ttkbootstrap
- Erro: `Windows fatal exception: access violation`

**Issues de Tracking:**
- CPython #125179 - Tkinter crash em Python 3.13
- CPython #118973 - ttkbootstrap element_create access violation

**Workarounds:**
1. **Recomendado:** Manter testes GUI skipped por padrão (configuração atual)
2. **Alternativa:** Rodar GUI tests em Python 3.11 ou 3.12 (downgrade temporário)
3. **Alternativa:** Executar app GUI manualmente para validação visual

---

## 📊 Estatísticas de Skipped Tests

### Última Contagem (pytest_skips_markers_FINAL.txt)

```
16 passed, 91 skipped, 7513 deselected in 24.86s
```

### Categorização

| Categoria | Quantidade | % | Motivo |
|-----------|------------|---|--------|
| **Python 3.13 + Tkinter bug** | 89 | 98% | CPython #125179, #118973 |
| **GUI tests (env var)** | 14 | 15% | RC_RUN_GUI_TESTS=1 requerido |
| **Optional deps** | 9 | 10% | py7zr, python-dotenv não instalados |
| **Platform-specific** | 1 | 1% | Linux-only test (Windows atual) |

**Nota:** Algumas categorias se sobrepõem (GUI tests também sofrem do bug Tkinter).

---

## 📂 Módulos Afetados

### GUI Tests (RC_RUN_GUI_TESTS=1)

Localizados em `tests/gui_legacy/`:
- `test_auditoria_main_frame_fase01.py`
- `test_auth_bootstrap_gui.py`
- `test_clientes_client_form_fase01.py`
- `test_clientes_forms_prepare_gui.py`
- `test_clientes_main_screen_fase01.py`
- `test_hub_screen_fase01.py`
- `test_lixeira_view_fase01.py`
- `test_main_window_view_fase01.py`
- `test_pdf_preview_main_window_fase01.py`
- `test_ui_components_clients_treeview.py`

Testes de LoginDialog:
- `test_login_dialog_focus.py`
- `test_login_dialog_style.py`
- `test_login_dialog_window_state.py`

### Python 3.13 + Tkinter Bug (89 testes)

**Integration Tests:**
- `tests/integration/modules/clientes/forms/test_client_form_integration_fase01.py` (28 testes)

**Unit Tests:**
- `tests/unit/modules/clientes/forms/test_client_form_adapters.py` (14 testes)
- `tests/unit/modules/clientes/forms/test_client_form_ui_builders.py` (24 testes)
- `tests/unit/modules/clientes/test_editor_cliente.py` (5 testes)
- `tests/unit/modules/pdf_preview/views/test_view_main_window_contract_fasePDF_final.py` (6 testes)
- `tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py` (3 testes)
- `tests/unit/modules/tasks/views/test_task_dialog.py` (9 testes)

---

## 🔧 Comandos de Diagnóstico

### Ver todos os skipped tests com detalhes

```bash
python -m pytest -m "skip or skipif" -rA --tb=no
```

### Filtrar apenas GUI tests

```bash
python -m pytest -m "skip or skipif" -k "gui" -rA --tb=no
```

### Rodar smoke tests (sem GUI)

```bash
pytest -q tests/unit/core/auth/test_auth.py
pytest -q tests/unit/utils/test_utils_validators_fase38.py
pytest -q tests/unit/core/services/test_clientes_service_fase60.py
pytest -q tests/unit/core/search/test_search_fase61.py
pytest -q tests/unit/modules/uploads/test_uploads_service_fase62.py
pytest -q tests/unit/modules/uploads/test_uploads_validation_fase63.py
pytest -q tests/unit/modules/uploads/test_uploads_repository_fase64.py
```

---

## 📖 Referências

### Documentação Interna
- [pytest_skips_markers_FINAL.txt](pytest_skips_markers_FINAL.txt) - Lista completa de skipped tests
- [SKIPPED_AUDIT.md](SKIPPED_AUDIT.md) - Auditoria completa de testes pulados
- [CODEX_CLEANUP_SKIPPEDS_2025-12-20.md](CODEX_CLEANUP_SKIPPEDS_2025-12-20.md) - Relatório de limpeza

### Issues Externas
- [CPython #125179](https://github.com/python/cpython/issues/125179) - Tkinter crash Python 3.13
- [CPython #118973](https://github.com/python/cpython/issues/118973) - ttkbootstrap access violation

---

## ✅ Recomendações

### Para Desenvolvimento Local
1. **Não** tente rodar GUI tests em Python 3.13 no Windows
2. Use smoke tests direcionados para validação rápida
3. Execute app GUI manualmente para validação visual quando necessário

### Para CI/CD
1. Manter GUI tests skipped por padrão
2. Considerar job separado com Python 3.11/3.12 para GUI tests (opcional)
3. Priorizar testes unitários headless (business logic)

### Para Testes de Aceitação
1. Executar app GUI compilado (.exe) manualmente
2. Seguir checklist de validação visual
3. Testar em ambiente representativo (Windows 10/11)

---

**Status:** ✅ GUI tests skipped intencionalmente (Python 3.13 bug)  
**Impacto:** Nenhum - lógica de negócio testada por testes unitários headless
