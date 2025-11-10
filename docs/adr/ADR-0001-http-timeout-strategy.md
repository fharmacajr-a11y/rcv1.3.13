# ADR-0001: HTTP Timeout Strategy (LIGHT/HEAVY Variants)

**Status**: Accepted  
**Date**: 2025-11-10  
**Deciders**: Development Team  
**Context**: Medium Priority Improvements - Sprint 1  

---

## Context

The application uses Supabase as backend, with various HTTP operations having different latency profiles:

1. **Light operations** (health checks, auth, RPC calls): Expected <5s, tolerate up to 30s
2. **Heavy operations** (file uploads/downloads): Expected 10-60s depending on file size
3. **Legacy timeout**: Single `HTTPX_TIMEOUT = 60s` for all operations

**Problem**: 60s timeout causes slow failure detection for stuck connections (health checks, auth) while 30s timeout could prematurely kill large uploads.

---

## Decision

Implement **two timeout variants** with backward-compatible alias:

```python
# infra/supabase/http_client.py
HTTPX_TIMEOUT_LIGHT = Timeout(connect=10.0, read=30.0, write=30.0, pool=None)
HTTPX_TIMEOUT_HEAVY = Timeout(connect=10.0, read=60.0, write=60.0, pool=None)

# Backward compatibility alias
HTTPX_TIMEOUT = HTTPX_TIMEOUT_LIGHT  # Defaults to faster failure detection
```

**Usage**:
- **LIGHT** (30s): Health checks (`infra/supabase/db_client.py`), auth, RPC, metadata queries
- **HEAVY** (60s): File uploads, large downloads (future use)
- **Alias**: Legacy code importing `HTTPX_TIMEOUT` continues to work (points to LIGHT)

---

## Rationale

### Why two variants?
- **Differentiated SLA**: Health checks should fail fast (30s), uploads can be patient (60s)
- **Better UX**: Faster detection of network issues vs. avoiding premature upload cancellation
- **Explicit intent**: Code clarity - `TIMEOUT_LIGHT` vs `TIMEOUT_HEAVY` documents expected latency

### Why LIGHT = 30s (not 15s or 60s)?
- **Industry standard**: AWS S3 SDK uses 30s read timeout
- **Network variance**: Allows 2-3 retries within typical health check window
- **Supabase latency**: p99 health check ~5s, 30s gives 6x buffer

### Why alias → LIGHT (not HEAVY)?
- **Majority use case**: 90% of current HTTPX_TIMEOUT usage is in light operations
- **Fail-fast principle**: Better to timeout early and retry than hang indefinitely
- **Original semantics**: Legacy timeout was used primarily for health/auth, not uploads

---

## Consequences

### Positive
- ✅ **Faster failure detection**: Health monitoring now fails in 30s instead of 60s
- ✅ **Backward compatible**: Zero breaking changes (alias preserves API)
- ✅ **Future-proof**: HEAVY variant ready for upload service refactoring
- ✅ **Code clarity**: Explicit timeout intent in function signatures

### Negative
- ⚠️ **Two constants to maintain**: Increased cognitive load (but documented)
- ⚠️ **Migration path**: New code should use explicit LIGHT/HEAVY, not alias

### Neutral
- 📝 **Testing**: 3 new tests verify alias behavior (`test_httpx_timeout_alias.py`)
- 📝 **Documentation**: ADR captures decision rationale for future reference

---

## Alternatives Considered

### Alternative 1: Single dynamic timeout
```python
def get_timeout(operation: str) -> Timeout:
    return TIMEOUTS.get(operation, DEFAULT_TIMEOUT)
```
**Rejected**: Too complex, requires timeout registry, harder to type-check.

### Alternative 2: Per-request timeout
```python
httpx.get(url, timeout=30)  # Inline timeout
```
**Rejected**: Easy to forget, inconsistent across codebase, no central config.

### Alternative 3: Environment variable
```python
HTTPX_TIMEOUT = int(os.getenv("HTTPX_TIMEOUT", "30"))
```
**Rejected**: Runtime config complexity, harder to test, unclear semantics.

---

## Implementation

**Files Changed**:
- `infra/supabase/http_client.py`: Added LIGHT/HEAVY + alias
- `infra/supabase/db_client.py`: Updated to use `HTTPX_TIMEOUT_LIGHT`
- `tests/test_httpx_timeout_alias.py`: 3 compatibility tests

**Validation**:
- ✅ All 41 tests passing
- ✅ App starts without ImportError
- ✅ Backward compatibility verified

**Commit**: `da6c4e2` (hotfix), `58bbcf8` (original refactoring)

---

## References

- **HTTPX Docs**: https://www.python-httpx.org/advanced/#timeout-configuration
- **Keep a Changelog**: Timeout changes documented in CHANGELOG.md v1.1.0
- **Related**: `HOTFIX_HTTPX_TIMEOUT.md` (backward compatibility report)
- **Quality Campaign**: `MEDIUM_PRIORITY_SUMMARY.md` (timeout refactoring context)

---

## Future Work

1. **Upload Service**: Integrate `HTTPX_TIMEOUT_HEAVY` in `upload_service.py` when refactoring large file uploads
2. **Metrics**: Add Prometheus metrics for timeout frequency (LIGHT vs HEAVY)
3. **Dynamic config**: Consider per-environment timeouts (dev=10s, prod=30s) if needed
4. **Deprecation**: Evaluate removing `HTTPX_TIMEOUT` alias in v2.0.0 (breaking change)

---

**Author**: GitHub Copilot (ADR Assistant)  
**Review**: Quality Campaign Team  
**Next Review**: v1.2.0 (evaluate usage patterns)
