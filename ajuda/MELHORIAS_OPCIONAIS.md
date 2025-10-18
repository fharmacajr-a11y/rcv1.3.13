# Melhorias Opcionais - Limpeza de Código

Este documento lista pequenas melhorias opcionais identificadas durante a análise.
**Nenhuma é crítica** - são apenas refinamentos de código.

---

## 1. Variáveis Não Usadas (Vulture)

### Issue 1: `application\keybindings.py:7`
**Problema:** Variável `ev` não está sendo usada

**Código atual:**
```python
def _toggle_fullscreen(ev):  # linha 7
    # código que não usa 'ev'
```

**Solução sugerida:**
```python
def _toggle_fullscreen(_):
    # código que não usa o parâmetro
```

ou

```python
def _toggle_fullscreen(ev):  # noqa: unused argument
    # código que não usa 'ev'
```

---

### Issue 2 e 3: `shared\logging\audit.py:24-25`
**Problema:** Variáveis `action` e `details` definidas mas não usadas na função `log_client_action`

**Código atual:**
```python
def log_client_action(
    user: str,
    client_id: int,
    action: str,
    details: Optional[str] = None,
) -> None:
    """Records a client action. Currently a no-op kept for future expansion."""
    return None
```

**Observação:** Esta é uma função placeholder para futura implementação. As variáveis são necessárias para manter a assinatura da API.

**Opções:**
1. **Manter como está** (recomendado) - É uma API placeholder
2. **Adicionar _ prefix** aos parâmetros não usados:
   ```python
   def log_client_action(
       user: str,
       client_id: int,
       _action: str,  # placeholder
       _details: Optional[str] = None,  # placeholder
   ) -> None:
   ```
3. **Adicionar docstring clara** indicando que é placeholder:
   ```python
   def log_client_action(
       user: str,
       client_id: int,
       action: str,  # Reserved for future use
       details: Optional[str] = None,  # Reserved for future use
   ) -> None:
       """
       Records a client action.

       Note: Currently a no-op placeholder for future audit logging.
       Parameters are reserved for the future implementation.
       """
       pass
   ```

---

## 2. Dependências (Deptry)

### Issue 1: urllib3 (DEP003)
**Problema:** `urllib3` é importado diretamente mas é uma dependência transitiva

**Arquivo:** `infra\net_session.py:14`

**Código atual:**
```python
import urllib3
```

**Opção 1 - Adicionar ao requirements.in** (recomendado):
```
# requirements.in
urllib3>=2.0.0
```

**Opção 2 - Usar via requests**:
Se `urllib3` for usado apenas para retry, considere usar `requests` com retry adapter:
```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
```

---

### Issue 2: PyPDF2 (DEP002)
**Problema:** `PyPDF2` está em `requirements.in` mas não é usado no codebase

**Verificação necessária:**
```powershell
# Buscar por importações de PyPDF2
grep -r "import PyPDF2" .
grep -r "from PyPDF2" .
```

**Se não for usado:**
```diff
# requirements.in
- PyPDF2
```

**Se for usado:** Verificar se foi substituído por `pypdf` (que está instalado):
```python
# Talvez o código use 'pypdf' agora ao invés de 'PyPDF2'
import pypdf  # novo pacote
```

---

### Issue 3: tzdata (DEP002)
**Problema:** `tzdata` está em `requirements.in` mas não é usado diretamente

**Observação:** `tzdata` é frequentemente uma dependência transitiva de outras bibliotecas de timezone/datetime.

**Verificação:**
```powershell
# Ver quais pacotes dependem de tzdata
pip show tzdata
```

**Ação:**
- Se for dependência transitiva: remover de `requirements.in`
- Se for necessário em Windows para timezone: manter

---

## 3. Documentação dos Novos __init__.py

Os seguintes arquivos foram criados e podem receber documentação adicional:

### `infra/__init__.py`
```python
# -*- coding: utf-8 -*-
"""
Infrastructure Layer
====================

Handles external systems integration:
- Supabase authentication (supabase_auth.py)
- Supabase client (supabase_client.py)
- Network session management (net_session.py)
- Network status monitoring (net_status.py)
- Health checks (healthcheck.py)

This layer provides low-level infrastructure services used by adapters and core.
"""
```

### `config/__init__.py`
```python
# -*- coding: utf-8 -*-
"""
Configuration Management
========================

Application configuration and constants:
- constants.py: Application-wide constants
- paths.py: Path resolution and management
- runtime_manifest.yaml: Runtime configuration

This layer provides configuration data used throughout the application.
"""
```

### `detectors/__init__.py`
```python
# -*- coding: utf-8 -*-
"""
Detectors and Parsers
=====================

Document detection and parsing utilities:
- cnpj_card.py: CNPJ detection in documents

This layer provides specialized detection and parsing functionality.
"""
```

---

## Script de Aplicação Automática

Para aplicar as melhorias automaticamente, você pode usar este script:

```python
# scripts/apply_cleanups.py
"""Aplica melhorias opcionais de limpeza identificadas."""

from pathlib import Path

ROOT = Path(__file__).parent.parent

# 1. Fix keybindings.py
keybindings = ROOT / "application" / "keybindings.py"
content = keybindings.read_text(encoding="utf-8")
content = content.replace("def _toggle_fullscreen(ev):", "def _toggle_fullscreen(_):")
keybindings.write_text(content, encoding="utf-8")
print("✓ Fixed application/keybindings.py")

# 2. Add urllib3 to requirements.in
req_in = ROOT / "requirements.in"
lines = req_in.read_text(encoding="utf-8").splitlines()
if "urllib3" not in "".join(lines):
    lines.append("urllib3>=2.0.0  # Direct dependency (used in infra/net_session.py)")
    req_in.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("✓ Added urllib3 to requirements.in")

print("\n✅ Melhorias aplicadas!")
print("Execute: pip-compile requirements.in")
```

---

## Priorização

### Alta Prioridade
- 🟡 **urllib3** - Adicionar ao requirements.in (evita problemas futuros)

### Média Prioridade
- 🟢 **PyPDF2/tzdata** - Verificar e limpar dependências não usadas
- 🟢 **Documentação** - Adicionar docstrings aos __init__.py

### Baixa Prioridade
- 🔵 **Variáveis não usadas** - Limpeza cosmética, não afeta funcionalidade

---

**Observação Final:** Todas essas melhorias são **opcionais**. O código está funcional e bem estruturado como está.
