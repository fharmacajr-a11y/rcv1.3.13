# CompatPack-03: Path / str Normalization

## 📊 Resumo Executivo

**Data**: 13 de novembro de 2025  
**Branch**: qa/fixpack-04  
**Estado Inicial**: 97 errors (CompatPack-02)  
**Estado Final**: 95 errors

### Redução Alcançada
- **Erros Path-related**: 2 → 0 (-2, -100%)
- **Erros totais**: 97 → 95 (-2, -2.1%)
- **Warnings**: 2803 (estável)

---

## 🎯 Objetivo do CompatPack-03

Tratar **apenas os erros de Path/PathLike/str** que o Pyright apontava em `src/`, `infra/`, `adapters`, usando tipo alias compatível com PEP 519 e mantendo o comportamento do app idêntico.

**Restrições**:
- ❌ Não mexer em lógica de negócio
- ❌ Não alterar fluxos de if/else
- ✅ Apenas ajustar anotações de tipo e normalizar Path → str

---

## 📁 Arquivos Modificados

### 1. Tipo Alias e Helper (`src/utils/paths.py`)

**Adicionado**:
```python
from os import PathLike, fspath
from pathlib import Path
from typing import TypeAlias, Union

# Type alias for path-like objects (PEP 519 compatible)
PathLikeStr: TypeAlias = Union[str, Path, PathLike[str]]

def ensure_str_path(path: PathLikeStr) -> str:
    """Normalize any path-like object to str using os.fspath (PEP 519)."""
    return str(fspath(path))
```

**Referências**:
- PEP 519: https://peps.python.org/pep-0519/
- Stack Overflow: https://stackoverflow.com/questions/60524617/how-to-type-hint-pathlike-objects

**Justificativa**: 
- Segue recomendações da comunidade Python para aceitar `str`, `pathlib.Path`, e qualquer objeto com `__fspath__`
- Usa `os.fspath` como método canônico de conversão (PEP 519)
- Evita repetir `Union[str, Path, os.PathLike[str]]` em múltiplos arquivos

---

## 🔧 Erros Corrigidos

### Erro 1: `src/core/services/path_resolver.py:80`

**Mensagem Pyright**:
```
Argument of type "Path" cannot be assigned to parameter "root" of type "str" 
in function "_find_by_marker"
  "Path" is not assignable to "str"
```

**Correção**:
```python
# ANTES
def _find_by_marker(root: str, pk: int, *, skip_names: set[str] | None = None) -> Optional[str]:
    if not os.path.isdir(root):
        return None
    # ...
    for name in os.listdir(root):
        path = os.path.join(root, name)
```

```python
# DEPOIS
from src.utils.paths import PathLikeStr, ensure_str_path

def _find_by_marker(root: PathLikeStr, pk: int, *, skip_names: set[str] | None = None) -> Optional[str]:
    # Normalize path-like to str (PEP 519)
    root_str = ensure_str_path(root)
    if not os.path.isdir(root_str):
        return None
    # ...
    for name in os.listdir(root_str):
        path = os.path.join(root_str, name)
```

**Análise**:
- Função `_find_by_marker` chamada com `Path(DOCS_DIR)` e `Path(TRASH_DIR)` em alguns contextos
- Normalização imediata na entrada garante compatibilidade com `os.path` APIs
- Sem alteração de lógica: apenas aceita mais tipos de entrada

---

### Erro 2: `src/ui/forms/actions.py:362`

**Mensagem Pyright**:
```
Argument of type "Path" cannot be assigned to parameter "path" of type "str" 
in function "read_pdf_text"
  "Path" is not assignable to "str"
```

**Correção**:
```python
# ANTES
from src.utils.pdf_reader import read_pdf_text

if not (cnpj or razao):
    pdf = find_cartao_cnpj_pdf(base)
    if pdf:
        text = read_pdf_text(pdf) or ""  # pdf é Path
        fields = extract_company_fields(text) if text else {}
```

```python
# DEPOIS
from src.utils.paths import ensure_str_path
from src.utils.pdf_reader import read_pdf_text

if not (cnpj or razao):
    pdf = find_cartao_cnpj_pdf(base)
    if pdf:
        # Normalize Path to str for read_pdf_text (PEP 519)
        text = read_pdf_text(ensure_str_path(pdf)) or ""
        fields = extract_company_fields(text) if text else {}
```

**Análise**:
- `find_cartao_cnpj_pdf` retorna `Path | None`
- `read_pdf_text` (de `src.utils.pdf_reader`) aceita apenas `str`
- Nota: existe outra `read_pdf_text` em `src.utils.file_utils.bytes_utils` que aceita `str | Path`, mas não é a importada aqui
- Conversão explícita resolve tipo sem alterar comportamento

**Alternativa considerada**: Atualizar assinatura de `pdf_reader.read_pdf_text` para aceitar `PathLikeStr`. Rejeitada porque:
1. Função usa `fitz.open(path)` que já aceita path-like internamente
2. Mas a assinatura atual `str` está correta para o uso no projeto
3. Melhor manter conversão explícita no ponto de uso

---

## ✅ Validação

### Build & Runtime
```bash
python main.py
```

**Resultado**:
```
2025-11-13 08:26:13,231 | INFO | startup | Timezone local detectado: America/Sao_Paulo
2025-11-13 08:26:13,467 | INFO | app_gui | App iniciado com tema: flatly
2025-11-13 08:26:20,891 | INFO | src.ui.login_dialog | Login OK: user.id=44900b9f...
2025-11-13 08:26:21,815 | INFO | health | HEALTH: ok=True | itens={'session': {'ok': True}, ...}
```

✅ App inicia normalmente  
✅ Login OK  
✅ Health check OK  
✅ 0 tracebacks ou exceções

---

### Pyright Analysis

**Path-related errors**:
```bash
python devtools/qa/analyze_path_errors.py
```

**Resultado**:
```
Total Pyright errors: 95
Path-related errors in src/infra/adapters: 0
Total: 0 Path-related errors a corrigir
```

✅ Todos os 2 erros de Path eliminados  
✅ 0 novos erros introduzidos  
✅ Erros totais: 97 → 95 (-2)

---

## 📊 Comparação Antes/Depois

| Métrica | CompatPack-02 | CompatPack-03 | Δ | % |
|---------|---------------|---------------|---|---|
| **Total Errors** | 97 | 95 | -2 | -2.1% |
| **Path Errors** | 2 | 0 | -2 | -100% |
| **Total Warnings** | 2803 | 2803 | 0 | 0% |
| **Total Diagnostics** | 2900 | 2898 | -2 | -0.07% |

### Erros Corrigidos por Arquivo

| Arquivo | Erros Antes | Erros Depois | Δ |
|---------|-------------|--------------|---|
| `src/core/services/path_resolver.py` | 1 Path | 0 | -1 ✅ |
| `src/ui/forms/actions.py` | 12 (1 Path) | 11 (0 Path) | -1 ✅ |

---

## 🔍 Análise Técnica

### Por que PEP 519?

PEP 519 (implementado desde Python 3.6) introduziu o protocolo `__fspath__` para permitir que objetos representem caminhos de forma consistente. `pathlib.Path` implementa este protocolo.

**Benefícios**:
1. **Flexibilidade**: Aceita `str`, `Path`, e qualquer objeto com `__fspath__`
2. **Compatibilidade**: `os.fspath` é o método canônico de conversão
3. **Type Safety**: Pyright entende `Union[str, PathLike[str]]` como path-like

**Referências**:
- PEP 519: https://peps.python.org/pep-0519/
- os.fspath: https://docs.python.org/3/library/os.html#os.fspath
- pathlib best practices: https://treyhunner.com/2018/12/why-you-should-be-using-pathlib/

### Por que `ensure_str_path` em vez de `str()`?

```python
# str() funciona, mas não é semântico
path_str = str(path)  # Pode converter qualquer objeto, não apenas paths

# ensure_str_path é explícito e usa fspath (PEP 519)
path_str = ensure_str_path(path)  # Claro: normaliza path-like para str
```

`os.fspath` valida que o objeto é realmente path-like (tem `__fspath__` ou é `str`/`bytes`), lançando `TypeError` caso contrário. `str()` aceita qualquer objeto.

---

## 🚫 Casos Não Corrigidos

**Nenhum**: Todos os 2 erros relacionados a Path foram corrigidos com sucesso.

**Decisões**:
- ✅ Não alterar assinatura de `pdf_reader.read_pdf_text` (mantém compatibilidade com uso existente)
- ✅ Conversão explícita no ponto de uso é mais clara que assinatura genérica

---

## 🎯 Próximos Passos

### CompatPack-04: Type Guards para Unknown
- Adicionar validações para Unknown | None → str (20+ erros)
- Usar TypeGuard para narrowing seguro
- Exemplos:
  - `src/ui/forms/forms.py` (4 erros: Unknown → str)
  - `src/ui/forms/pipeline.py` (4 erros: Unknown → str)
  - `src/core/services/lixeira_service.py` (2 erros: Unknown → Misc)

### CompatPack-05: API Response Typing
- Definir TypedDicts para respostas Supabase (15+ erros)
- Validação em runtime com Pydantic (opcional)
- Exemplos:
  - `adapters/storage/api.py` (3 erros: object → str/bool/Iterable)
  - `src/core/api/api_clients.py` (2 erros: list[Cliente] → List[Dict])

### CompatPack-06: Funções Duplicadas
- Resolver redefinições em actions.py, main_screen.py (5 erros)
- Manter apenas implementação mais robusta
- Análise de qual versão preservar (primeira ou segunda)

---

## 🚀 Conclusão

**CompatPack-03 foi bem-sucedido**:
- ✅ **2 erros Path eliminados** (-100%)
- ✅ **0 alterações em lógica de negócio**
- ✅ **PEP 519 compliance** (os.fspath, PathLikeStr)
- ✅ **App validado**: login OK, health OK, 0 regressões

**Estratégia de Path handling estabelecida**:
1. Usar `PathLikeStr` em assinaturas que aceitam múltiplos tipos
2. Normalizar com `ensure_str_path` na entrada de funções
3. Trabalhar internamente com `str` quando APIs externas exigem

**Progresso geral** (FixPack-01 → CompatPack-03):
- Erros Pyright: 113 → 95 (-18, -15.9%)
- Warnings: 3554 → 2803 (-751, -21.1%)
- Path errors: 2 → 0 (-100%) ✅
- ttkbootstrap stubs: ~70 erros eliminados ✅
