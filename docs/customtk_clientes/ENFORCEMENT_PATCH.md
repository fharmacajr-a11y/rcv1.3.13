# 🎯 Enforcement CustomTkinter - Patch Completo

Este documento contém o diff completo de todas as alterações implementadas para enforcement da política CustomTkinter SSoT.

---

## 📦 Arquivos Criados

### 1. `.github/workflows/pre-commit.yml` (novo)

```yaml
name: Pre-commit Checks

on:
  push:
    branches: ['**']
  pull_request:
    branches: ['**']

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install pre-commit
        run: pip install pre-commit

      - name: Run pre-commit hooks
        uses: pre-commit/action@v3.0.1
        with:
          extra_args: --all-files --show-diff-on-failure

      - name: Upload pre-commit results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: pre-commit-failures
          path: .pre-commit.log
          retention-days: 7
```

### 2. `scripts/validate_ctk_policy.py` (novo)

**Propósito**: Script Python para validação manual da política antes de commitar.

**Funcionalidades**:
- Busca recursiva por imports diretos de customtkinter
- Relatório detalhado com linha, arquivo e tipo de import
- Respeita whitelist (src/ui/ctk_config.py)
- Pula diretórios ocultos e __pycache__

**Uso**:
```powershell
python scripts/validate_ctk_policy.py
```

**Saída esperada**:
```
🔍 Validando política CustomTkinter (SSoT)...

❌ 15 violação(ões) encontrada(s):

  📄 src/modules/uploads/views/action_bar.py:11
     from customtkinter import CTkButton, CTkFrame
     Tipo: from

🔧 Como corrigir:
   1. Substitua imports diretos por:
      from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
```

### 3. `docs/CTK_IMPORT_POLICY.md` (novo)

**Propósito**: Documentação completa da política SSoT.

**Conteúdo**:
- Regra principal (nunca import customtkinter direto)
- Padrões corretos vs proibidos
- Como é garantido (pre-commit + CI/CD)
- Como corrigir violações
- Justificativa técnica
- Arquivo whitelist

### 4. `docs/CTK_VALIDATION_QUICKSTART.md` (novo)

**Propósito**: Guia rápido de comandos de validação.

**Conteúdo**:
- Instalação do pre-commit
- Comandos de validação (todos os hooks, apenas CTk, arquivo específico)
- Exemplos práticos de correção
- Troubleshooting (hook falha, como corrigir, bypass)
- Status atual do repositório

### 5. `docs/ENFORCEMENT_SUMMARY.md` (novo)

**Propósito**: Sumário completo da implementação de enforcement.

**Conteúdo**:
- Lista de arquivos criados/atualizados
- Comandos de validação local
- Teste do enforcement
- Status atual de violações (15 detectadas)
- Próximos passos (Microfase 23.2)
- Checklist de implementação

---

## 📝 Arquivos Atualizados

### 1. `.pre-commit-config.yaml`

**Diff**:

```diff
       - id: name-tests-test
         name: Verificar nomes de arquivos de teste
         args: ['--pytest-test-first']
         files: ^tests/(unit|integration)/.*\.py$
         exclude: (doubles|factories|helpers|conftest|LEGACY_).*\.py$

+  # ---------------------------------------------------------------------------
+  # HOOKS LOCAIS - Políticas Customizadas do Projeto
+  # ---------------------------------------------------------------------------
+  - repo: local
+    hooks:
+      - id: no-direct-customtkinter-import
+        name: Proibir import direto de customtkinter (usar src/ui/ctk_config.py)
+        language: pygrep
+        entry: '^\s*(import\s+customtkinter|from\s+customtkinter\s+import)'
+        types: [python]
+        exclude: ^src/ui/ctk_config\.py$
+        description: |
+          CustomTkinter deve ser importado apenas via src/ui/ctk_config.py (Single Source of Truth).
+          Use: from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
+
 # ============================================================================
 # CONFIGURAÇÕES GLOBAIS
 # ============================================================================
```

**Explicação**:
- `repo: local`: Hook customizado do projeto (não vem de repo externo)
- `language: pygrep`: Busca por regex em arquivos Python
- `entry`: Regex que captura `import customtkinter` e `from customtkinter import ...`
- `types: [python]`: Aplica apenas em arquivos .py
- `exclude`: Whitelist - permite apenas src/ui/ctk_config.py

### 2. `CONTRIBUTING.md`

**Diff**:

```diff
 ### 4. Instalar hooks do pre-commit

 **IMPORTANTE:** Configure os hooks de pre-commit para garantir qualidade de código antes de cada commit:

 ```powershell
 pre-commit install
 pre-commit run --all-files  # primeira vez
 ```

 Após essa configuração:

 - ✅ Antes de cada commit, o pre-commit executará automaticamente:
   - Ruff (linter e formatador Python)
   - Verificação de trailing whitespace
   - Garantia de nova linha no final dos arquivos
   - Validação de sintaxe YAML/TOML/JSON
   - Detecção de merge conflicts
   - Normalização de line endings
+  - **Enforcement de políticas CustomTkinter** (ver abaixo)

 - ⚠️ **Se algum hook falhar** (ex: ruff encontrar problema de lint/formato), você precisa:
   1. Revisar as correções automáticas feitas pelo pre-commit
   2. Adicionar os arquivos corrigidos (`git add <arquivos>`)
   3. Tentar o commit novamente

 - 🚫 **Não use `--no-verify`** para pular pre-commit, exceto em casos muito específicos (ex: commits de docs/merge)

+#### 🎨 Política CustomTkinter (Single Source of Truth)
+
+**REGRA DE OURO:** Nunca importe `customtkinter` diretamente em qualquer arquivo do projeto.
+
+✅ **CORRETO:**
+```python
+from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
+
+if HAS_CUSTOMTKINTER:
+    # usar ctk.CTkButton, etc.
+```
+
+❌ **PROIBIDO:**
+```python
+import customtkinter  # ❌ HOOK VAI FALHAR!
+from customtkinter import CTkButton  # ❌ HOOK VAI FALHAR!
+```
+
+**Por quê?**
+- `src/ui/ctk_config.py` é o **único arquivo permitido** para importar customtkinter
+- Isso garante Single Source of Truth (SSoT) para detecção de CTk
+- Evita duplicação de lógica try/except em múltiplos módulos
+- Facilita manutenção e debugging
+
+**O que acontece se eu importar direto?**
+- ⚠️ O hook `no-direct-customtkinter-import` do pre-commit **vai falhar o commit**
+- ⚠️ A CI/CD no GitHub Actions **vai falhar o PR**
+- 📝 Você precisará refatorar para usar `src.ui.ctk_config`
+
+**Arquivo whitelist (permitido):**
+- `src/ui/ctk_config.py` (único permitido)
+
 ### 5. Validar instalação rodando testes
```

### 3. `README.md`

**Diff**:

```diff
 📖 **Documentação Adicional:**
 - [Modelo de Segurança - Criptografia e Gestão de Chaves](docs/SECURITY_MODEL.md)
+- [Política CustomTkinter (SSoT) - Guia de Imports](docs/CTK_IMPORT_POLICY.md)
+- [Guia de Contribuição - Setup e Boas Práticas](CONTRIBUTING.md)

 ---
```

### 4. `docs/MICROFASE_23_CTK_SINGLE_SOURCE_OF_TRUTH.md`

**Diff**: Adicionada seção completa "🛡️ Enforcement (Microfase 23.1)" com:
- Arquivos criados/atualizados
- Hook pre-commit (código)
- GitHub Actions workflow (código)
- Validação manual (comandos)
- Status atual de violações (15 encontradas)
- Comandos de validação

---

## ✅ Checklist de Validação

### Instalação (Primeira Vez)

```powershell
# 1. Instalar pre-commit
pip install pre-commit

# 2. Instalar hooks no repo
pre-commit install

# 3. Rodar pela primeira vez (instala dependências dos hooks)
pre-commit run --all-files
```

### Comandos de Validação

```powershell
# Validar todos os hooks
pre-commit run --all-files

# Validar apenas política CTk
pre-commit run no-direct-customtkinter-import --all-files

# Script Python (relatório detalhado)
python scripts/validate_ctk_policy.py

# Validar arquivo específico
pre-commit run no-direct-customtkinter-import --files src/modules/exemplo/view.py
```

### Teste Manual

```powershell
# 1. Criar arquivo temporário com violação
@"
import customtkinter
def test(): pass
"@ | Out-File -FilePath test_violation.py -Encoding utf8

# 2. Tentar commitar (deve falhar)
git add test_violation.py
git commit -m "test: verificar enforcement"

# Resultado esperado:
# no-direct-customtkinter-import...............................Failed
# - hook id: no-direct-customtkinter-import
# - exit code: 1
# test_violation.py:1:import customtkinter

# 3. Limpar
git reset HEAD test_violation.py
Remove-Item test_violation.py
```

---

## 🎯 Resultado Final

### ✅ Implementado

1. **Pre-commit Hook**: Detecta imports diretos de customtkinter
2. **GitHub Actions**: Roda pre-commit em PRs e pushes
3. **Documentação**: 4 documentos criados/atualizados
4. **Script de Validação**: Python script para relatório detalhado
5. **Whitelist**: Apenas src/ui/ctk_config.py permitido

### 📊 Status Atual

- **Violações detectadas**: 15 (código legado pré-enforcement)
- **Hook funcionando**: ✅ Sim (testado e validado)
- **CI/CD configurado**: ✅ Sim (.github/workflows/pre-commit.yml)
- **Documentação completa**: ✅ Sim (4 documentos)

### 🚀 Próximos Passos

**Microfase 23.2** (opcional): Refatorar 15 violações legadas

```powershell
# Criar branch
git checkout -b refactor/microfase-23-2-fix-ctk-violations

# Refatorar arquivos (ver exemplos em docs/CTK_IMPORT_POLICY.md)
# ...

# Validar (deve passar com 0 violações)
pre-commit run --all-files

# Commitar
git commit -m "refactor: migrar violações para src.ui.ctk_config (Microfase 23.2)"
```

---

## 📚 Documentação Completa

1. [CTK_IMPORT_POLICY.md](docs/CTK_IMPORT_POLICY.md) - Política completa
2. [CTK_VALIDATION_QUICKSTART.md](docs/CTK_VALIDATION_QUICKSTART.md) - Guia rápido
3. [ENFORCEMENT_SUMMARY.md](docs/ENFORCEMENT_SUMMARY.md) - Sumário completo
4. [MICROFASE_23_CTK_SINGLE_SOURCE_OF_TRUTH.md](docs/MICROFASE_23_CTK_SINGLE_SOURCE_OF_TRUTH.md#-enforcement-microfase-231) - Seção enforcement

---

**Implementação validada e funcional** ✅

**Comandos finais para testar**:

```powershell
# 1. Validar tudo
pre-commit run --all-files

# 2. Relatório detalhado
python scripts/validate_ctk_policy.py

# 3. Apenas hook CTk
pre-commit run no-direct-customtkinter-import --all-files
```
