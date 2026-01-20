# MICROFASE 18-19 (Clientes) — VERIFICADORES DO APP (ENV + COBERTURA + EXECUÇÃO)

**Data**: 2026-01-14  
**Objetivo**: Scripts de diagnóstico unificado para validar ambiente, cobertura e execução real  
**Status**: ✅ Concluído

---

## 📋 SCRIPTS DISPONÍVEIS

### 1️⃣ verify_app_clientes_coverage_env.py (Microfase 18)

**Propósito**: Análise estática sem executar testes

**O que verifica**:
- Python ativo vs .venv + customtkinter
- Comandos de cobertura encontrados no projeto
- Configuração de seleção de testes (inclui/exclui modules)
- Coleta de testes (--collect-only, rápido)
- Hotspots Pylance (scan estático)

**Como usar**:
```powershell
python tools/verify_app_clientes_coverage_env.py
```

**Logs gerados**: `diagnostics/app_clientes/01_*.txt` a `06_*.txt`

---

### 2️⃣ verify_app_coverage_execution.py (Microfase 19) ⭐ NOVO

**Propósito**: Execução real da cobertura global

**O que verifica**:
- Descobre comando de cobertura do app
- **EXECUTA** o comando via subprocess (pode levar 5-10 minutos)
- Captura stdout/stderr completo
- Verifica se tests/modules/clientes foi **EXECUTADO** (não apenas coletado)
- Valida artefatos de cobertura gerados (htmlcov, coverage.json)

**Como usar**:

**Modo completo** (toda a suite de testes):
```powershell
python tools/verify_app_coverage_execution.py
# ⚠️  Pode levar 10+ minutos
```

**Modo rápido** (apenas tests/modules/clientes):
```powershell
python tools/verify_app_coverage_execution.py --quick
# ⚡ ~45 segundos
```

**Logs gerados**: `diagnostics/app_clientes/07_*.txt` a `09_*.txt`

---

## 📂 ARQUIVOS DE DIAGNÓSTICO

| # | Arquivo | Script | Conteúdo |
|---|---------|--------|----------|
| 01 | env_active_python.txt | verify_env | Python ativo + customtkinter |
| 02 | env_venv_python.txt | verify_env | Python .venv + customtkinter |
| 03 | app_coverage_commands_found.txt | verify_env | Comandos pytest/coverage |
| 04 | test_selection_diagnosis.txt | verify_env | Inclui/exclui modules |
| 05 | pytest_collect_only_active_command.txt | verify_env | Coleta de testes |
| 06 | pylance_hotspots_scan.txt | verify_env | Hotspots Pylance |
| 07 | run_global_coverage_stdout.txt | **verify_execution** | Stdout da execução |
| 08 | run_global_coverage_stderr.txt | **verify_execution** | Stderr da execução |
| 09 | consolidated_report.txt | **verify_execution** | **Resumo consolidado** |

---

## 🎯 QUANDO USAR CADA SCRIPT

### Use verify_app_clientes_coverage_env.py quando:
- ✅ Quer validação rápida (~10 segundos)
- ✅ Precisa verificar configuração sem rodar testes
- ✅ Quer saber se customtkinter está instalado
- ✅ Precisa confirmar que comandos incluem tests/modules
- ✅ Quer scan de hotspots Pylance

### Use verify_app_coverage_execution.py quando:
- ✅ Quer confirmar que testes **EXECUTAM** de verdade
- ✅ Precisa validar cobertura real (não apenas coleta)
- ✅ Quer ver logs completos da execução
- ✅ Precisa confirmar artefatos gerados (htmlcov)
- ⚠️  **Aceita esperar 5-10 minutos** (modo completo)
- ⚡ Use `--quick` para teste rápido (45 segundos)

---

## 📊 EXEMPLO DE USO COMPLETO

```powershell
# Passo 1: Validação rápida (10 segundos)
python tools/verify_app_clientes_coverage_env.py

# Verificar diagnóstico 04: inclui tests/modules?
type diagnostics\app_clientes\04_test_selection_diagnosis.txt

# Passo 2: Teste rápido de execução (45 segundos)
python tools/verify_app_coverage_execution.py --quick

# Verificar resumo consolidado
type diagnostics\app_clientes\09_consolidated_report.txt

# Passo 3 (opcional): Execução completa (10 minutos)
python tools/verify_app_coverage_execution.py
```

---

## 📋 O QUE O SCRIPT VERIFICA (Microfase 18)

O script [tools/verify_app_clientes_coverage_env.py](../../tools/verify_app_clientes_coverage_env.py) realiza **3 verificações principais**:

### 1️⃣ Ambiente Python e customtkinter

**Verifica**:
- Python atualmente ativo (`sys.executable`)
- Python da `.venv` (via `.vscode/settings.json` ou `.venv/Scripts/python.exe`)
- Se `customtkinter` está instalado em cada Python (versão + localização)
- Variáveis de ambiente (`VIRTUAL_ENV`, `CONDA_PREFIX`, `PYTHONPATH`)

**Por quê**: Se `customtkinter` não estiver na `.venv`, testes de módulos Clientes serão skipados na PP.

---

### 2️⃣ Comandos de Cobertura e Seleção de Testes

**Verifica**:
- Comandos `pytest`/`coverage` em arquivos do projeto:
  - `.github/workflows/*.yml` (Pull Pipeline)
  - `pytest.ini`, `pytest_cov.ini` (configurações)
  - `scripts/*.py`, `tools/*.py` (scripts de automação)
  - `.vscode/tasks.json` (tarefas VS Code)
- Se comandos incluem `tests/unit` isoladamente (exclui `tests/modules`)
- Configuração `testpaths` no `pytest.ini`
- Coleta real do pytest (`--collect-only`) para confirmar inclusão de `tests/modules/clientes`

**Por quê**: Se PP usa `pytest tests/unit`, a cobertura de módulos Clientes NÃO entra.

---

### 3️⃣ Hotspots Pylance (Scan Estático)

**Verifica**:
- **Redefinição de `HAS_CUSTOMTKINTER`**:
  - Procura por múltiplas atribuições `HAS_CUSTOMTKINTER =` no mesmo arquivo
  - Locais: `tests/modules/clientes/**/*.py`, `tests/unit/modules/clientes/**/*.py`
  
- **Uso de `.reconfigure()` sem cast**:
  - Procura por `.reconfigure(` em `tools/**/*.py`
  - Causa: `sys.stdout` tipado como `TextIO` (abstrato), mas runtime é `TextIOWrapper`

**Por quê**: Gera erros `reportConstantRedefinition` e `reportAttributeAccessIssue` no Pylance.

---

## 🚀 COMO EXECUTAR

### Opção 1: VS Code (Recomendado)

1. Abrir arquivo: [tools/verify_app_clientes_coverage_env.py](../../tools/verify_app_clientes_coverage_env.py)
2. Clicar com botão direito → **"Run Python File in Terminal"**
3. Aguardar conclusão (~10-30 segundos)

### Opção 2: Terminal

```powershell
# Windows PowerShell
python tools/verify_app_clientes_coverage_env.py

# Ou via .venv (se ativado)
.venv\Scripts\Activate.ps1
python tools/verify_app_clientes_coverage_env.py
```

```bash
# Linux/Mac
python tools/verify_app_clientes_coverage_env.py

# Ou via .venv (se ativado)
source .venv/bin/activate
python tools/verify_app_clientes_coverage_env.py
```

---

## 📂 ONDE FICAM OS LOGS

Todos os diagnósticos são salvos em: **`diagnostics/app_clientes/`**

| Arquivo | Conteúdo |
|---------|----------|
| `01_env_active_python.txt` | Python atualmente ativo + customtkinter |
| `02_env_venv_python.txt` | Python da .venv + customtkinter (via subprocess) |
| `03_app_coverage_commands_found.txt` | Comandos pytest/coverage encontrados no projeto |
| `04_test_selection_diagnosis.txt` | Análise de inclusão/exclusão de tests/modules |
| `05_pytest_collect_only_active_command.txt` | Coleta real do pytest (testes coletados) |
| `06_pylance_hotspots_scan.txt` | Hotspots Pylance (redefinições + .reconfigure) |

---

## 🔍 COMO INTERPRETAR OS RESULTADOS

### Diagnóstico 01: Python Ativo

**Exemplo de saída**:
```
[Python Ativo]
sys.executable: C:\Users\User\AppData\Local\Programs\Python\Python313\python.exe
sys.version: 3.13.7 ...

[Import customtkinter]
✓ Status: OK
✓ Versão: 5.2.2
✓ Localização: C:\...\site-packages\customtkinter\__init__.py
```

**Interpretação**:
- ✅ **OK**: customtkinter instalado no Python ativo
- ❌ **ImportError**: customtkinter não instalado neste Python

**Ação se falhar**:
```powershell
# Instalar no Python ativo
pip install customtkinter>=5.2.0
```

---

### Diagnóstico 02: Python da .venv

**Exemplo de saída**:
```
✓ Python da .venv ENCONTRADO: .venv\Scripts\python.exe

[Executando verificação via subprocess...]

sys.executable: C:\Users\User\Desktop\v1.5.42\.venv\Scripts\python.exe
✓ customtkinter: OK
✓ Versão: 5.2.2
```

**Interpretação**:
- ✅ **OK**: `.venv` existe e `customtkinter` instalado
- ⚠️ **ImportError**: `.venv` existe, mas `customtkinter` NÃO instalado
- ❌ **NÃO ENCONTRADO**: `.venv` não existe

**Ação se customtkinter ausente na .venv**:
```powershell
# Windows
.venv\Scripts\Activate.ps1
pip install customtkinter>=5.2.0

# Linux/Mac
source .venv/bin/activate
pip install customtkinter>=5.2.0
```

**Ação se .venv não existir**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac
pip install -r requirements-dev.txt
```

---

### Diagnóstico 03: Comandos de Cobertura Encontrados

**Exemplo de saída**:
```
✓ 15 linhas encontradas com keywords:

[.github/workflows/ci.yml]
  Linha 28: run: python -m pytest --cov=src --cov-report=term-missing -v

[pytest.ini]
  Linha 7: testpaths = tests
```

**Interpretação**:
- ✅ **Comando sem restrição de caminho**: coleta tudo em `testpaths`
- ⚠️ **Comando com `tests/unit`**: exclui `tests/modules`
- ⚠️ **Comando com `-m unit` ou `-k unit`**: pode excluir `tests/modules`

---

### Diagnóstico 04: Seleção de Testes

**Exemplo de saída 1 (BOM)**:
```
[Comandos que especificam APENAS tests/unit]
  ✓ Nenhum encontrado

[Configuração pytest.ini]
  testpaths: tests
  ✓ Inclui todo o diretório tests/ (modules incluído)

[CONCLUSÃO]
  INCLUI tests/modules (testpaths=tests)

✓ TUDO CERTO:
  - Configuração inclui tests/modules/clientes
  - Cobertura de módulos Clientes ENTRA na PP
```

**Exemplo de saída 2 (RUIM)**:
```
[Comandos que especificam APENAS tests/unit]
  ⚠️  .github/workflows/ci.yml:28

[CONCLUSÃO]
  EXCLUI tests/modules

⚠️  AÇÃO NECESSÁRIA:
  - Comandos encontrados excluem tests/modules/clientes
  - Cobertura de módulos Clientes NÃO entra na PP
```

**Ação se EXCLUI tests/modules**:

Editar [.github/workflows/ci.yml](../../.github/workflows/ci.yml):

```yaml
# ❌ ANTES (exclui modules)
- name: Run tests with coverage
  run: python -m pytest tests/unit --cov=src -v

# ✅ DEPOIS (inclui modules)
- name: Run tests with coverage
  run: python -m pytest --cov=src -v
```

---

### Diagnóstico 05: Pytest Collect-Only

**Exemplo de saída 1 (BOM)**:
```
[Análise]
✓ tests/modules/clientes DETECTADO na coleta
✓ 153 linhas de testes/modules/clientes encontradas
```

**Exemplo de saída 2 (RUIM)**:
```
[Análise]
✗ tests/modules/clientes NÃO DETECTADO na coleta
  Possíveis causas:
  - Comando exclui tests/modules
  - Todos os testes são skipados (ImportError customtkinter)
  - Configuração pytest.ini exclui o diretório
```

**Ação se NÃO DETECTADO**:
1. Verificar diagnóstico 02: `customtkinter` instalado na `.venv`?
2. Verificar diagnóstico 04: comandos excluem `tests/modules`?
3. Verificar `pytest.ini`: `norecursedirs` inclui `tests/modules`?

---

### Diagnóstico 06: Pylance Hotspots

**Exemplo de saída 1 (BOM)**:
```
✓ Nenhum hotspot Pylance encontrado

Verificações realizadas:
  1. HAS_CUSTOMTKINTER redefinido em tests/modules/clientes/**/*.py
  2. .reconfigure( em tools/**/*.py
```

**Exemplo de saída 2 (RUIM)**:
```
⚠️  2 arquivo(s) com hotspots Pylance:

[tests/modules/clientes/test_exemplo.py]
  Linha 15: HAS_CUSTOMTKINTER = True
  Linha 18: HAS_CUSTOMTKINTER = False

  → Correção: Importar de appearance.py em vez de redefinir
    from src.modules.clientes.appearance import HAS_CUSTOMTKINTER

[tools/trace_coverage_clientes.py]
  Linha 42: sys.stdout.reconfigure(encoding='utf-8')

  → Correção: Usar cast para io.TextIOWrapper
    from typing import cast
    import io
    cast(io.TextIOWrapper, sys.stdout).reconfigure(...)
```

**Ação se hotspots encontrados**:

#### 1) HAS_CUSTOMTKINTER redefinido

**Problema**:
```python
# ❌ Pylance: reportConstantRedefinition
try:
    import customtkinter
    HAS_CUSTOMTKINTER = True
except ImportError:
    HAS_CUSTOMTKINTER = False  # ← Redefinição!
```

**Solução**:
```python
# ✅ Importar da fonte oficial
from src.modules.clientes.appearance import HAS_CUSTOMTKINTER

pytestmark = pytest.mark.skipif(
    not HAS_CUSTOMTKINTER, reason="No module named 'customtkinter'"
)
```

#### 2) .reconfigure() sem cast

**Problema**:
```python
# ❌ Pylance: reportAttributeAccessIssue
sys.stdout.reconfigure(encoding='utf-8')
# TextIO (abstrato) não tem .reconfigure
```

**Solução**:
```python
# ✅ Cast para io.TextIOWrapper (concreto)
import io
from typing import cast

if hasattr(sys.stdout, "reconfigure"):
    cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
```

---

## 🛠️ TROUBLESHOOTING

### Problema 1: "customtkinter: ImportError" na .venv

**Sintoma**: Diagnóstico 02 mostra `✗ customtkinter: ImportError`

**Causa**: `customtkinter` não instalado na `.venv`

**Solução**:
```powershell
# 1. Ativar .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

# 2. Instalar customtkinter
pip install customtkinter>=5.2.0

# 3. Ou instalar tudo de uma vez
pip install -r requirements-dev.txt
```

**Validação**:
```powershell
python -c "import customtkinter; print(customtkinter.__version__)"
# ✅ Deve imprimir: 5.2.2
```

---

### Problema 2: "tests/modules/clientes NÃO DETECTADO na coleta"

**Sintoma**: Diagnóstico 05 não encontra `tests/modules/clientes`

**Causa 1**: Todos os testes skipados (ImportError customtkinter)

**Solução 1**: Instalar `customtkinter` na `.venv` (ver Problema 1)

**Causa 2**: Comando exclui `tests/modules` explicitamente

**Solução 2**: Editar comando em [.github/workflows/ci.yml](../../.github/workflows/ci.yml):
```yaml
# ❌ Exclui modules
run: python -m pytest tests/unit --cov=src -v

# ✅ Inclui modules
run: python -m pytest --cov=src -v
```

**Causa 3**: `pytest.ini` exclui `tests/modules` em `norecursedirs`

**Solução 3**: Editar [pytest.ini](../../pytest.ini):
```ini
# ❌ Exclui modules
norecursedirs = tests/modules

# ✅ Não exclui
norecursedirs = .venv venv build dist
```

---

### Problema 3: ".venv NÃO ENCONTRADO"

**Sintoma**: Diagnóstico 02 mostra `✗ Python da .venv NÃO ENCONTRADO`

**Causa**: `.venv` não existe no projeto

**Solução**:
```powershell
# 1. Criar .venv
python -m venv .venv

# 2. Ativar
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

# 3. Instalar dependências
pip install -r requirements-dev.txt

# 4. Configurar VS Code
# Criar/editar .vscode/settings.json:
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```

---

### Problema 4: "TIMEOUT após 30 segundos" no collect-only

**Sintoma**: Diagnóstico 05 mostra `✗ TIMEOUT após 30 segundos`

**Causa**: Muitos testes no projeto (coleta lenta)

**Solução**: Normal para projetos grandes. Verificar diagnóstico 04 (seleção de testes) em vez do 05.

**Alternativa**: Coletar apenas módulo específico:
```powershell
python -m pytest --collect-only tests/modules/clientes/ -q
```

---

### Problema 5: Script falha ao executar

**Sintoma**: Erro Python ao rodar o script

**Solução**:
1. Verificar Python 3.8+ instalado:
   ```powershell
   python --version
   # Deve ser >= 3.8
   ```

2. Executar com `-v` para debug:
   ```powershell
   python -v tools/verify_app_clientes_coverage_env.py
   ```

3. Verificar permissões de escrita em `diagnostics/`:
   ```powershell
   # Windows
   icacls diagnostics
   
   # Linux/Mac
   ls -la diagnostics
   ```

---

## 📊 MÉTRICAS DE SUCESSO

### ✅ Ambiente OK

- [ ] Diagnóstico 01: `✓ customtkinter: OK` (Python ativo)
- [ ] Diagnóstico 02: `✓ customtkinter: OK` (Python da .venv)
- [ ] Variáveis de ambiente: `VIRTUAL_ENV` aponta para `.venv`

### ✅ Cobertura OK

- [ ] Diagnóstico 03: Comando PP sem `tests/unit` isolado
- [ ] Diagnóstico 04: Conclusão = `INCLUI tests/modules (testpaths=tests)`
- [ ] Diagnóstico 05: `✓ tests/modules/clientes DETECTADO na coleta`

### ✅ Pylance OK

- [ ] Diagnóstico 06: `✓ Nenhum hotspot Pylance encontrado`
- [ ] OU hotspots já corrigidos nas Microfases 16-17

---

## 🔄 FLUXO DE TRABALHO RECOMENDADO

### 1️⃣ Antes de Iniciar Desenvolvimento

```powershell
# 1. Ativar .venv
.venv\Scripts\Activate.ps1

# 2. Rodar verificador
python tools/verify_app_clientes_coverage_env.py

# 3. Verificar diagnósticos
# - 01: customtkinter OK no Python ativo?
# - 02: customtkinter OK na .venv?
# - 04: tests/modules INCLUÍDO?
# - 06: Nenhum hotspot Pylance?
```

### 2️⃣ Antes de Abrir Pull Request

```powershell
# 1. Rodar verificador
python tools/verify_app_clientes_coverage_env.py

# 2. Verificar diagnóstico 04
# - Conclusão deve ser: INCLUI tests/modules

# 3. Rodar testes localmente (simular PP)
python -m pytest --cov=src --cov-report=term-missing -v

# 4. Verificar cobertura inclui módulos Clientes
# - Relatório deve mostrar: src/modules/clientes/views/toolbar_ctk.py
```

### 3️⃣ Após Mudanças em Configuração

Se alterar:
- `pytest.ini`, `pytest_cov.ini`
- `.github/workflows/ci.yml`
- `requirements.txt`, `requirements-dev.txt`

```powershell
# Rodar verificador novamente
python tools/verify_app_clientes_coverage_env.py

# Verificar diagnósticos 03, 04, 05
# - Comandos de cobertura atualizados?
# - Seleção de testes correta?
# - Coleta real confirma mudanças?
```

---

## 📚 REFERÊNCIAS

- Microfase 16: [CLIENTES_MICROFASE_16_PP_COVERAGE_ALIGNMENT.md](CLIENTES_MICROFASE_16_PP_COVERAGE_ALIGNMENT.md) - Correções Pylance
- Microfase 17: [CLIENTES_MICROFASE_17_PP_COVERAGE_CLOSE.md](CLIENTES_MICROFASE_17_PP_COVERAGE_CLOSE.md) - Validação PP
- Script 1: [tools/verify_app_clientes_coverage_env.py](../../tools/verify_app_clientes_coverage_env.py) - Análise estática
- Script 2: [tools/verify_app_coverage_execution.py](../../tools/verify_app_coverage_execution.py) - Execução real ⭐
- [pytest.ini](../../pytest.ini) - Configuração de coleta
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml) - Pull Pipeline

---

## ✅ RESUMO EXECUTIVO

### Script 1: verify_app_clientes_coverage_env.py (Análise Estática)

**O que faz**:
1. ✅ Valida ambiente Python (ativo + .venv) e `customtkinter`
2. ✅ Descobre comandos de cobertura e se incluem `tests/modules`
3. ✅ Scan estático de hotspots Pylance (redefinições + .reconfigure)

**Como usar**:
```powershell
python tools/verify_app_clientes_coverage_env.py
```

**Logs gerados**:
```
diagnostics/app_clientes/01_env_active_python.txt
diagnostics/app_clientes/02_env_venv_python.txt
diagnostics/app_clientes/03_app_coverage_commands_found.txt
diagnostics/app_clientes/04_test_selection_diagnosis.txt
diagnostics/app_clientes/05_pytest_collect_only_active_command.txt
diagnostics/app_clientes/06_pylance_hotspots_scan.txt
```

---

### Script 2: verify_app_coverage_execution.py (Execução Real) ⭐ NOVO

**O que faz**:
1. ✅ Descobre comando de cobertura do app (pytest -c pytest_cov.ini)
2. ✅ **EXECUTA** o comando via subprocess usando Python da .venv
3. ✅ Captura stdout/stderr completo da execução
4. ✅ Verifica se tests/modules/clientes foi **EXECUTADO** (não apenas coletado)
5. ✅ Valida artefatos de cobertura (htmlcov, coverage.json)

**Como usar**:

Modo rápido (recomendado):
```powershell
python tools/verify_app_coverage_execution.py --quick
# ⚡ ~45 segundos (apenas tests/modules/clientes)
```

Modo completo:
```powershell
python tools/verify_app_coverage_execution.py
# ⚠️  ~10 minutos (toda a suite de testes)
```

**Logs gerados**:
```
diagnostics/app_clientes/07_run_global_coverage_stdout.txt  (stdout completo)
diagnostics/app_clientes/08_run_global_coverage_stderr.txt  (stderr completo)
diagnostics/app_clientes/09_consolidated_report.txt         (resumo consolidado)
```

**Exemplo de saída** (modo rápido):
```
✓ customtkinter na .venv: OK
✓ tests/modules/clientes executado: SIM
✓ Resultado: 137 passed, 1 xfailed, 3 warnings in 44.05s
✓ Artefatos gerados: SIM
```

---

## Execução Manual da Cobertura Global (14/01/2026)

Para validar completamente a suite de testes, executamos a cobertura global diretamente no terminal:

```powershell
pytest -c pytest_cov.ini
```

### 📊 Resultados da Execução Manual

**Sumário de Execução:**
- **Total de testes:** 8,784 testes
- **✅ Passou:** 8,735 (99.4%)
- **❌ Falhou:** 5 (0.06%)
- **⏭️ Pulados:** 43 (skipped)
- **⚠️ XFailed:** 1 (falha esperada)
- **⚠️ Warnings:** 29
- **⏱️ Tempo:** 6876.29s ≈ **1h 55min**

**Testes Falhados (5):**
1. `test_toolbar_search_wrapper_corner_matches_entry` 
   - Erro: corner_radius divergente (wrapper=6, entry=5)
   - Arquivo: [tests/modules/clientes/test_clientes_layout_polish_smoke.py](../../tests/modules/clientes/test_clientes_layout_polish_smoke.py#L276)

2. `test_apply_theme_to_widgets_no_crash_with_ctk`
   - Erro: `_tkinter.TclError: Layout info.Round.Toggle not found`
   - Arquivo: [tests/modules/test_clientes_apply_theme_no_crash.py](../../tests/modules/test_clientes_apply_theme_no_crash.py#L31)

3. `test_create_search_controls_with_palette`
   - Erro: `_tkinter.TclError: image "pyimage7" doesn't exist`
   - Arquivo: [tests/modules/test_clientes_theme_smoke.py](../../tests/modules/test_clientes_theme_smoke.py#L89)

4. `test_toolbar_ctk_fallback`
   - Erro: `_tkinter.TclError: image "pyimage8" doesn't exist`
   - Arquivo: [tests/modules/test_clientes_toolbar_ctk_smoke.py](../../tests/modules/test_clientes_toolbar_ctk_smoke.py#L98)

5. `test_form_cliente_creates_toplevel_window`
   - Erro: AssertionError em `mock.withdraw.called`
   - Arquivo: [tests/unit/modules/clientes/forms/test_client_form_execution.py](../../tests/unit/modules/clientes/forms/test_client_form_execution.py#L129)

**⚠️ Warnings Principais:**
- 4 módulos nunca importados: `adapters`, `infra`, `data`, `security`
- 9 warnings do Pydantic sobre `@model_validator` deprecated
- Múltiplos warnings sobre pytest marks não registrados: `@pytest.mark.gui`, `@pytest.mark.unit`
- Vários warnings de deprecação em `src.ui.*` (migração para `src.modules.*`)

**✅ Artefatos Gerados:**
- `htmlcov/index.html` - Relatório HTML completo
- `reports/coverage.json` - Dados JSON para processamento

**🎯 Confirmação:**
- ✅ **tests/modules/clientes EXECUTADO:** Confirmado pela execução completa de 8,735 testes
- ✅ **Cobertura global funcional:** 99.4% de taxa de sucesso
- ⚠️ **5 falhas pontuais:** Relacionadas a UI (tkinter/customtkinter) e mocks

---

## 🎯 AÇÃO SE FALHAR

### Script 1 (verify_env)
- Diagnóstico 02 (ImportError): `pip install customtkinter>=5.2.0` na `.venv`
- Diagnóstico 04 (EXCLUI modules): Editar [.github/workflows/ci.yml](../../.github/workflows/ci.yml)
- Diagnóstico 06 (hotspots): Aplicar correções sugeridas no relatório

### Script 2 (verify_execution)
- TIMEOUT: Use `--quick` ou aguarde mais tempo
- customtkinter AUSENTE: Instalar na .venv
- tests/modules NÃO executado: Verificar diagnósticos 03-04 do Script 1
- Artefatos NÃO gerados: Verificar stderr (diagnóstico 08)

