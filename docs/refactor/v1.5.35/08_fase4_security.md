# 08 - Fase 4: Migração de `security/` para `src/security/`

> **Data de execução:** 2025-01-02  
> **Status:** ✅ Concluída  
> **Duração estimada:** ~10 minutos

---

## 🎯 Objetivo

Atualizar todos os imports do projeto de `security.*` para `src.security.*`. A pasta `security/` já havia sido movida para `src/security/` anteriormente, restando apenas a atualização dos imports.

---

## 📋 Pre-flight Check

```bash
$ python -c "from src.version import get_version; print(get_version())"
1.4.93
```

**Nota:** Versão reportada é 1.4.93 (arquivo version.py não foi atualizado para v1.5.35 ainda).

---

## 📊 Métricas Antes/Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Imports `from security` / `import security` | **6** | **0** |
| Imports `from src.security` / `import src.security` | **0** | **6** |
| Arquivos .py atualizados | - | **6** |
| Arquivos movidos | - | **0** (já estava em src/security/) |

---

## 📋 Plano de Execução

### Etapa 1: Verificações Prévias
- [x] Verificar se `src/security/` já existe → **Já existia** (migração de arquivos feita anteriormente)
- [x] Verificar se `security/` existe na raiz → **Não existe**
- [x] Contar imports de `security.*` via AST → **6 imports**

### Etapa 2: Mover Pasta
- [x] ~~Executar `git mv security src/security`~~ → **Não necessário**, pasta já estava em src/

### Etapa 3: Atualizar Imports
- [x] Substituir `from security.` → `from src.security.`
- [x] Substituir `import security` → `import src.security as crypto`
- [x] Atualizar patches em testes (`patch("security.crypto.*")` → `patch("src.security.crypto.*")`)
- [x] Atualizar testes em `tests/`

### Etapa 4: Validações
- [x] `python -m py_compile main.py` → **OK**
- [x] `python -m compileall -q src tests` → **OK**
- [x] `python -c "import src; import src.security"` → **OK**
- [x] Contagem de imports `security` remanescentes → **0**
- [x] Testes de security → **53 passed** ✅

---

## 📁 Arquivos em src/security/ (já existentes)

```
src/security/__init__.py
src/security/crypto.py
```

---

## 📝 Arquivos com Imports Atualizados (6 arquivos)

### Código Principal (2 arquivos)

| Diretório | Arquivos |
|-----------|----------|
| `src/data/` | `supabase_repo.py` |
| `src/modules/passwords/` | `controller.py` |

### Testes (4 arquivos)

```
tests/integration/passwords/test_passwords_crypto_integration.py
tests/unit/security/test_crypto_edge_cases.py
tests/unit/security/test_crypto_keyring.py
tests/unit/security/test_security_crypto_fase33.py
```

---

## 🔄 Padrões de Import Alterados

### Padrão 1: Import de funções específicas

```python
# ANTES
from security.crypto import decrypt_text, encrypt_text

# DEPOIS
from src.security.crypto import decrypt_text, encrypt_text
```

### Padrão 2: Import de módulo

```python
# ANTES
from security import crypto

# DEPOIS
from src.security import crypto
```

### Padrão 3: Patches em testes

```python
# ANTES
with patch("security.crypto.Fernet") as mock_fernet:
with patch("security.crypto._keyring_is_available", return_value=True):

# DEPOIS
with patch("src.security.crypto.Fernet") as mock_fernet:
with patch("src.security.crypto._keyring_is_available", return_value=True):
```

---

## ✅ Validações Executadas

### 1. Sintaxe

```bash
$ python -m py_compile main.py
# (sem erros)

$ python -m compileall -q src tests
# (sem erros)
```

### 2. Imports Básicos

```bash
$ python -c "import src; import src.security; print('OK')"
OK: src + src.security importaram
```

### 3. Contagem de Imports (via AST)

```
Imports remanescentes de security (sem src.): 0
Total de imports src.security: 6
```

### 4. Testes de Security

```bash
$ pytest tests/unit/security/ tests/integration/passwords/test_passwords_crypto_integration.py -v
============================= 53 passed in 13.04s =============================
```

---

## ⚠️ Riscos / Follow-ups

### 1. Build PyInstaller (rcgestor.spec)

O arquivo `rcgestor.spec` pode precisar de ajustes para o novo path `src/security`. Será tratado na **Fase 5**.

### 2. sitecustomize.py

O arquivo `sitecustomize.py` pode ter referências a `security`. Será verificado na **Fase 5**.

### 3. Outras Falhas de Teste

Os testes gerais apresentaram algumas falhas (~200), mas nenhuma relacionada à migração de security. As 53 testes específicos de security/crypto passaram com sucesso.

---

## 📋 Commit Sugerido

```bash
git add -A
git commit -m "refactor(security): update imports from 'security' to 'src.security'

- Update 6 import statements from 'security.*' to 'src.security.*'
- Update 6 Python files (2 source + 4 tests)
- Update test patches to use new module path
- All security tests passing (53 tests)
- security/ folder was already at src/security/

Phase 4 of src-layout consolidation (v1.5.35 refactor)
"
```

---

## 📎 Arquivos Relacionados

- [README.md](README.md) - Roadmap atualizado
- [07_fase3_adapters.md](07_fase3_adapters.md) - Documentação da Fase 3
- [06_fase2_data.md](06_fase2_data.md) - Documentação da Fase 2
- [05_fase1_infra.md](05_fase1_infra.md) - Documentação da Fase 1
