# Convenções de Nomes - RC Gestor de Clientes

**Projeto:** RC - Gestor de Clientes  
**Versão:** v1.3.92  
**Última atualização:** 7 de dezembro de 2025 (FASE 12 - Fechamento Final)

---

## 📚 Documento de Referência

Este documento é um **resumo executivo** das convenções de nomes do projeto.

Para o **histórico completo** de consolidações e contexto das decisões, consulte:
- 📖 **[CLEANUP_HISTORY.md](./CLEANUP_HISTORY.md)** - Histórico detalhado das FASES 1-6

---

## 🎯 Princípios Gerais

### **1. Seguir PEP 8**

Todas as convenções de nomes seguem estritamente [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/):

| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| **Funções** | `snake_case` | `normalize_cnpj`, `format_datetime` |
| **Variáveis** | `snake_case` | `user_name`, `total_count` |
| **Constantes** | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| **Classes** | `CamelCase` | `ClientPicker`, `PasswordService` |
| **Métodos** | `snake_case` | `get_client`, `validate_input` |
| **Privados** | `_prefixo` | `_strip_diacritics`, `_parse_any_dt` |

### **2. Uso de Prefixos Semânticos**

Prefixos de funções **comunicam intenção** claramente:

| Prefixo | Uso | Localização Típica | Exemplos |
|---------|-----|-------------------|----------|
| `normalize_*` | Limpeza/padronização de dados | `src/core/`, `src/utils/` | `normalize_cnpj`, `normalize_ascii` |
| `format_*` | Formatação para **exibição** | `src/helpers/formatters.py` | `format_cnpj`, `format_datetime`, `format_datetime_br` |
| `is_valid_*` | Validação booleana | `src/core/`, `src/utils/validators.py` | `is_valid_cnpj`, `is_valid_email` |
| `strip_*` | Remoção de caracteres específicos | `src/core/text_normalization.py` | `strip_diacritics`, `strip_whitespace` |
| `only_*` | Extração filtrada | `src/core/string_utils.py` | `only_digits`, `only_alpha` |

---

## ⚠️ Prefixos Deprecados

### **`fmt_*` → `format_*`**

O prefixo `fmt_*` está **sendo descontinuado** em favor de `format_*` (mais explícito).

#### **Funções Existentes com `fmt_*`:**

| Função | Arquivo | Status | Ação |
|--------|---------|--------|------|
| `fmt_data` | `src/app_utils.py` | ✅ **Wrapper legado** | Mantido para compatibilidade, delega para `format_datetime_br` |
| `fmt_datetime` | `src/helpers/formatters.py` | ✅ **Wrapper legado** (FASE 11) | Mantido para compatibilidade, delega para `format_datetime` |
| `format_datetime` | `src/helpers/formatters.py` | ✅ **Função canônica** (FASE 11) | Usar em código novo (padrão ISO YYYY-MM-DD HH:MM:SS) |
| `fmt_datetime_br` | `src/helpers/formatters.py` | ✅ **Função canônica** | Usar em código novo (padrão BR DD/MM/YYYY - HH:MM:SS) |

#### **Diretrizes:**

✅ **FAZER:**
- Novas funções de formatação devem usar `format_*` (ex.: `format_cpf`, `format_phone`)
- Manter wrappers legados com `fmt_*` se já existirem em código de produção

❌ **EVITAR:**
- Criar **novas** funções com prefixo `fmt_*`

**Exemplo:**
```python
# ❌ NÃO FAZER (nova função)
def fmt_telefone(phone: str) -> str:
    ...

# ✅ FAZER (nova função)
def format_telefone(phone: str) -> str:
    ...

# ✅ ACEITÁVEL (wrapper legado)
def fmt_data(iso_str: str | None) -> str:
    """[DEPRECATED] Use format_datetime_br."""
    from src.helpers.formatters import fmt_datetime_br
    return fmt_datetime_br(iso_str)
```

---

## 📋 Checklist para Novas Funções

Ao criar uma nova função utilitária, siga este checklist:

### **1. Localização**

- ✅ Funções **genéricas** → `src/core/` ou `src/helpers/`
- ✅ Funções **específicas de domínio** → Módulo correspondente (ex.: `src/modules/clientes/utils.py`)

### **2. Nomenclatura**

- ✅ Usar prefixo semântico apropriado (`normalize_*`, `format_*`, `is_valid_*`, etc.)
- ✅ Nome em `snake_case`
- ✅ Evitar abreviações obscuras (ex.: `fmt` → `format`, `val` → `validate`)

### **3. Documentação**

```python
def format_phone(phone: str | None) -> str:
    """Formata telefone no padrão brasileiro.

    Args:
        phone: Número de telefone (somente dígitos ou com formatação).

    Returns:
        String formatada (XX) XXXXX-XXXX ou vazio se inválido.

    Examples:
        >>> format_phone("11987654321")
        '(11) 98765-4321'
        >>> format_phone(None)
        ''
    """
```

### **4. Testes**

- ✅ Criar teste canônico em `tests/unit/core/` ou `tests/unit/helpers/`
- ✅ Cobrir: caso feliz, None, vazio, edge cases

### **5. Evitar Duplicação**

Antes de criar, verificar se já existe em:
- `src/core/string_utils.py` (manipulação de strings)
- `src/core/cnpj_norm.py` (CNPJ)
- `src/core/text_normalization.py` (acentos, ASCII)
- `src/helpers/formatters.py` (formatação de exibição)
- `src/utils/validators.py` (validações)

---

## 🔍 Exemplos Práticos

### **Normalização vs. Formatação**

```python
# NORMALIZAÇÃO: Remove formatação, valida, retorna padrão interno
from src.core.cnpj_norm import normalize_cnpj
cnpj = normalize_cnpj("11.222.333/0001-65")  # → "11222333000165"

# FORMATAÇÃO: Adiciona formatação para exibição
from src.helpers.formatters import format_cnpj
display = format_cnpj("11222333000165")  # → "11.222.333/0001-65"
```

### **Validação Booleana**

```python
from src.core.cnpj_norm import is_valid_cnpj

# Valida CNPJ com dígito verificador (DV)
is_valid_cnpj("11.222.333/0001-65")  # → True
is_valid_cnpj("00.000.000/0000-00")  # → False (DV inválido)
```

### **Remoção de Caracteres**

```python
from src.core.text_normalization import strip_diacritics
from src.core.string_utils import only_digits

# Remove acentos
strip_diacritics("São Paulo")  # → "Sao Paulo"

# Extrai apenas dígitos
only_digits("(11) 98765-4321")  # → "11987654321"
```

---

## 🛠️ Ferramentas de Verificação

### **Ruff (Linter)**

O projeto usa **Ruff** para garantir conformidade com PEP 8, incluindo regras de naming:

```bash
# Verificar violações de naming
ruff check src tests

# Auto-corrigir problemas simples (ex.: imports não usados)
ruff check --fix src tests
```

**Regras de naming ativadas:**
- `N8xx` - PEP 8 naming conventions (ativado na FASE 8)
  - `N802` - Função deve ser `snake_case`
  - `N803` - Argumento deve ser `snake_case`
  - `N806` - Variável em função deve ser lowercase
  - `N818` - Exceção deve ter sufixo `Error`

### **Pyright (Type Checker)**

```bash
# Verificar tipos estáticos
pyright src/
```

---

## 📊 Resumo de Funções Canônicas

| Função Canônica | Arquivo | Substituiu | Uso |
|-----------------|---------|------------|-----|
| `only_digits` | `src/core/string_utils.py` | 6 duplicatas | Extrai dígitos de string |
| `format_cnpj` | `src/helpers/formatters.py` | 7 duplicatas | Formata CNPJ (XX.XXX.XXX/XXXX-XX) |
| `normalize_cnpj` | `src/core/cnpj_norm.py` | 2 duplicatas | Normaliza e valida CNPJ |
| `is_valid_cnpj` | `src/core/cnpj_norm.py` | 1 implementação antiga | Valida CNPJ com DV |
| `strip_diacritics` | `src/core/text_normalization.py` | 6 duplicatas | Remove acentos (NFD) |
| `normalize_ascii` | `src/core/text_normalization.py` | 2 duplicatas | Remove acentos e converte para ASCII |
| `fmt_datetime_br` | `src/helpers/formatters.py` | `fmt_data` | Formata data brasileira |

**Consulte [CLEANUP_HISTORY.md](./CLEANUP_HISTORY.md) para detalhes de cada consolidação.**

---

## 🔗 Referências

### **Documentação Interna**
- [CLEANUP_HISTORY.md](./CLEANUP_HISTORY.md) - Histórico completo de refatorações
- [TEST_ARCHITECTURE.md](./TEST_ARCHITECTURE.md) - Arquitetura de testes

### **Padrões Externos**
- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

### **Linters**
- [Ruff Rules - pep8-naming](https://docs.astral.sh/ruff/rules/#pep8-naming-n)

---

## 🎓 Boas Práticas

### ✅ **FAZER**

1. **Usar prefixos semânticos consistentes** (`normalize_*`, `format_*`, `is_valid_*`)
2. **Documentar com docstrings completas** (Args, Returns, Examples)
3. **Criar testes canônicos** para novas funções utilitárias
4. **Verificar duplicação** antes de criar nova função
5. **Rodar Ruff** antes de cada commit

### ❌ **EVITAR**

1. **Criar novos `fmt_*`** (usar `format_*`)
2. **Abreviações obscuras** (`val`, `fmt`, `chk`)
3. **Duplicar lógica** que já existe em `src/core/` ou `src/helpers/`
4. **Misturar normalização e formatação** na mesma função
5. **Ignorar avisos do Ruff** sem justificativa documentada

---

**Última atualização:** 7 de dezembro de 2025 (FASE 8 - Naming & Lint Rules)  
**Responsáveis:** Equipe de Qualidade - RC Gestor
