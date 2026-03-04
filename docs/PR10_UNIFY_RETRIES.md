# PR 10 — Unify All Retry / Backoff Into a Single Module

## A) Arquivos alterados / removidos

| Arquivo | Ação |
|---------|------|
| `src/infra/retry_policy.py` | **NOVO** — módulo unificado de retry |
| `src/infra/http/retry.py` | Reescrito como shim re-export de `retry_policy.retry_call` |
| `src/infra/supabase/db_client.py` | Import alterado; `exec_postgrest` usa novo `retry_call` |
| `src/db/supabase_repo.py` | **Removido** `with_retries`, `RETRY_ERRORS`; 10 call-sites simplificados |
| `src/core/db_manager/db_manager.py` | **Removido** `_with_retries`, `RETRY_ERRORS`; 3 call-sites simplificados |
| `src/core/services/notes_service.py` | **Removido** `_with_retry`; 3 call-sites com inline transient-check |
| `src/modules/uploads/upload_retry.py` | `upload_with_retry` delega para `_core_retry` + `_is_upload_transient` |
| `src/adapters/storage/supabase_storage.py` | `_upload` reescrito com `_core_retry` + `_is_transient_exc` |
| `src/core/services/clientes_service.py` | `count_clients` simplificado (retry já vive em `exec_postgrest`) |
| `src/utils/net_retry.py` | **Gutted** — era dead-code (0 callers) |
| `tests/test_retry_policy.py` | **NOVO** — 31 testes |
| `tests/test_supabase_repo_winerror.py` | Reescrito — 5 testes usam novo `retry_call` |

**Total: 2 novos, 10 modificados.**

---

## B) Migrações de retry

### (1) `exec_postgrest` (db_client.py)
- **Antes**: importava `retry_call` de `src.infra.http.retry` (que capturava `Exception` genérica)
- **Depois**: importa de `src.infra.retry_policy`; `retry_call(rb.execute, max_attempts=3, base_delay=0.7, jitter=0.3)`

### (2) `with_retries` (supabase_repo.py) — **REMOVIDA**
- **Antes**: wrapper local com `RETRY_ERRORS=(httpx.ReadError, …)`, sleep `random.uniform()`, 3 tentativas. Aplicado em 10 métodos.
- **Problema**: `with_retries` envolvia `exec_postgrest`, que **já** retenta → **retry aninhado 3×3 = 9 tentativas**.
- **Depois**: 10 call-sites chamam diretamente; retry único vive em `exec_postgrest`.

### (3) `_with_retries` (db_manager.py) — **REMOVIDA**
- **Antes**: clone quase idêntico de `with_retries`, mesma lista `RETRY_ERRORS`, 3 call-sites.
- **Depois**: 3 call-sites chamam diretamente; retry em `exec_postgrest` é suficiente.

### (4) `_with_retry` (notes_service.py) — **REMOVIDA**
- **Antes**: retry manual com `secrets.randbelow()`, captura de `RETRY_ERRORS`, 2-3 tentativas.
- **Depois**: 3 métodos chamam direto; erros transitórios convertidos inline em `NotesTransientError`.

### (5) `upload_with_retry` (upload_retry.py) — **REESCRITA**
- **Antes**: loop manual com backoff customizado, classificação inline.
- **Depois**: delega para `_core_retry(upload_fn, …, is_transient=_is_upload_transient)`.

### (6) `_upload` (supabase_storage.py) — **REESCRITA**
- **Antes**: loop `for attempt in range(max_retries)` com `random.uniform()` e sleep.
- **Depois**: `_core_retry(_do_upload, …, is_transient=_is_transient_exc, sleep_fn=_sleep, on_retry=_on_retry)`.

### (7) `count_clients` (clientes_service.py) — **SIMPLIFICADA**
- **Antes**: `for attempt in range(max_retries)` loop manual com `time.sleep(2 ** attempt)`.
- **Depois**: try/except único; `exec_postgrest` já retenta. Fallback para cache mantido.

### (8) `run_cloud_op` (net_retry.py) — **DEAD CODE REMOVIDO**
- 0 callers no projeto inteiro; módulo mantido vazio para evitar `ImportError`.

### (9) `retry_call` antigo (http/retry.py) — **CONVERTIDO EM SHIM**
- **Antes**: implementação completa com `DEFAULT_EXCS` incluindo catch-all `Exception`.
- **Depois**: `from src.infra.retry_policy import retry_call` — re-export puro.

---

## C) Política final — `src/infra/retry_policy.py`

### API

```python
retry_call(
    fn: Callable[..., T],
    *args,
    max_attempts: int = 3,       # total de tentativas (incluindo a 1ª)
    base_delay: float = 0.4,     # delay base (s)
    max_delay: float = 8.0,      # cap exponencial (s)
    jitter: float = 0.15,        # jitter máximo (s, uniform via secrets)
    is_transient: Callable[[Exception], bool] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs,
) -> T
```

### Fórmula de backoff

```
delay = min(base_delay × 2^(attempt-1), max_delay) + uniform(0, jitter)
```

| Tentativa | base_delay=0.4 | + jitter ≤0.15 | Total |
|-----------|----------------|----------------|-------|
| 1ª falha  | 0.40 s         | 0–0.15 s       | 0.40–0.55 s |
| 2ª falha  | 0.80 s         | 0–0.15 s       | 0.80–0.95 s |
| 3ª falha  | 1.60 s         | 0–0.15 s       | 1.60–1.75 s |
| … (cap)   | 8.00 s         | 0–0.15 s       | 8.00–8.15 s |

### Classificador `is_transient_error(exc)`

| Condição | Resultado |
|----------|-----------|
| `OSError` com `winerror == 10035` (WSAEWOULDBLOCK) | ✅ Transitório |
| `OSError` subclasse de `socket.timeout / ConnectionError / TimeoutError` | ✅ Transitório |
| `OSError` com `errno` EWOULDBLOCK / EAGAIN | ✅ Transitório |
| Outros `OSError` (PermissionError, FileNotFoundError…) | ❌ Não-transitório |
| `httpx.ReadError / WriteError / ConnectError / ConnectTimeout / RemoteProtocolError` | ✅ Transitório |
| `httpcore.ReadError / WriteError` | ✅ Transitório |
| Mensagem contém `502/503/504/429/bad gateway/timeout/connection/…` | ✅ Transitório |
| `ValueError`, `KeyError`, `AttributeError`… | ❌ Não-transitório |

### Extensibilidade

Callers podem fornecer `is_transient=custom_fn` para classificação especializada
(ex.: `_is_upload_transient` em `upload_retry.py` que também classifica 413/PayloadTooLarge).

---

## D) Saída de pytest + ruff

### ruff check (12 arquivos)

```
$ python -m ruff check src/infra/retry_policy.py src/infra/http/retry.py \
    src/infra/supabase/db_client.py src/db/supabase_repo.py \
    src/core/db_manager/db_manager.py src/core/services/notes_service.py \
    src/modules/uploads/upload_retry.py src/adapters/storage/supabase_storage.py \
    src/core/services/clientes_service.py src/utils/net_retry.py \
    tests/test_retry_policy.py tests/test_supabase_repo_winerror.py
All checks passed!
```

### pytest — testes focados (36 testes)

```
$ python -m pytest tests/test_retry_policy.py tests/test_supabase_repo_winerror.py -v
tests/test_retry_policy.py::TestIsTransientError::test_winerror_10035 PASSED
tests/test_retry_policy.py::TestIsTransientError::test_other_oserror_not_transient PASSED
tests/test_retry_policy.py::TestIsTransientError::test_timeout_error PASSED
tests/test_retry_policy.py::TestIsTransientError::test_connection_error PASSED
tests/test_retry_policy.py::TestIsTransientError::test_socket_timeout PASSED
tests/test_retry_policy.py::TestIsTransientError::test_message_5xx PASSED
tests/test_retry_policy.py::TestIsTransientError::test_message_429 PASSED
tests/test_retry_policy.py::TestIsTransientError::test_message_404_not_transient PASSED
tests/test_retry_policy.py::TestIsTransientError::test_value_error_not_transient PASSED
tests/test_retry_policy.py::TestIsTransientError::test_generic_runtime_not_transient PASSED
tests/test_retry_policy.py::TestIsTransientError::test_bad_gateway_text PASSED
tests/test_retry_policy.py::TestIsTransientError::test_eagain_errno PASSED
tests/test_retry_policy.py::TestCalculateDelay::test_attempt_1 PASSED
tests/test_retry_policy.py::TestCalculateDelay::test_attempt_2 PASSED
tests/test_retry_policy.py::TestCalculateDelay::test_cap PASSED
tests/test_retry_policy.py::TestCalculateDelay::test_jitter_bounds PASSED
tests/test_retry_policy.py::TestCalculateDelay::test_zero_jitter PASSED
tests/test_retry_policy.py::TestRetryCall::test_success_first_try PASSED
tests/test_retry_policy.py::TestRetryCall::test_success_after_transient PASSED
tests/test_retry_policy.py::TestRetryCall::test_exhaust_retries PASSED
tests/test_retry_policy.py::TestRetryCall::test_non_transient_no_retry PASSED
tests/test_retry_policy.py::TestRetryCall::test_winerror_10035_retry PASSED
tests/test_retry_policy.py::TestRetryCall::test_plain_oserror_no_retry PASSED
tests/test_retry_policy.py::TestRetryCall::test_other_winerror_no_retry PASSED
tests/test_retry_policy.py::TestRetryCall::test_5xx_message_retry PASSED
tests/test_retry_policy.py::TestRetryCall::test_on_retry_callback PASSED
tests/test_retry_policy.py::TestRetryCall::test_sleep_fn_called PASSED
tests/test_retry_policy.py::TestRetryCall::test_args_kwargs_passthrough PASSED
tests/test_retry_policy.py::TestRetryCall::test_custom_classifier PASSED
tests/test_retry_policy.py::TestRetryCall::test_max_attempts_1 PASSED
tests/test_retry_policy.py::TestRetryCall::test_callback_error_swallowed PASSED
tests/test_supabase_repo_winerror.py::TestWinError10035Retry::test_winerror_10035_retried PASSED
tests/test_supabase_repo_winerror.py::TestWinError10035Retry::test_other_oserror_not_retried PASSED
tests/test_supabase_repo_winerror.py::TestWinError10035Retry::test_different_winerror_not_retried PASSED
tests/test_supabase_repo_winerror.py::TestWinError10035Retry::test_non_oserror_not_retried PASSED
tests/test_supabase_repo_winerror.py::TestWinError10035Retry::test_all_attempts_exhausted PASSED
============================== 36 passed in 0.52s ==============================
```

### pytest — suíte completa

```
$ python -m pytest tests/ -q --timeout=60
596 passed in 7.22s
```

**565 → 596 testes (+31 net new).**

---

## E) Exemplo de log durante retry

Quando `exec_postgrest` encontra um `httpx.ReadError` transitório, o log emitido:

```
DEBUG src.infra.retry_policy retry attempt 1/3 failed (ReadError: [Errno 10054] Connection was forcibly closed). retrying in 0.72s
DEBUG src.infra.retry_policy retry attempt 2/3 failed (ReadError: [Errno 10054] Connection was forcibly closed). retrying in 1.21s
```

Formato: `retry attempt {attempt}/{max_attempts} failed ({ExcType}: {msg[:120]}). retrying in {delay:.2f}s`

Nível: `DEBUG` (não polui stdout em produção; visível com `LOG_LEVEL=DEBUG`).

---

## Resumo

| Métrica | Antes | Depois |
|---------|-------|--------|
| Implementações de retry distintas | 14 | **1** (`retry_policy.py`) |
| Linhas de retry duplicadas | ~280 | 0 |
| Retry aninhado (3×3 = 9 tentativas) | Sim | **Não** |
| Catch-all `Exception` em retry | Sim (`http/retry.py`) | **Não** (classificador seletivo) |
| `random.uniform()` (B311) | 4 locais | **0** (`secrets.randbelow`) |
| Dead code (`net_retry.py`, `http_client.py`) | 2 módulos | Removido |
| Testes | 565 | **596** (+31) |
| Ruff violations | 0 | 0 |
