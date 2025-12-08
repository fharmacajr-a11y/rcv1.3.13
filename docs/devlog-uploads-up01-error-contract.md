# UP-01: Contrato de Erros do Módulo Uploads

**Status:** ✅ Concluído  
**Data:** 2025-01-XX  
**Objetivo:** Fechar e documentar o contrato oficial de erros do módulo uploads, alinhando testes à Opção A (exceções de domínio na API com raw exceptions preservadas em `__cause__`).

---

## Contexto

Após executar a suíte global de testes, identificamos 3 testes falhando no módulo uploads:

1. `test_upload_adapter_exception_propagates` - esperava `RuntimeError` mas recebia `UploadError`
2. `test_builder_without_kwargs_fails_with_kwargs_passed` - esperava `TypeError` mas recebia `UploadError`
3. `test_upload_items_with_adapter_duplicate_error` - erro 409 duplicate estava sendo adicionado a `failures` incorretamente

**Problema raiz:**  
- Não havia documentação clara do contrato de erros
- Testes esperavam exceções brutas (`RuntimeError`, `TypeError`) em vez de exceções de domínio
- `classify_upload_exception()` não preservava a exceção original em `__cause__`
- Verificação de duplicatas em `repository.py` procurava pela palavra "duplicate" na mensagem amigável (que não continha essa palavra)

---

## Decisão de Design: Opção A

**Contrato oficial:**  
A API de domínio (`repository.py`, `upload_retry.py`) expõe **apenas exceções de domínio** (`UploadError` e subclasses). Exceções brutas (`RuntimeError`, `TypeError`, `HTTPError`, etc.) são preservadas em `__cause__` para debug/logging, mas não vazam diretamente para o chamador.

**Hierarquia de exceções:**
```
UploadError (base)
├── UploadValidationError (arquivo inválido antes do upload)
├── UploadNetworkError (falha de conexão/timeout)
└── UploadServerError (5xx, servidor fora, RLS bloqueou, duplicatas)
```

**Comportamento especial:**  
HTTP 409 (duplicado) é classificado como `UploadServerError` via `make_server_error("duplicate")`, mas em `upload_items_with_adapter` é tratado como operação bem-sucedida (arquivo já existe = não é falha).

---

## Mudanças Implementadas

### 1. Documentação do Contrato (`exceptions.py`)

**Arquivo:** `src/modules/uploads/exceptions.py`  
**Mudança:** Adicionado docstring no módulo documentando:
- Hierarquia de exceções
- Contrato Opção A (domain exceptions na API, raw em `__cause__`)
- Tratamento especial de HTTP 409

```python
"""
CONTRATO DE ERROS (Opção A - UP-01):
    A API de domínio (repository.py, upload_retry.py) expõe apenas exceções
    de domínio (UploadError e subclasses). Exceções brutas (RuntimeError,
    TypeError, etc.) são preservadas em __cause__ para debug/logging, mas
    não vazam diretamente para o chamador.

    Tratamento de HTTP 409 (duplicado): Classificado como UploadServerError
    via make_server_error("duplicate"), mas em upload_items_with_adapter
    é tratado como operação bem-sucedida (arquivo já existe = não é falha).
"""
```

### 2. Preservação de `__cause__` em `classify_upload_exception()`

**Arquivo:** `src/modules/uploads/upload_retry.py`  
**Problema:** Função criava novas exceções sem preservar a original em `__cause__`  
**Solução:** Adicionado `err.__cause__ = exc` para erros de cliente (4xx) e genéricos

**Antes:**
```python
is_client, code = _is_client_error(exc)
if is_client:
    return UploadError(
        f"Erro ao enviar arquivo (código {code}).",
        detail=f"HTTP {code}: {exc}",
    )

return UploadError(
    "Ocorreu um erro inesperado ao enviar o arquivo.",
    detail=str(exc),
)
```

**Depois:**
```python
is_client, code = _is_client_error(exc)
if is_client:
    err = UploadError(
        f"Erro ao enviar arquivo (código {code}).",
        detail=f"HTTP {code}: {exc}",
    )
    err.__cause__ = exc
    return err

err = UploadError(
    "Ocorreu um erro inesperado ao enviar o arquivo.",
    detail=str(exc),
)
err.__cause__ = exc
return err
```

### 3. Correção da Detecção de Duplicatas

**Arquivo:** `src/modules/uploads/repository.py`  
**Problema:** Código verificava palavra "duplicate" na mensagem amigável (`"Este arquivo já existe no servidor."`), que não contém essa palavra  
**Solução:** Verificar `detail` em vez de mensagem amigável

**Antes:**
```python
error_msg = str(classified_exc)
is_duplicate = "Duplicate" in error_msg or "duplicate" in error_msg.lower()
```

**Depois:**
```python
error_detail = getattr(classified_exc, "detail", "")
is_duplicate = "duplicate" in error_detail.lower()
```

### 4. Atualização dos Testes

**Arquivo:** `tests/unit/modules/uploads/test_uploads_repository.py`

#### Teste 1: `test_upload_adapter_exception_propagates`
**Mudança:** Verificar `UploadError` com `RuntimeError` em `__cause__`

```python
# Antes
assert isinstance(failures[0][1], RuntimeError)

# Depois
from src.modules.uploads.exceptions import UploadError
assert isinstance(failures[0][1], UploadError)
assert isinstance(failures[0][1].__cause__, RuntimeError)
```

#### Teste 2: `test_builder_without_kwargs_fails_with_kwargs_passed`
**Mudança:** Verificar `UploadError` com `TypeError` em `__cause__`

```python
# Antes
assert isinstance(failures[0][1], TypeError)

# Depois
from src.modules.uploads.exceptions import UploadError
assert isinstance(failures[0][1], UploadError)
assert isinstance(failures[0][1].__cause__, TypeError)
```

**Arquivo:** `tests/unit/modules/uploads/test_uploads_repository_fase13.py`

#### Teste 3: `test_upload_items_with_adapter_duplicate_error`
**Mudança:** Adicionar docstring explicando comportamento esperado (teste já estava correto, apenas melhorado)

```python
def test_upload_items_with_adapter_duplicate_error(monkeypatch):
    """Testa que erro 409 duplicate não aparece em failures (tratado como skip)."""
    # ... resto do teste
```

---

## Resultados

### Testes Executados
```bash
$ python -m pytest tests/unit/modules/uploads -q
........................................................................................................ [ 52%]
................................................................................................         [100%]
192 passed in 3.41s
```

### Validações
- ✅ Todos os 192 testes de uploads passando
- ✅ Contrato de erros documentado em docstring do módulo
- ✅ `classify_upload_exception()` preserva `__cause__` corretamente
- ✅ Detecção de duplicatas funcionando via `detail` em vez de mensagem
- ✅ Testes alinhados ao contrato Opção A

---

## Lições Aprendidas

1. **Documentação de contratos é essencial**: Sem documentação explícita do contrato de erros, testes e código de produção divergiam.

2. **`__cause__` vs `from exc`**:
   - `raise NewException(...) from original` → define `__cause__` automaticamente
   - Para exceções retornadas (não raised), é preciso definir manualmente: `err.__cause__ = original`

3. **Mensagens amigáveis vs detalhes técnicos**:
   - `message`: para usuário final ("Este arquivo já existe no servidor.")
   - `detail`: para logging e lógica interna ("duplicate | HTTP 409 | RuntimeError: 409 Conflict already exists")

4. **Verificação de erros especiais**: Ao verificar tipos de erro específicos (como duplicatas), usar `detail` em vez de `message` para lógica de decisão.

---

## Arquivos Modificados

1. `src/modules/uploads/exceptions.py` - Documentação do contrato
2. `src/modules/uploads/upload_retry.py` - Preservação de `__cause__` em `classify_upload_exception()`
3. `src/modules/uploads/repository.py` - Correção da detecção de duplicatas
4. `tests/unit/modules/uploads/test_uploads_repository.py` - Atualização de 2 testes
5. `tests/unit/modules/uploads/test_uploads_repository_fase13.py` - Melhoria de docstring

---

## Próximos Passos

- ✅ UP-01 concluído - todos os testes de uploads passando
- 🎯 Próximo milestone: aguardando instruções do usuário
