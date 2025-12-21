# TEST-009 — Network Utils

**Data**: 2025-12-20
**Fase**: 66 (v1.4.72)

## Alvo Selecionado

**Arquivo**: `src/utils/network.py`

Módulo de verificação de conectividade para modo cloud-only, sem GUI para testes unitários.

## Funções Mapeadas

### Funções Públicas

1. `check_internet_connectivity(timeout: float = 1.0) -> bool`
   - Verifica conectividade via socket e fallback HTTP
   - Respeita `RC_NO_NET_CHECK=1` para bypass
   - Retorna `True` se há internet, `False` caso contrário

2. `require_internet_or_alert() -> bool`
   - Verifica internet apenas em cloud-only mode (`RC_NO_LOCAL_FS=1`)
   - Mostra alerta GUI se sem internet (exceto se `RC_NO_GUI_ERRORS=1`)
   - Retorna `True` se internet disponível ou não requerida

### Funções Internas

3. `_socket_check(timeout: float) -> bool`
   - Tenta socket TCP para `8.8.8.8:53`
   - Trata `WinError 10013` (firewall/VPN)

4. `_http_check(timeout: float) -> bool`
   - Fallback HTTP via HEAD requests
   - URLs whitelist: Google, Cloudflare

## Dependências Identificadas

- `socket.create_connection` - teste de conectividade via TCP
- `urllib.request.urlopen` - fallback HTTP
- `tkinter.messagebox` - GUI alert (apenas em `require_internet_or_alert`)

## Estratégia de Teste

### A) check_internet_connectivity

**Cenários:**
- ✅ Sucesso via socket → `True`
- ✅ Falha socket + sucesso HTTP → `True`
- ✅ Falha ambos → `False`
- ✅ Bypass com `RC_NO_NET_CHECK=1` → `True`
- ✅ Timeout customizado

**Mocks:**
- `socket.create_connection` (sucesso/OSError/WinError 10013)
- `urllib.request.urlopen` (sucesso/URLError)

### B) require_internet_or_alert

**Cenários:**
- ✅ Modo não cloud-only → `True` (skip check)
- ✅ Cloud-only + internet → `True`
- ✅ Cloud-only + sem internet + GUI suppressed → `False`
- ✅ Cloud-only + sem internet + GUI (mock messagebox)

**Mocks:**
- `os.getenv` para flags (RC_NO_LOCAL_FS, RC_NO_GUI_ERRORS)
- `check_internet_connectivity` (True/False)
- `tkinter.messagebox.askokcancel` (user response)

### C) Funções Internas

**Cenários:**
- ✅ `_socket_check`: sucesso, OSError genérico, WinError 10013
- ✅ `_http_check`: sucesso primeira URL, sucesso segunda URL, todas falham

## Arquivo de Teste

`tests/unit/utils/test_network_fase66.py`

## Comando de Execução

```bash
pytest -q tests/unit/utils/test_network_fase66.py
```
