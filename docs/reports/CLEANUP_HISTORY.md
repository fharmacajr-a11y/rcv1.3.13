# Histórico de Limpeza e Consolidação - RC Gestor de Clientes

**Projeto:** RC - Gestor de Clientes  
**Versão:** v1.3.92  
**Branch:** qa/fixpack-04  
**Período:** Novembro - Dezembro de 2025  
**Última atualização:** 7 de dezembro de 2025 (FASE UI-UPLOADS-LEGACY-REMOVAL-01)

---

## 📖 Introdução

Este documento registra as **refatorações estruturais não-funcionais** realizadas no projeto RC - Gestor de Clientes durante as **FASES 1-11** de consolidação e limpeza de código, bem como fases subsequentes de remoção de código legado.

**Para visualização do estado final consolidado, consulte:** [CLEANUP_STATUS_FINAL.md](./CLEANUP_STATUS_FINAL.md)

### **Objetivos**

1. ✅ **Eliminar duplicação:** Código repetido em múltiplos módulos
2. ✅ **Estabelecer funções canônicas:** "Fonte única da verdade" para operações comuns
3. ✅ **Melhorar manutenibilidade:** Mudanças futuras em um único lugar
4. ✅ **Facilitar onboarding:** Desenvolvedores novos sabem onde encontrar utilidades
5. ✅ **Reduzir débito técnico:** Código legado arquivado ou removido
6. ✅ **Remover código morto:** Arquivos deprecated sem uso real em produção

### **Benefícios Alcançados (Atualizado em 07/12/2025)**

- 📉 **-1720 linhas de código duplicado/legado** eliminadas
- 📚 **5 módulos canônicos** criados (`string_utils`, `cnpj_norm`, `text_normalization`, etc.)
- 🧪 **+162 novos testes** criados (150 para funções canônicas + 12 para upload helpers)
- 🗂️ **7 arquivos LEGACY** arquivados com segurança
- 🗑️ **2 módulos legados removidos** (browser antigo 1550 linhas + wrapper 20 linhas)
- 📝 **Documentação consolidada** (este documento + TEST_ARCHITECTURE.md + devlogs)

---

## 📅 Linha do Tempo das Fases

### **FASE UI-UPLOADS-LEGACY-REMOVAL-01 – Remoção do Browser Legado**

**Data:** 7 de dezembro de 2025  
**Devlog:** [devlog-ui-uploads-legacy-removal-01.md](./devlog-ui-uploads-legacy-removal-01.md)

#### **Problema Identificado**

Após a migração UP-03, permanecia código legado não utilizado:
- `src/ui/files_browser/main.py` (1550 linhas) - browser antigo DEPRECATED
- `src/ui/files_browser.py` (20 linhas) - wrapper deprecated
- `open_files_browser_legacy` exportado mas **nunca importado** em produção

**Impacto:**
- ❌ Custo cognitivo desnecessário
- ❌ Risco de confusão entre browser novo e legado
- ❌ 1570 linhas de código morto

#### **Solução Implementada**

1. ✅ **Removido browser legado:** `src/ui/files_browser/main.py` (1550 linhas)
2. ✅ **Removido wrapper deprecated:** `src/ui/files_browser.py` (20 linhas)
3. ✅ **Atualizado `__init__.py`:** removida exportação de `open_files_browser_legacy`
4. ✅ **Mantidos utilities:** `utils.py` e `constants.py` (usados pelo browser novo)

#### **Validação**

- ✅ **265 testes** passando (26 utils + 195 uploads + 42 app_actions + 2 wrappers)
- ✅ **0 regressões** detectadas
- ✅ **API pública mantida:** `from src.modules.uploads import open_files_browser`
- ✅ **Browser novo funcional** em todos os fluxos (menu, hub, auditoria)

#### **Métricas**

| Categoria | Removido |
|-----------|----------|
| Browser legado | -1550 linhas |
| Wrapper deprecated | -20 linhas |
| **Total** | **-1570 linhas** 🎉 |

---

### **FASE UI-CLIENTES-FORM-HEADLESS-01 – Extração de Lógica de Upload**

**Data:** 7 de dezembro de 2025  
**Devlog:** [devlog-ui-clientes-form-headless-01.md](./devlog-ui-clientes-form-headless-01.md)

#### **Problema Identificado**

`client_form.py` (~921 linhas) misturava lógica de negócio com UI Tkinter:
- Implementação inline de upload (150 linhas) duplicando lógica
- Montagem de payloads, validação, upload em closures aninhadas
- Difícil testabilidade sem mockar Tkinter

#### **Solução Implementada**

1. ✅ **Criado módulo headless:** `client_form_upload_helpers.py` (218 linhas)
   - `execute_upload_flow()` - fluxo completo de upload
   - `_format_validation_errors()` - formatação de erros
2. ✅ **Refatorado `_salvar_e_enviar()`:** delegação para helpers
3. ✅ **Removidos 7 imports desnecessários**
4. ✅ **Criados 12 novos testes** cobrindo fluxo de upload

#### **Validação**

- ✅ **198 testes** de forms passando (186 existentes + 12 novos)
- ✅ **0 regressões**
- ✅ **Ruff:** 100% clean

#### **Métricas**

| Categoria | Antes | Depois | Δ |
|-----------|-------|--------|---|
| `client_form.py` | 921 | 799 | -122 |
| Novo módulo headless | 0 | 218 | +218 |
| Novos testes | 0 | 12 | +12 |

---

### **FASE 1 – only_digits (Extração de Dígitos)**

**Data:** Novembro de 2025  
**Módulo criado:** `src/core/string_utils.py`

#### **Problema Identificado**

Implementações duplicadas de `only_digits` em **6 arquivos diferentes**:
- `src/utils/text_utils.py`
- `src/utils/phone_utils.py`
- `src/utils/validators.py`
- `src/app_utils.py`
- `src/modules/clientes/viewmodel.py`
- `src/helpers/formatters.py` (como `_only_digits`)

**Similaridade:** ~90% de código idêntico usando `re.sub(r"\D", "", s)`

#### **Solução Implementada**

1. ✅ **Criado módulo canônico:** `src/core/string_utils.py`
   ```python
   def only_digits(s: str | None) -> str:
       """Extrai apenas dígitos de uma string."""
       if s is None:
           return ""
       return _ONLY_DIGITS_REGEX.sub("", s)
   ```

2. ✅ **Convertidos duplicatas em wrappers:**
   - Todas as 6 implementações agora delegam para `src.core.string_utils.only_digits`
   - Mantida compatibilidade total com código existente

3. ✅ **Criado teste canônico:** `tests/unit/core/test_string_utils.py` (8 testes)

#### **Validação**

- ✅ **550+ testes** passando após migração
- ✅ **0 regressões** detectadas
- ✅ **Linting:** 0 erros

---

### **FASE 2 – format_cnpj (Formatação de CNPJ)**

**Data:** Novembro de 2025  
**Módulo canônico:** `src/helpers/formatters.py`

#### **Problema Identificado**

Implementações duplicadas de `format_cnpj` em **7 arquivos**:
- `src/utils/text_utils.py`
- `src/modules/passwords/utils.py`
- `src/modules/uploads/helpers.py`
- `src/ui/pick_mode.py`
- `src/modules/clientes/client_picker.py`
- `src/modules/main_window/main_frame.py`
- `src/modules/uploads/upload_flow.py`

**Similaridade:** ~85%, com variações no tratamento de None/inválidos

#### **Solução Implementada**

1. ✅ **Consolidado em:** `src/helpers/formatters.format_cnpj`
   - Aceita: `str | int | float | None`
   - Formato: `XX.XXX.XXX/XXXX-XX`
   - Trata None, valores vazios e inválidos consistentemente

2. ✅ **Convertidos 7 arquivos** para delegar à função canônica

3. ✅ **Criado teste canônico:** `tests/unit/helpers/test_format_cnpj_canonical_fase2.py` (20 testes)

4. ✅ **Corrigidos 5 testes pré-existentes** não relacionados:
   - 3 testes obsoletos marcados como `skip`
   - 2 testes com asserções incorretas corrigidos

#### **Validação**

- ✅ **680 testes** passando (51 específicos de `format_cnpj`)
- ✅ **Comportamento canônico** documentado com tabela de entrada/saída

---

### **FASE 3 – CNPJ (Normalização e Validação com DV)**

**Data:** Novembro de 2025  
**Módulo criado:** `src/core/cnpj_norm.py`

#### **Problema Identificado**

Lógica de CNPJ espalhada em múltiplos arquivos:
- `normalize_cnpj` em `validators.py` e `text_utils.py` (duplicado)
- `normalize_cnpj_digits` (extração de dígitos apenas)
- `is_valid_cnpj` validando apenas **comprimento**, não **DV** (dígito verificador)

**Risco:** CNPJs inválidos sendo aceitos como válidos

#### **Solução Implementada**

1. ✅ **Criado módulo canônico:** `src/core/cnpj_norm.py`
   - `normalize_cnpj(raw)` - Normaliza e valida
   - `normalize_cnpj_digits(raw)` - Apenas dígitos
   - `is_valid_cnpj(cnpj)` - **Valida DV completo** (algoritmo oficial)

2. ✅ **BREAKING CHANGE:** `is_valid_cnpj` agora valida DV
   - Antes: `len(digits) == 14` (aceitava qualquer 14 dígitos)
   - Depois: Valida DV usando algoritmo módulo 11

3. ✅ **Convertidos wrappers:**
   - `src/utils/validators.py` → delega para `core.cnpj_norm`
   - `src/utils/text_utils.py` → delega para `core.cnpj_norm`

4. ✅ **Corrigidos testes com CNPJs inválidos:**
   - Substituídos CNPJs falsos por válidos: `11222333000165`, `12345678000110`

5. ✅ **Criado teste canônico:** `tests/unit/core/test_cnpj_norm_canonical_fase3.py` (43 testes)

#### **Validação**

- ✅ **216 testes de CNPJ** passando
- ✅ **76 testes** de normalização/validação específicos
- ✅ **Validação DV:** Agora rejeita CNPJs com DV incorreto

---

### **FASE 4 – Normalização de Texto / Acentos**

**Data:** Dezembro de 2025  
**Módulo criado:** `src/core/text_normalization.py`

#### **Problema Identificado**

Implementações duplicadas de remoção de diacríticos (acentos) em **6 arquivos**:
- `src/core/textnorm.py` → `_strip_diacritics` (NFD)
- `src/core/cnpj_norm.py` → `_strip_diacritics` (NFD)
- `src/core/storage_key.py` → `_strip_diacritics` (NFD)
- `src/shared/subfolders.py` → `_strip_diacritics` (NFD)
- `src/utils/text_utils.py` → `normalize_ascii` (NFKD)
- `adapters/storage/supabase_storage.py` → `_strip_accents` (NFKD)

**Divergência técnica:**
- 4 arquivos usando **NFD** (Canonical Decomposition)
- 2 arquivos usando **NFKD** (Compatibility Decomposition)

#### **Solução Implementada**

1. ✅ **Criado módulo canônico:** `src/core/text_normalization.py`
   ```python
   def strip_diacritics(value: str | None) -> str:
       """Remove acentos usando NFD (preserva semântica)."""

   def normalize_ascii(value: str | None) -> str:
       """Remove acentos e converte para ASCII puro."""
   ```

2. ✅ **Decisão técnica:** NFD como padrão (preserva mais significado semântico)

3. ✅ **Convertidos 6 arquivos** para delegar à implementação canônica

4. ✅ **Corrigidos testes que acessavam `_strip_accents` privado:**
   - `test_supabase_storage_fase02.py` - Migrado para testar `normalize_key_for_storage`
   - `test_adapters_supabase_storage_fase37.py` - Atualizado fixture

5. ✅ **Criado teste canônico:** `tests/unit/core/test_text_normalization_canonical_fase4.py` (39 testes)

#### **Validação**

- ✅ **107 testes** passando relacionados a normalização de texto
- ✅ **4 imports não usados** removidos pelo `ruff --fix`

---

### **FASE 5 – Formatação de Datas**

**Data:** Dezembro de 2025  
**Módulo canônico:** `src/helpers/formatters.py`

#### **Problema Identificado**

Duplicação entre `fmt_data` e `fmt_datetime_br`:
- **`fmt_data`** (em `app_utils.py`) - Aceita `str | None`
- **`fmt_datetime_br`** (em `formatters.py`) - Aceita `datetime | date | str | int | float | None`

**Similaridade:** ~85%, mesma saída esperada (DD/MM/YYYY - HH:MM:SS)

**Diferença:** `fmt_datetime_br` é **mais robusta** (múltiplos formatos de entrada)

#### **Solução Implementada**

1. ✅ **Aprimorado `fmt_datetime_br`:**
   - Adicionado tratamento de whitespace (retorna `""` para `"   "`)
   - Aceita todos os tipos que `fmt_data` aceitava + mais

2. ✅ **Convertido `fmt_data` em wrapper deprecado:**
   ```python
   def fmt_data(iso_str: str | None) -> str:
       """[DEPRECATED] Use fmt_datetime_br de src.helpers.formatters."""
       from src.helpers.formatters import fmt_datetime_br
       return fmt_datetime_br(iso_str)
   ```

3. ✅ **Migrados 2 arquivos de produção:**
   - `src/modules/clientes/viewmodel.py`
   - `src/modules/lixeira/views/lixeira.py`

4. ✅ **Criado teste canônico:** `tests/unit/helpers/test_formatters_datetime_fase5.py` (25 testes)
   - Incluindo testes de **compatibilidade** com `fmt_data`

#### **Validação**

- ✅ **51 testes** passando relacionados a formatação de data
- ✅ **100% compatibilidade** entre `fmt_data` e `fmt_datetime_br`
- ✅ **Decisão:** Manter `fmt_data` como wrapper para código legado

---

### **FASE 6 – Arquivamento de Testes LEGACY**

**Data:** 7 de dezembro de 2025  
**Estrutura criada:** `tests/archived/`

#### **Problema Identificado**

7 arquivos de teste com prefixo `LEGACY_test_*`:
- 6 arquivos em `tests/unit/modules/passwords/`
- 1 arquivo em `tests/unit/modules/clientes/views/`

**Características:**
- ✅ Já tinham `pytest.skip(allow_module_level=True)`
- ✅ Já estavam em `norecursedirs` (não executados)
- ✅ Baseados em arquitetura pré-refatoração (REF-001)
- ✅ Todos possuíam substitutos oficiais mais recentes

#### **Solução Implementada**

1. ✅ **Criada estrutura de arquivamento:**
   ```
   tests/archived/
   ├── README.md       # Documentação do diretório
   ├── INDEX.md        # Índice detalhado com mapeamento
   ├── passwords/      # 6 arquivos LEGACY de Senhas
   └── clientes/       # 1 arquivo LEGACY de Obrigações
   ```

2. ✅ **Movidos 7 arquivos** de `tests/unit/modules/` para `tests/archived/`

3. ✅ **Atualizado `pytest.ini`:**
   ```ini
   # Antes
   norecursedirs = ... tests/unit/modules/passwords

   # Depois
   norecursedirs = ... tests/archived
   ```

4. ✅ **Removida exclusão desnecessária** de `tests/unit/modules/passwords`
   - Diretório agora contém apenas testes oficiais

5. ✅ **Documentados mapeamentos:**
   - Cada arquivo LEGACY → Teste oficial substituto
   - Motivo do arquivamento
   - Referências para consulta

#### **Arquivos Movidos**

| Arquivo LEGACY | Teste Substituto Oficial | Status |
|----------------|--------------------------|--------|
| `LEGACY_test_helpers.py` | `tests/modules/passwords/test_passwords_actions.py` | ✅ Arquivado |
| `LEGACY_test_passwords_service.py` | `tests/modules/passwords/test_passwords_service.py` | ✅ Arquivado |
| `LEGACY_test_passwords_controller.py` | `tests/unit/modules/passwords/test_passwords_controller.py` | ✅ Arquivado |
| `LEGACY_test_passwords_screen_ui.py` | `tests/unit/modules/passwords/test_passwords_controller.py` | ✅ Arquivado |
| `LEGACY_test_passwords_repository_fase53.py` | `tests/modules/passwords/test_passwords_service.py` | ✅ Arquivado |
| `LEGACY_test_passwords_client_selection_feature001.py` | `tests/modules/passwords/test_passwords_actions.py` | ✅ Arquivado |
| `LEGACY_test_obligations_integration.py` | `tests/unit/modules/hub/views/test_dashboard_center.py` | ✅ Arquivado |

**Contexto:** Funcionalidade de Obrigações migrou do módulo Clientes para Hub na v1.3.61

#### **Validação**

- ✅ **0 arquivos LEGACY** coletados pelo pytest
- ✅ **119 testes oficiais** passando (senhas + hub/obrigações)
- ✅ **pytest.ini** limpo e simplificado

---

## 🎯 Funções Canônicas Consolidadas

### **Resumo Executivo**

| Função Canônica | Localização | Substituiu | Testes |
|-----------------|-------------|------------|--------|
| `only_digits` | `src/core/string_utils.py` | 6 duplicatas | 8 testes |
| `format_cnpj` | `src/helpers/formatters.py` | 7 duplicatas | 20 testes |
| `normalize_cnpj`<br>`normalize_cnpj_digits`<br>`is_valid_cnpj` | `src/core/cnpj_norm.py` | 3 variações | 43 testes |
| `strip_diacritics`<br>`normalize_ascii` | `src/core/text_normalization.py` | 6 duplicatas | 39 testes |
| `fmt_datetime_br` | `src/helpers/formatters.py` | `fmt_data` (deprecado) | 25 testes |

**Total:**
- ✅ **5 módulos canônicos** criados
- ✅ **25 duplicatas** eliminadas
- ✅ **135 testes** novos criados
- ✅ **~150 linhas** de código duplicado removidas

---

## 📋 Diretrizes para o Futuro

### **1. Criação de Novos Helpers**

✅ **FAZER:**
- Colocar helpers genéricos em `src/core/` ou `src/helpers/`
- Documentar com docstring completa (tipo, exemplos, edge cases)
- Criar testes canônicos em `tests/unit/core/` ou `tests/unit/helpers/`

❌ **EVITAR:**
- Criar versões locais em `utils/` de módulos específicos
- Duplicar lógica que já existe em `core/` ou `helpers/`

**Exemplo:**
```python
# ❌ NÃO FAZER
# src/modules/meu_modulo/utils.py
def only_digits(s: str) -> str:  # Duplicação!
    return re.sub(r"\D", "", s)

# ✅ FAZER
# src/modules/meu_modulo/business_logic.py
from src.core.string_utils import only_digits  # Reutilizar!
```

### **2. Nomenclatura de Funções**

**Padrões estabelecidos:**

| Padrão | Uso | Exemplo |
|--------|-----|---------|
| `normalize_*` | Limpeza/padronização de dados | `normalize_cnpj`, `normalize_ascii` |
| `format_*` | Formatação para exibição | `format_cnpj`, `format_datetime` |
| `is_valid_*` | Validação booleana | `is_valid_cnpj`, `is_valid_email` |
| `strip_*` | Remoção de caracteres | `strip_diacritics`, `strip_whitespace` |

❌ **EVITAR:** Criar novas convenções (`fmt_*` está deprecado, use `format_*`)

### **3. Wrappers vs. Duplicação**

**Quando criar wrapper:**
- ✅ Para compatibilidade com código existente
- ✅ Para adaptar assinatura de função canônica
- ✅ Para deprecação gradual

**Exemplo de wrapper válido:**
```python
def fmt_data(iso_str: str | None) -> str:
    """[DEPRECATED] Use fmt_datetime_br."""
    from src.helpers.formatters import fmt_datetime_br
    return fmt_datetime_br(iso_str)
```

### **4. Refatorações Grandes**

**Checklist antes de refatorar:**

1. ✅ Documentar em devlog (`docs/devlog-<tema>-<milestone>.md`)
2. ✅ Executar testes **antes** da mudança (baseline)
3. ✅ Criar testes canônicos para nova implementação
4. ✅ Migrar duplicatas para wrappers
5. ✅ Validar com pytest focado
6. ✅ Executar linters (ruff, pyright)
7. ✅ Se envolver arquivamento de testes, atualizar `tests/archived/INDEX.md`

### **5. Linters e Type Checkers**

**Ferramentas obrigatórias:**

```bash
# Linting (PEP 8, imports, etc.)
ruff check src/ tests/

# Auto-fix de problemas simples
ruff check --fix src/ tests/

# Type checking estático
pyright src/
```

**Configuração:**
- `ruff.toml` - Regras de linting
- `pyrightconfig.json` - Regras de tipos

**Boas práticas:**
- ✅ Executar ruff antes de cada commit
- ✅ Manter 0 erros de pyright em código novo
- ✅ Usar `# noqa: <code>` apenas quando inevitável (documentar motivo)

### **6. Documentação de Testes**

**Ao criar testes:**

```python
class TestMinhaFuncionalidade:
    """Testes para [descrição da funcionalidade].

    Cobertura:
    - Caso feliz (entrada válida)
    - Casos de erro (None, vazio, inválido)
    - Edge cases específicos do domínio
    """

    def test_quando_input_valido_entao_retorna_esperado(self):
        """Deve [comportamento esperado] quando [condição]."""
        # Arrange
        input_data = ...
        expected = ...

        # Act
        result = minha_funcao(input_data)

        # Assert
        assert result == expected
```

### **7. Arquivamento de Testes**

**Quando arquivar:**
- ✅ Teste baseado em código/arquitetura descontinuada
- ✅ Já existe substituto oficial completo
- ✅ Teste não reflete mais comportamento atual

**Processo:**
1. Mover para `tests/archived/<módulo>/`
2. Adicionar entrada em `tests/archived/INDEX.md`
3. Referenciar teste oficial substituto
4. Confirmar que pytest não coleta mais o arquivo

---

## 📊 Impacto Quantitativo

### **Antes das Fases 1-6**

- 📦 **~25 duplicatas** de funções espalhadas
- 🔴 **Risco alto** de comportamentos inconsistentes
- 🐛 **Bugs** em validação (CNPJ aceita DV inválido)
- 📝 **Documentação fragmentada**
- 🗂️ **7 arquivos LEGACY** no caminho de execução

### **Depois das Fases 1-6**

- ✅ **5 módulos canônicos** bem definidos
- ✅ **~135 novos testes** criados
- ✅ **0 duplicatas** - apenas wrappers documentados
- ✅ **Validação CNPJ correta** (DV verificado)
- ✅ **Testes LEGACY arquivados** com segurança
- ✅ **Documentação consolidada** (este doc + TEST_ARCHITECTURE.md)

### **Métricas de Qualidade**

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Duplicatas de código | 25 | 0 | ✅ -100% |
| Linhas duplicadas | ~150 | 0 | ✅ -100% |
| Testes canônicos | 0 | 135 | ✅ +135 |
| Testes LEGACY ativos | 7 | 0 | ✅ -100% |
| Módulos canônicos | 0 | 5 | ✅ +5 |

---

### **FASE 7 – Documentação de Arquitetura de Testes**

**Data:** 7 de dezembro de 2025  
**Documento criado:** `TEST_ARCHITECTURE.md`

#### **Objetivo**

Consolidar documentação sobre a arquitetura de testes do projeto, incluindo estrutura de pastas, níveis de teste, e boas práticas.

#### **Resultado**

✅ `TEST_ARCHITECTURE.md` criado com seções:
- Estrutura de pastas (`unit/`, `modules/`, `integration/`, `archived/`)
- Níveis de teste (unitário, funcional, integração)
- Padrões de nomenclatura e descoberta
- Configuração do pytest

---

### **FASE 8 – Naming Conventions (Ruff N8xx)**

**Data:** 7 de dezembro de 2025  
**Documento criado:** `NAMING_GUIDELINES.md`

#### **Objetivo**

Ativar regras de naming PEP 8 (`N8xx`) no Ruff e criar documentação sobre convenções de nomes.

#### **Resultado**

✅ Ruff configurado com `select = ["E", "F", "N"]`  
✅ 44 violações de naming mapeadas  
✅ `NAMING_GUIDELINES.md` criado com:
- Prefixos semânticos (`normalize_*`, `format_*`, `is_valid_*`)
- Padrão PEP 8 (snake_case, CamelCase, UPPER_SNAKE_CASE)
- Prefixos deprecados (`fmt_*` → `format_*`)

**Devlog:** `docs/devlog-naming-lint-fase8.md`

---

### **FASE 9 – Auto-fix Imports (F401)**

**Data:** 7 de dezembro de 2025

#### **Objetivo**

Remover imports não usados identificados na FASE 8.

#### **Resultado**

✅ **17 erros F401** corrigidos automaticamente via `ruff check --fix`  
✅ **0 erros restantes**  
✅ **12 arquivos** modificados (4 produção, 8 testes)

**Devlog:** `docs/devlog-lint-fase9-ruff-fix-imports.md`

---

### **FASE 10 – Naming Simples (N806, N818, N813, N807)**

**Data:** 7 de dezembro de 2025

#### **Objetivo**

Corrigir violações de naming "simples e seguras" (exceto N802 - renomear funções).

#### **Resultado**

✅ **69% de redução** em violações N8xx (39 → 12 erros)  
✅ **N818** (exceções sem `Error`) - 7 corrigidas, 0 restantes  
✅ **N813** (import CamelCase) - 1 corrigida, 0 restantes  
✅ **N807** (função com `__`) - 1 corrigida, 0 restantes  
✅ **N806** (variáveis UPPERCASE) - 18 corrigidas, 10 restantes (justificadas)

**Restantes justificados:** Constantes Win32/Qt definidas por APIs externas

**Devlog:** `docs/devlog-naming-fase10-simple.md`

---

### **FASE 11 – Renomear fmt_datetime → format_datetime**

**Data:** 7 de dezembro de 2025

#### **Objetivo**

Alinhar nome de função global com padrão `format_*` (PEP 8), eliminando violação N802.

#### **Resultado**

✅ `format_datetime` criado como função canônica  
✅ `fmt_datetime` convertido em wrapper deprecado  
✅ Testes migrados para usar novo nome  
✅ 1 violação N802 eliminada

**Devlog:** `docs/devlog-naming-fase11-format-datetime.md`

---

## 🔗 Referências

### **Documentação Interna**

- [TEST_ARCHITECTURE.md](./TEST_ARCHITECTURE.md) - Arquitetura de testes
- [tests/archived/INDEX.md](../tests/archived/INDEX.md) - Índice de arquivos LEGACY
- [tests/archived/README.md](../tests/archived/README.md) - Guia de uso de arquivados

### **Devlogs Relacionados**

- `docs/devlog-tests-passwords-legacy-ms1.md` - Desativação de testes antigos de Senhas (v1.3.47)
- `docs/devlog-qa-global-ms1.md` - Análise global de qualidade
- Outros devlogs específicos de refatorações

### **Referências Externas**

- [pytest Documentation](https://docs.pytest.org) - Framework de testes
- [Real Python - Testing Best Practices](https://realpython.com/pytest-python-testing/) - Boas práticas
- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/) - Guia de estilo Python

---

## 🎓 Lições Aprendidas

### **1. Consolidação incremental funciona**

Fazer 6 fases pequenas e focadas foi **mais eficaz** que uma grande refatoração monolítica.

### **2. Testes são essenciais**

Ter testes antes de refatorar permitiu **validação contínua** sem regressões.

### **3. Documentação é investimento**

Tempo gasto documentando (devlogs, este doc) **economiza horas** futuras de investigação.

### **4. Wrappers facilitam migração**

Manter compatibilidade com wrappers permitiu **migração gradual** sem quebrar código existente.

### **5. Arquivar ≠ Deletar**

Preservar testes LEGACY para referência **não custa quase nada** e pode ser valioso futuramente.

---

**Última atualização:** 7 de dezembro de 2025 (FASE 12 - Fechamento Final)  
**Responsáveis:** Equipe de Qualidade - RC Gestor
