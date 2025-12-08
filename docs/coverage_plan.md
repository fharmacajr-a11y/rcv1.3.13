# Plano de Cobertura de Testes - RC Gestor v1.3.61

**Data de início:** 2025-12-04  
**Branch:** qa/fixpack-04

## Objetivo

Aumentar a cobertura de testes unitários de forma incremental, priorizando módulos não-UI e de baixo acoplamento.

---

## Módulos Priorizados

| Módulo | Status | Cobertura | Observações |
|--------|--------|-----------|-------------|
| `src/utils/phone_utils.py` | ✅ **COMPLETO** | **95.9%** | TEST-001: Funções puras, sem dependências externas. |
| `src/utils/validators.py` | ✅ **COMPLETO** | **95.2%** | TEST-002: Type hints já adequados; 70 testes existentes. |
| `src/utils/paths.py` | ✅ **COMPLETO** | **100%** | TEST-003: Caminhos PyInstaller/dev; 10 testes. |

---

## Critérios de Seleção

1. **Não-UI**: Módulos sem dependência de Tkinter/ttkbootstrap
2. **Baixo acoplamento**: Funções puras ou com poucas dependências
3. **Impacto**: Módulos usados em várias partes do sistema
4. **Testabilidade**: Entrada/saída bem definidas

---

## Histórico

### TEST-001: `src/utils/phone_utils.py` (2025-12-04)

**Justificativa da escolha:**
- Módulo pequeno (~70 linhas)
- Funções puras: `only_digits()` e `normalize_br_whatsapp()`
- Sem dependências externas além de `re` (stdlib)
- Sem testes existentes em `tests/utils/`
- Fácil de validar: entrada de telefone → saída formatada

**Status:** ✅ COMPLETO

**Resultados:**
- **20 testes** criados (6 para `only_digits`, 14 para `normalize_br_whatsapp`)
- **Cobertura:** 95.9% (31 statements, 1 miss, 18 branches)
- **Arquivo de testes:** `tests/utils/test_phone_utils.py`
- **Linha não coberta:** 62 (branch de tratamento de erro raro)

### TEST-002: `src/utils/validators.py` (2025-12-04)

**Justificativa da escolha:**
- Módulo de validação central do sistema (~250 linhas)
- Funções públicas: `only_digits`, `normalize_text`, `normalize_whatsapp`, `is_valid_whatsapp_br`, `normalize_cnpj`, `is_valid_cnpj`, `validate_required_fields`, `check_duplicates`, `validate_cliente_payload`
- Type hints já adequados com `Optional[str]`
- Testes existentes completos em `tests/unit/utils/test_utils_validators_fase38.py`

**Status:** ✅ COMPLETO

**Resultados:**
- **70 testes** já existentes (cobrindo todas as funções públicas)
- **Cobertura:** 95.2% (103 statements, 2 miss, 42 branches)
- **Arquivo de testes:** `tests/unit/utils/test_utils_validators_fase38.py`
- **Linhas não cobertas:** branches internos de `check_duplicates` (edge cases SQL)

### TEST-003: `src/utils/paths.py` (2025-12-04)

**Justificativa da escolha:**
- Módulo essencial para resolução de caminhos (~90 linhas)
- Funções públicas: `resource_path()`, `is_bundled()`, `ensure_str_path()`
- Usa `os`, `sys`, `pathlib` para suporte PyInstaller e desenvolvimento
- Testes parciais existentes em `tests/unit/utils/test_paths.py`

**Status:** ✅ COMPLETO

**Resultados:**
- **10 testes** (6 existentes + 4 novos para `ensure_str_path`)
- **Cobertura:** 100% (18 statements, 0 miss, 0 branches)
- **Arquivo de testes:** `tests/unit/utils/test_paths.py`
- **Todas as linhas cobertas**
