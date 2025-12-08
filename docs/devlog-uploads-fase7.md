# Devlog – FASE 7: Uploads & File Browser – UX de Erro, Robustez e Segurança

**Data:** 2025-01-XX  
**Branch:** qa/fixpack-04  
**Escopo:** Módulo de uploads – melhorar mensagens de erro, adicionar retry/backoff, validação OWASP

---

## Objetivo

Reforçar o módulo de uploads com:
1. **Mensagens claras de erro** – UX amigável para usuários
2. **Retry com backoff** – robustez contra falhas de rede temporárias
3. **Validação OWASP** – segurança antes do upload (whitelist extensões, limite de tamanho)
4. **Testes cobrindo erros** – cobertura completa de cenários de falha

**Regra:** Não alterar fluxo funcional básico.

---

## Arquivos Criados

### 1. `src/modules/uploads/exceptions.py`
Exceções tipadas para classificar erros de upload:

```python
class UploadError(Exception):
    """Base para erros de upload."""
    user_message: str  # Mensagem amigável para o usuário

class UploadValidationError(UploadError): ...  # Arquivo inválido
class UploadNetworkError(UploadError): ...     # Falha de conexão
class UploadServerError(UploadError): ...      # Erro no servidor
class UploadPermissionError(UploadError): ...  # Sem permissão
```

Funções factory para criar exceções com mensagens padronizadas:
- `make_validation_error(filename, reason)`
- `make_network_error(original_exc)`
- `make_server_error(status_code, detail)`
- `make_permission_error(bucket, path)`

### 2. `src/modules/uploads/file_validator.py`
Validação OWASP antes do upload:

```python
@dataclass
class FileValidationResult:
    valid: bool
    errors: list[str]
    user_message: str

def validate_upload_file(
    path: Path,
    allowed_extensions: frozenset[str] = DEFAULT_ALLOWED_EXTENSIONS,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
) -> FileValidationResult: ...
```

**Regras OWASP implementadas:**
- ✅ Whitelist de extensões (padrão: `.pdf`)
- ✅ Limite de tamanho (padrão: 50 MB)
- ✅ Verificação se arquivo existe e é legível
- ✅ Mensagens específicas para cada tipo de erro

### 3. `src/modules/uploads/upload_retry.py`
Retry com backoff exponencial:

```python
def upload_with_retry(
    adapter: SupabaseStorageAdapter,
    local_path: Path,
    remote_key: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> str | None: ...

def classify_upload_exception(exc: Exception) -> UploadError: ...
```

**Comportamento:**
- Erros de rede/servidor: retry com backoff exponencial
- Erros de validação/permissão: falha imediata (não faz sentido retry)
- Padrão: 3 tentativas, backoff 0.5s

---

## Arquivos Modificados

### 1. `src/modules/uploads/uploader_supabase.py`
- Importa novos módulos de exceções e validação
- `_show_upload_summary()` agora mostra mensagens específicas baseadas no tipo de exceção

### 2. `src/modules/uploads/__init__.py`
- Exporta todas as novas classes e funções

---

## Testes Criados

### Unitários (72 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `test_upload_exceptions_fase7.py` | 27 | Exceções, factory functions, herança |
| `test_file_validator_fase7.py` | 23 | Validação OWASP, edge cases |
| `test_upload_retry_fase7.py` | 22 | Retry, backoff, classificação |

### Integração (10 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `test_upload_flow_fase7.py` | 10 | Fluxo completo validação → retry → resultado |

**Total: 82 testes passando**

---

## QA Executado

```bash
# Ruff (lint) - passou
ruff check src/modules/uploads tests/unit/modules/uploads tests/integration/uploads
# All checks passed!

# Pyright (tipos) - passou
pyright src/modules/uploads
# 0 errors, 0 warnings

# Pytest - passou
python -m pytest tests/unit/modules/uploads/test_*_fase7.py tests/integration/uploads/ -v --no-cov
# 82 passed
```

---

## Decisões de Design

### 1. Exceções tipadas vs códigos de erro
**Escolha:** Exceções tipadas com `user_message`  
**Razão:** Permite tratamento específico (retry apenas para Network/Server) + mensagem amigável para UI

### 2. Whitelist de extensões (OWASP)
**Escolha:** Apenas `.pdf` por padrão  
**Razão:** Princípio do menor privilégio; pode ser expandido via parâmetro

### 3. Retry apenas para erros recuperáveis
**Escolha:** `UploadNetworkError` e `UploadServerError` fazem retry; outros falham imediato  
**Razão:** Não faz sentido retry para arquivo inválido ou sem permissão

### 4. Backoff exponencial
**Escolha:** `backoff_factor * (2 ** tentativa)`  
**Razão:** Reduz carga no servidor durante problemas; padrão bem estabelecido

---

## Notas Importantes

1. **Fluxo básico não alterado** – Apenas adicionadas camadas de validação e retry
2. **Compatibilidade** – Novos módulos são opcionais; código existente continua funcionando
3. **Segurança** – Validação OWASP protege contra upload de arquivos maliciosos
4. **UX** – Mensagens de erro agora são específicas e acionáveis

---

## Próximos Passos (sugestões)

- [ ] Integrar validação no `ExternalUploadService`
- [ ] Adicionar logging estruturado nos retries
- [ ] Considerar rate limiting para uploads em massa
- [ ] Expandir whitelist conforme necessidade do negócio

---

## Resumo

| Métrica | Valor |
|---------|-------|
| Arquivos criados | 3 (src) + 4 (tests) |
| Arquivos modificados | 2 |
| Testes adicionados | 82 |
| Erros ruff | 0 |
| Erros pyright | 0 |
| Quebras de fluxo | 0 |
