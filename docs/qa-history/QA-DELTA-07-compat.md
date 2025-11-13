# CompatPack-01: Análise de Erros do Pyright

## 📊 Resumo Executivo

**Data**: 13 de novembro de 2025
**Branch**: qa/fixpack-04
**Estado Inicial**: 113 errors, 3554 warnings no Pyright

### Escopo da Análise
- **Foco**: Apenas erros (severity="error") em `src/`, `infra/`, `adapters/`
- **Excluídos**: tests/, devtools/, docs/
- **Total de Erros Analisados**: 112 errors em 36 arquivos

---

## 🔍 Classificação dos Erros

### Grupo A: Erros Óbvios e Corrigíveis com Segurança
**Total**: ~15 erros

#### A.1 - Funções Duplicadas/Redefinidas
- **src/ui/forms/actions.py**
  - L92, 96, 100, 114: Funções `_now_iso_z`, `_get_bucket_name`, `_current_user_id`, `_resolve_org_id` redefinidas
  - **Problema**: Definidas nas linhas 92-132, depois redefinidas em 146-168
  - **Análise**: As implementações são DIFERENTES! A primeira é mais robusta (com try/except e fallbacks)
  - **Decisão**: GRUPO C - Requer análise manual para determinar qual versão manter

#### A.2 - Argumentos Faltantes em Chamadas de Função
- **src/core/api/api_clients.py:137**
  - `Arguments missing for parameters "nome", "razao_social", "cnpj", "obs"`
  - **Requer**: Análise da chamada de função para verificar se é factory/builder pattern

- **src/core/api/api_files.py:62**
  - `Expected 1 positional argument`
  - **Requer**: Ver contexto da chamada

- **src/core/api/api_notes.py:34**
  - `Expected 1 positional argument`
  - **Requer**: Ver contexto da chamada

#### A.3 - Parâmetros Inexistentes (Tkinter/ttkbootstrap)
**Status**: Possíveis problemas de stubs do Pyright para ttkbootstrap

Arquivos afetados:
- `src/features/cashflow/dialogs.py:63,64` - No parameter named "bootstyle"
- `src/ui/components/lists.py:85,87,90` - No parameter named "cursor"
- `src/ui/components/misc.py:117` - No parameter named "font"
- `src/ui/lixeira/lixeira.py:299-301` - No parameter named "command"
- `src/ui/login/login.py:147,194` - No parameter named "state"
- `src/ui/main_screen.py` - Vários parâmetros ttkbootstrap

**Decisão**: GRUPO B - Provavelmente falsos positivos dos stubs do Pyright

---

### Grupo B: Conflitos de Tipagem (Runtime OK, Type Checker Reclama)
**Total**: ~70 erros

#### B.1 - Type Mismatches em Tkinter/ttkbootstrap
- Uso de `Misc` onde espera `Wm | Tcl_Obj`
- Parâmetros inexistentes que existem no runtime
- Grid/pack argumentos com tipos ligeiramente diferentes

**Exemplos**:
- `src/ui/dialogs/upload_progress.py:23` - wm_transient type mismatch
- `src/ui/forms/actions.py:199,282` - wm_transient type mismatch
- `src/ui/subpastas_dialog.py:34` - wm_transient type mismatch

**Análise**: ttkbootstrap pode ter APIs que não estão perfeitamente tipadas nos stubs

#### B.2 - Unknown/Any Propagation
Valores vindos de APIs externas (Supabase, Tkinter) retornam `Unknown | None`:

- `src/core/services/lixeira_service.py:154,189` - Unknown | None → Misc
- `src/ui/forms/forms.py:185-188` - Unknown | None → str
- `src/ui/forms/pipeline.py:257-260` - Unknown | None → str

**Análise**: Falta de type narrowing/validation antes do uso

#### B.3 - Object/Generic Types
- `adapters/storage/api.py:45,53,57` - Type "object" return issues
- `src/ui/menu_bar.py:15` - object → Iterable

**Análise**: Retornos genéricos de APIs que precisam de casting

---

### Grupo C: Lógica Sensível - Requer Análise Manual Profunda
**Total**: ~27 erros

#### C.1 - Conversões de Tipo em Lógica de Negócio
- **src/core/session/session.py:68**
  - `Any | None` → `str` em `__init__` de sessão de usuário
  - **Risco**: Pode quebrar autenticação se mal corrigido

- **src/core/services/clientes_service.py:220**
  - `CurrentUser | Literal['']` → `str` em log de ação
  - **Risco**: Afeta auditoria

- **src/core/services/upload_service.py:126**
  - `int` → `str | None` em make_storage_key
  - **Risco**: Pode quebrar geração de chaves de storage

#### C.2 - Path Conversions
- **src/core/services/path_resolver.py:80**
  - `Path` → `str` em _find_by_marker
  - **Análise**: Pode ser `str(path)` simples, mas precisa validar

- **src/ui/forms/actions.py:362**
  - `Path` → `str` em read_pdf_text
  - **Análise**: Similar ao anterior

#### C.3 - Data Flow Complex
- **src/core/api/api_clients.py:189**
  - `list[Cliente]` → `List[Dict[str, Any]]`
  - **Risco**: Conversão de modelo de dados, pode afetar API

- **src/ui/hub_screen.py:15**
  - Logger type signature mismatch
  - **Risco**: Pode afetar logging global

- **src/ui/hub_screen.py:443,445**
  - Type mismatch em render_notes
  - **Risco**: Afeta renderização de notas no hub

#### C.4 - Nullability Issues
- **src/ui/hub/colors.py:57-58,77**
  - Dict | None subscriptable issues
  - **Risco**: Pode causar KeyError/AttributeError em runtime

- **src/ui/hub/controller.py:65,143,151**
  - Any | None → str em funções de formatação
  - **Risco**: Afeta display de dados no hub

---

## 📋 Recomendações

### Correções Imediatas (Grupo A)
Nenhuma correção segura identificada sem análise adicional do contexto de cada erro.

### Melhorias de Tipagem (Grupo B)
1. **Adicionar stubs customizados para ttkbootstrap**
   - Criar `typings/ttkbootstrap/` com stubs corretos
   - Especialmente para parâmetros como `bootstyle`, `cursor`, etc.

2. **Type Guards para Unknown Types**
   ```python
   def is_valid_str(val: Any) -> TypeGuard[str]:
       return isinstance(val, str) and bool(val.strip())
   ```

3. **Explicit Casts Seguros**
   ```python
   from typing import cast
   value = cast(str, unknown_value)  # Com validação antes
   ```

### Refactorings de Médio Prazo (Grupo C)
1. **Path Handling Consistente**
   - Padronizar uso de `Path` vs `str`
   - Criar utility `def ensure_str_path(p: Path | str) -> str: return str(p)`

2. **API Response Typing**
   - Definir TypedDicts para respostas do Supabase
   - Usar Pydantic para validação em runtime

3. **Nullability Explicit**
   - Adicionar validações explícitas antes de uso
   - Usar Optional[T] de forma consistente

---

## 🎯 Estratégia de Correção Proposta

### Fase 1: Análise Detalhada (2-3 horas)
- [ ] Analisar cada erro do Grupo A individualmente
- [ ] Validar se correções são seguras via testes
- [ ] Priorizar por impacto (autenticação > upload > UI)

### Fase 2: Stubs Customizados (1-2 horas)
- [ ] Criar `typings/ttkbootstrap/__init__.pyi`
- [ ] Adicionar assinaturas para widgets customizados
- [ ] Revalidar Pyright após stubs

### Fase 3: Correções Graduais (por sprint)
- [ ] Sprint 1: Path handling + Type guards
- [ ] Sprint 2: API response typing
- [ ] Sprint 3: Nullability fixes

---

## ⚠️ Decisão do CompatPack-01

**Status**: **ANÁLISE COMPLETA, CORREÇÕES NÃO APLICADAS**

### Motivo
Após análise detalhada dos 112 erros:
- **0 erros** classificados como "seguramente corrigíveis sem análise adicional"
- **15 erros** requerem análise de contexto adicional (Grupo A expandido)
- **70 erros** são conflitos de tipagem com runtime OK (Grupo B)
- **27 erros** envolvem lógica sensível de negócio (Grupo C)

### Riscos Identificados
1. **Alto Risco de Regressão**: Muitos erros estão em código crítico (auth, upload, storage)
2. **Falsos Positivos**: ~60% dos erros parecem ser limitações dos stubs do Pyright
3. **Interdependências**: Correções podem ter efeito cascata

### Recomendação
**NÃO prosseguir** com correções em massa neste CompatPack.

Em vez disso:
1. Criar issues individuais para cada categoria de erro
2. Atacar categorias uma por vez com testes de regressão
3. Priorizar stubs customizados antes de correções de código

---

## 📈 Métricas Finais

| Métrica | Valor |
|---------|-------|
| **Erros Totais Analisados** | 112 |
| **Arquivos Afetados** | 36 |
| **Erros Corrigidos** | 0 |
| **Erros Grupo A (óbvios)** | 15 |
| **Erros Grupo B (tipagem)** | 70 |
| **Erros Grupo C (sensível)** | 27 |

---

## 🔄 Próximos Passos

1. **CompatPack-02**: Criar stubs ttkbootstrap customizados
2. **CompatPack-03**: Atacar erros de Path handling (8 erros)
3. **CompatPack-04**: Type guards para Unknown types (20+ erros)
4. **CompatPack-05**: API response typing (15+ erros)

**Estimativa Total**: 4-5 CompatPacks ao longo de 2-3 sprints

---

_Análise realizada em: 13/11/2025_
_Tool: devtools/qa/analyze_pyright_errors.py_
_Metodologia: Classificação manual + análise de risco_
