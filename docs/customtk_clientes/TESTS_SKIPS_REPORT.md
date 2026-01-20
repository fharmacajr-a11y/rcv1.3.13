# Relatório de Testes Skipped (Pulados)

**Data**: 14 de janeiro de 2026  
**Workspace**: RC Gestor v1.5.42  
**Python**: 3.13.7  
**Pytest**: 8.4.2  
**Status**: ✅ Analisado e documentado

---

## 📊 Resumo Executivo

Este relatório analisa **todos os testes que são pulados (skipped)** no projeto, identifica os motivos e propõe ações para maximizar cobertura local sem quebrar CI/headless.

**Total de categorias de skip identificadas**: 5
- ✅ CustomTkinter não instalado (~15 testes)
- ✅ GUI não disponível (4+ testes com marker `@pytest.mark.gui`)
- ✅ Filelock não instalado (4 testes)
- ✅ ANVISA-only mode (7 testes)
- ✅ Platform-specific (2 testes)

---

## 🔍 Análise Detalhada por Categoria

### 1. CustomTkinter não instalado (~15 testes)

**Arquivos afetados**:
- `tests/modules/clientes/test_client_form_ctk_import_smoke.py` (4 testes)
- `tests/modules/clientes/test_clientes_modal_ctk_import_smoke.py` (4 testes)
- `tests/modules/clientes/test_client_form_ctk_create_no_crash.py` (2 testes)
- `tests/modules/clientes/test_clientes_modal_ctk_create_no_crash.py` (4 testes)
- `tests/modules/clientes/test_clientes_toolbar_ctk_visual_polish_smoke.py` (4 testes)
- `tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py` (7 testes)

**Condição de skip**:
```python
pytest.importorskip("customtkinter")
# ou
@pytest.mark.skipif(not HAS_CUSTOMTKINTER, reason="Requer customtkinter")
```

**O que testam**:
- **Imports**: Verificam que classes CTk podem ser importadas
- **Criação**: Verificam que widgets CTk podem ser instanciados sem crash
- **Toolbar**: Inicialização, cores, refresh dinâmico
- **ActionBar**: Callbacks, estados, cores
- **Modals**: Criação de dialogs (confirm/alert/error/info)
- **Forms**: ClientFormViewCTK e builders

**Motivo do skip**:
CustomTkinter é dependência opcional. App funciona com fallback para ttk/ttkbootstrap.

**Status atual**:
- ✅ **Local (Windows)**: CustomTkinter 5.2.2 instalado na venv → testes **PASSAM**
- ❌ **CI/CD**: Sem CustomTkinter → testes **SKIPPED** (esperado)

**Como rodar localmente**:
```bash
# Se CustomTkinter não estiver instalado:
pip install customtkinter==5.2.2

# Rodar testes CTk
pytest tests/modules/clientes/test_*ctk*.py -v
```

**Ação**: ✅ **NENHUMA** - Comportamento correto. `importorskip` garante skip automático quando pacote ausente.

---

### 2. GUI não disponível (4+ testes - marker `@pytest.mark.gui`)

**Arquivos afetados**:
- `tests/modules/clientes/test_clientes_modal_ctk_create_no_crash.py`
  - `test_clientes_modal_ctk_alert_no_crash`
  - `test_clientes_modal_ctk_error_no_crash`
  - `test_clientes_modal_ctk_info_no_crash`
  - `test_clientes_modal_ctk_confirm_no_crash`
- `tests/modules/clientes/test_client_form_ctk_create_no_crash.py`
  - `test_client_form_view_ctk_create_no_crash`
  - `test_client_form_ui_builders_ctk_create_widgets`

**Condição de skip**:
```python
@pytest.mark.gui
def test_clientes_modal_ctk_alert_no_crash():
    root = tk.Tk()  # Requer display
    ...
```

**O que testam**:
Testes que criam widgets Tkinter/CTk requerem display disponível (X11, DISPLAY, etc). Validam que:
- Widgets podem ser criados sem crash
- Janelas podem ser abertas e fechadas
- Não há memory leaks óbvios

**Motivo do skip**:
Ambientes headless (CI/CD sem GUI) não têm display. Testes falham com `TclError: no display name and no $DISPLAY environment variable`.

**Status atual**:
- ✅ **Local (Windows/Linux Desktop)**: Display disponível → testes **PASSAM**
- ❌ **CI/CD headless**: Sem display → testes devem ser **SKIPPED**

**Configuração** (já aplicada em pytest.ini):
```ini
markers =
    gui: Tests that require GUI/display (skip on headless CI)
```

**Como rodar**:
```bash
# Apenas testes GUI
pytest -m gui -v

# Excluir testes GUI (para CI)
pytest -m "not gui" -v
```

**Ação**: ✅ **JÁ CONFIGURADO** - Marker `@pytest.mark.gui` permite controle via `-m`.

---

### 3. Filelock não instalado (4 testes)

**Arquivos afetados**:
- `tests/utils/test_prefs.py` (linhas 144, 585, 597)
- `tests/unit/utils/test_prefs_legacy_fase14.py` (linha 88)
- `tests/unit/utils/test_prefs.py` (linha 612)

**Condição de skip**:
```python
@pytest.mark.skipif(not HAS_FILELOCK, reason="Requer filelock instalado")
# ou
if not HAS_FILELOCK:
    pytest.skip("filelock não disponível")
```

**O que testam**:
- Concorrência de leitura/escrita de preferências
- Lock de arquivos entre processos
- Cenários de race condition

**Motivo do skip**:
`filelock` é dependência opcional para testes de edge cases de concorrência. Não é crítico para funcionalidade core.

**Status atual**:
- ❓ **Local**: Depende se `filelock` está instalado
- ❌ **CI/CD**: Provavelmente skip

**Verificar instalação**:
```bash
pip show filelock
```

**Se ausente, instalar**:
```bash
pip install filelock
```

**Ação**: ✅ **OPCIONAL** - Se quiser testar concorrência local:
1. Instalar: `pip install filelock`
2. Testes passarão automaticamente
3. Considerar adicionar em `requirements-dev.txt`

**Prioridade**: 🟡 Média - Testes de edge case, não bloqueantes

---

### 4. ANVISA-only mode (7 testes desabilitados)

**Arquivo**:
- `tests/unit/modules/hub/test_dashboard_service.py`

**Testes afetados**:
- `test_recent_activity_includes_all_sections` (linha 941)
- `test_recent_activity_excludes_clientes_if_empty` (linha 1032)
- `test_recent_activity_orders_by_datetime` (linha 1088)
- `test_recent_activity_respects_max_items_per_section` (linha 1139)
- `test_recent_activity_handles_pagination_correctly` (linha 1168)
- `test_recent_activity_integrates_with_redis_cache` (linha 1231)
- `test_recent_activity_calculates_correct_datetime` (linha 1271)

**Condição de skip**:
```python
@pytest.mark.skip(reason="Disabled in ANVISA-only mode - recent_activity is empty")
```

**O que testam**:
Dashboard com atividades recentes de múltiplos módulos (Clientes, Sites, Equipamentos, etc).

**Motivo do skip**:
Sistema está configurado para modo ANVISA-only (funcionalidade específica de um módulo). Dashboard de atividades assume módulos não-ANVISA ativos.

**Status atual**:
- ❌ **Sempre skip**: Independente de ambiente
- 🔧 **Razão**: Lógica de negócio - modo operacional diferente

**Ação**: ✅ **INTENCIONAL** - Testes desabilitados por decisão de produto, não por limitação técnica.

**Notas**:
- Se modo ANVISA-only mudar no futuro, remover `@pytest.mark.skip`
- Alternativa: criar variant condicional baseado em config do app

**Prioridade**: 🔴 Baixa - Comportamento esperado do produto

---

### 5. Platform-specific (2 testes)

**Arquivo**:
- `tests/unit/modules/uploads/test_download_and_open_file.py`

**Testes afetados**:

1. **Windows-only** (linha 16):
```python
@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-only")
def test_download_and_open_file_windows():
    # Testa subprocess com start (Windows)
    ...
```

2. **Linux-only** (linha 55):
```python
@pytest.mark.skipif(
    sys.platform.startswith("win") or sys.platform == "darwin",
    reason="Linux-only"
)
def test_download_and_open_file_linux():
    # Testa xdg-open (Linux)
    ...
```

**O que testam**:
Comportamento específico de abrir arquivos baixados:
- Windows: `os.startfile()` ou `start` command
- Linux: `xdg-open`
- macOS: `open` (não testado atualmente)

**Motivo do skip**:
APIs e comandos diferem entre sistemas operacionais.

**Status atual**:
- ✅ **Windows local**: Windows-only **PASSA**, Linux-only **SKIP**
- ✅ **Linux CI**: Linux-only **PASSA**, Windows-only **SKIP**

**Ação**: ✅ **CORRETO** - Skips intencionais por plataforma.

---

## 🎯 Recomendações por Ambiente

### Para Desenvolvedor Local (Windows)

**Setup completo**:
```bash
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Instalar deps opcionais
pip install customtkinter==5.2.2 filelock

# Verificar
pip show customtkinter filelock
```

**Rodar todos os testes possíveis**:
```bash
pytest -v  # Rodará tudo exceto ANVISA-only e Linux-only
```

**Expectativa**:
- ✅ CustomTkinter tests: **PASS**
- ✅ GUI tests: **PASS**
- ✅ Filelock tests: **PASS** (se instalado)
- ⏭️ ANVISA-only: **SKIP** (intencional)
- ⏭️ Linux-only: **SKIP** (plataforma)

---

### Para CI/CD (Headless, Linux, sem CustomTkinter)

**Configuração recomendada**:
```bash
pytest -m "not gui" -v  # Pula testes que requerem display
```

**Expectativa**:
- ⏭️ CustomTkinter tests: **SKIP** (importorskip)
- ⏭️ GUI tests: **SKIP** (marker)
- ⏭️ Filelock tests: **SKIP** (não instalado)
- ⏭️ ANVISA-only: **SKIP** (intencional)
- ✅ Windows-only: **SKIP** (plataforma)
- ✅ Linux-only: **PASS** ✨
- ✅ Testes de lógica/negócio: **PASS** ✨

---

## 📋 Checklist de Validação

### Desenvolvedor Local (Windows com CustomTkinter)

- [ ] Ativar venv: `.venv\Scripts\Activate.ps1`
- [ ] Verificar Python: `python --version` (3.13+)
- [ ] Verificar CustomTkinter: `pip show customtkinter`
- [ ] Verificar filelock: `pip show filelock` (opcional)
- [ ] Rodar: `pytest tests/modules/clientes/ -v`
- [ ] Confirmar: CustomTkinter tests passam
- [ ] Confirmar: GUI tests passam
- [ ] Confirmar: Apenas ANVISA-only e Linux-only skipados

### CI/CD (Headless, Linux)

- [ ] Python 3.13+ instalado
- [ ] Sem CustomTkinter (intencional)
- [ ] Sem display (headless)
- [ ] Rodar: `pytest -m "not gui" -v`
- [ ] Confirmar: GUI tests skipados (marker)
- [ ] Confirmar: CustomTkinter tests skipados (importorskip)
- [ ] Confirmar: Testes core passam

---

## 📊 Tabela Resumo de Skips

| Categoria | Qtd | Local (Win+CTk) | CI (Linux) | Ação Recomendada |
|-----------|-----|-----------------|------------|------------------|
| CustomTkinter | ~15 | ✅ PASS | ⏭️ SKIP | Instalar localmente |
| GUI marker | 4+ | ✅ PASS | ⏭️ SKIP | Manter marker |
| Filelock | 4 | ⚠️ Opcional | ⏭️ SKIP | Instalar se quiser |
| ANVISA-only | 7 | ⏭️ SKIP | ⏭️ SKIP | Nenhuma - produto |
| Windows-only | 1 | ✅ PASS | ⏭️ SKIP | Nenhuma - OK |
| Linux-only | 1 | ⏭️ SKIP | ✅ PASS | Nenhuma - OK |

**Total**: ~32 skips potenciais dependendo do ambiente

---

## 🔧 Como Reduzir Skips Localmente

### 1. Instalar CustomTkinter ⭐
```bash
pip install customtkinter==5.2.2
```
**Reduz**: ~15 skips → Maior impacto!

### 2. Instalar Filelock
```bash
pip install filelock
```
**Reduz**: 4 skips

### 3. Ter Display Disponível
✅ **Windows**: Já tem (GUI nativa)  
✅ **Linux Desktop**: Já tem (X11/Wayland)  
❌ **Linux Server/CI**: Requer Xvfb ou skip com `-m "not gui"`

**Não é possível reduzir**:
- ANVISA-only (7) - decisão de produto
- Platform-specific (2) - dependente de OS

---

## 🎓 Lições Aprendidas

### ✅ Padrões Corretos de Skip

**`pytest.importorskip("package")`**:
```python
# ✅ Detecta dinamicamente se pacote está instalado
pytest.importorskip("customtkinter")
from customtkinter import CTkButton
```

**`@pytest.mark.skipif(condition, reason="...")`**:
```python
# ✅ Lógica condicional clara
@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-only")
def test_windows_specific():
    ...
```

**`@pytest.mark.gui`**:
```python
# ✅ Marker customizado para controle fino
@pytest.mark.gui
def test_create_window():
    root = tk.Tk()  # Requer display
    ...
```

### ❌ Anti-Patterns Evitados

**Não usar**:
```python
# ❌ Flag global pode ficar desatualizada
HAS_CUSTOMTKINTER = False  # Hard-coded!
if HAS_CUSTOMTKINTER:
    # Teste nunca roda mesmo com pacote instalado

# ❌ Import no topo falha antes do skip
import customtkinter  # ModuleNotFoundError antes do skip!
@pytest.mark.skipif(...)
def test_something():
    ...
```

**Usar**:
```python
# ✅ importorskip detecta dinamicamente
pytest.importorskip("customtkinter")
import customtkinter  # Só importa se skip não ativou
```

---

## 📚 Referências

- [pytest.importorskip docs](https://docs.pytest.org/en/stable/how-to/skipping.html#skipping-on-a-missing-import-dependency)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)
- [pytest.ini configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- [CustomTkinter docs](https://customtkinter.tomschimansky.com/)

---

## 🚀 Próximos Passos

### Curto Prazo (Opcional)
1. ✅ Adicionar `customtkinter` em `requirements-dev.txt` (se quiser cobertura local)
2. ✅ Adicionar `filelock` em `requirements-dev.txt` (se quiser testes de concorrência)
3. Documentar processo de setup no README para novos devs

### Médio Prazo
1. Considerar testes de smoke para modo ANVISA vs full
2. Avaliar se ANVISA-only deve ter suite própria
3. Adicionar teste Windows/Linux/macOS para abrir arquivos (expandir cobertura)

### Longo Prazo
1. CI matrix: Linux (sem CTk) + Windows (com CTk)
2. Testes de integração com Xvfb no CI Linux (GUI headless)
3. Cobertura de código condicional (branches de fallback)

---

**Conclusão**: Todos os skips identificados são **intencionais e corretos**. Comportamento varia conforme ambiente (local vs CI, Windows vs Linux, dependências opcionais instaladas). Não há "bugs" de skip, apenas decisões de design apropriadas para diferentes contextos de execução.

✅ **RELATÓRIO COMPLETO - TODOS OS SKIPS JUSTIFICADOS E DOCUMENTADOS**
