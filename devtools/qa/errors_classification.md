# CompatPack-17: Classificação dos 59 Erros Pyright

## **Grupo C – Crítico (NÃO tocar lógica, só ignore se necessário)** = 9 erros

Áreas de exclusão conforme prompt: `adapters/storage/**`, `infra/supabase/**`, `src/core/session/**`, `upload_service.py`

1. **adapters/storage/api.py:45** - reportReturnType (object → str)
   → Zona crítica: storage API

2. **adapters/storage/api.py:53** - reportReturnType (object → bool)
   → Zona crítica: storage API

3. **adapters/storage/api.py:57** - reportReturnType (object → Iterable)
   → Zona crítica: storage API

4. **adapters/storage/supabase_storage.py:81** - reportArgumentType (Unknown/dict → ReadableBuffer)
   → Zona crítica: Supabase storage

5. **adapters/storage/supabase_storage.py:83** - reportReturnType (Unknown/dict → str|bytes)
   → Zona crítica: Supabase storage

6. **infra/supabase/auth.py:152** (2x) - reportArgumentType (int|None → ConvertibleToInt)
   → Zona crítica: Supabase auth

7. **infra/supabase/db_manager.py:69** - reportGeneralTypeIssues (Invalid exception None)
   → Zona crítica: Supabase DB

8. **src/core/session/session.py:68** (2x) - reportArgumentType (Any|None → str for email/uid)
   → Zona crítica: session

9. **src/core/services/upload_service.py:126** - reportArgumentType (int → str|None)
   → Zona crítica: upload service

**Ação Grupo C:** Aplicar `# pyright: ignore[...]` específico em cada linha

---

## **Grupo B – Ignorar (chato/verboso/falso positivo)** = 33 erros

Casos onde o código funciona mas Pyright reclama por stubs/libs externas/detalhes verbosos

### B1. Stubs faltando `__getitem__`/`__setitem__` (20 erros)
- **src/modules/auditoria/view.py:668** - reportIndexIssue (Misc)
- **src/modules/clientes/storage_uploader.py:89** - reportIndexIssue (Combobox)
- **src/ui/files_browser.py** (17x): 357, 362, 364, 371, 373, 376, 409, 411, 447, 480, 515, 582, 597, 767, 819, 838, 868 - reportIndexIssue (Treeview)
- **src/ui/topbar.py:40** - reportIndexIssue (Button)

**Motivo:** Pyright não reconhece que tkinter widgets suportam subscript, mas funciona em runtime
**Ação:** `# pyright: ignore[reportIndexIssue]`

### B2. Biblioteca externa/PyMuPDF (2 erros)
- **src/utils/file_utils/bytes_utils.py:91** - reportArgumentType (Document não iterável)
- **src/utils/file_utils/path_utils.py:131** - reportGeneralTypeIssues ("Never" not iterable)

**Motivo:** Stub do PyMuPDF incompleto
**Ação:** `# pyright: ignore[reportArgumentType]` / `# pyright: ignore[reportGeneralTypeIssues]`

### B3. Assinatura de logging/getLogger (1 erro)
- **src/ui/hub/hub_screen.py:15** - reportAssignmentType (Logger parameter name mismatch)

**Motivo:** Falso positivo na declaração de tipo do logger
**Ação:** `# pyright: ignore[reportAssignmentType]`

### B4. Type checker verboso (4 erros simples de UI)
- **src/modules/notas/lixeira.py:98** - reportArgumentType (tuple[str,int,str] vs tuple[str,int] - font com 3 elementos)
- **src/ui/main_screen.py:443** - reportArgumentType (tuple[str,int,str] vs tuple[str,int] - font com 3 elementos)
- **src/ui/main_screen.py:1096** - reportAssignmentType (str vs tuple - annotation issue)
- **src/ui/menu_bar.py:15** - reportArgumentType (object vs Iterable)

**Motivo:** Stubs de tkinter não aceitam tuple[str,int,str] para font (aceita só 2 elementos)
**Ação:** `# pyright: ignore[reportArgumentType]` / `# pyright: ignore[reportAssignmentType]`

### B5. main_screen.py bbox (já tentamos corrigir no CP-16, ainda persiste)
- **src/ui/main_screen.py:333** (2x) - reportArgumentType (None → ConvertibleToInt)
- **src/ui/main_screen.py:338** (2x) - reportArgumentType (None → ConvertibleToInt)

**Motivo:** Já fizemos `bx = None` inicialização, mas Pyright ainda insiste que bx pode ser None no unpack
**Ação:** `# pyright: ignore[reportArgumentType]` nas linhas 333, 338

### B6. Classe base obscura
- **src/ui/main_screen.py:119** - reportGeneralTypeIssues (Argument to class must be base class)

**Motivo:** Falso positivo em declaração de classe
**Ação:** `# pyright: ignore[reportGeneralTypeIssues]`

### B7. HiDPI stub incompleto
- **src/utils/helpers/hidpi.py:56** - reportCallIssue (Expected 0 positional arguments)

**Motivo:** Biblioteca tkinter stub incompleto
**Ação:** `# pyright: ignore[reportCallIssue]`

---

## **Grupo A – Corrigir (seguro e simples)** = 17 erros

### A1. api_clients.py - Cliente constructor (1 erro FÁCIL)
- **src/core/api_clients.py:139** - reportCallIssue (Arguments missing)

**Ação:** Verificar chamada do construtor `Cliente()`, provavelmente faltando argumentos ou usando `**dict`

### A2. api_files/api_notes - positional argument (2 erros)
- **src/core/api_files.py:62** - reportCallIssue (Expected 1 positional)
- **src/core/api_notes.py:34** - reportCallIssue (Expected 1 positional)

**Ação:** Verificar chamadas, possivelmente faltando argumento posicional

### A3. api_notes - str vs Iterable[int] (1 erro)
- **src/core/api_notes.py:88** - reportArgumentType (str → Iterable[int])

**Ação:** Converter string pra lista: `[int(x)]` ou corrigir chamada

### A4. clientes_service - CurrentUser vs str (1 erro)
- **src/core/services/clientes_service.py:220** - reportArgumentType (CurrentUser|'' → str)

**Ação:** Guard pra converter CurrentUser pra str: `str(user) if not isinstance(user, str) else user`

### A5. repository.py - TypeIs obscuro (1 erro)
- **src/data/repository.py:32** - reportGeneralTypeIssues (Expected class but received TypeIs)

**Ação:** Revisar anotação de tipo, possivelmente corrigir type annotation

### A6. actions.py - parameter name mismatch (1 erro)
- **src/ui/hub/actions.py:64** - reportAssignmentType (Parameter "value" vs "s")

**Ação:** Renomear parâmetro `s` → `value` pra match com type annotation

### A7. actions.py - undefined variable (1 erro)
- **src/ui/hub/actions.py:275** - reportUndefinedVariable (_sanitize_key_component not defined)

**Ação:** Importar função ou renomear pra nome correto

### A8. colors.py - None guard (3 erros SIMPLES)
- **src/ui/hub/colors.py:57** - reportOperatorIssue (in operator com None)
- **src/ui/hub/colors.py:58** - reportOptionalSubscript (None subscript)
- **src/ui/hub/colors.py:77** - reportOptionalSubscript (None subscript)

**Ação:** Guard antes de usar: `if colors is not None and key in colors:`

### A9. hub_screen.py - Optional callback (1 erro)
- **src/ui/hub/hub_screen.py:191** - reportOptionalCall (None não é callable)

**Ação:** Guard: `if callback is not None: callback()`

### A10. hub_screen.py - Any|None → str (2 erros)
- **src/ui/hub/hub_screen.py:637** - reportArgumentType (Any|None → str ts_iso)
- **src/ui/hub/hub_screen.py:646** - reportArgumentType (Any|None → str created_at)

**Ação:** Guard: `if ts_iso is None: ts_iso = ""` ou early return

### A11. main_screen.py - redeclaration (1 erro)
- **src/ui/main_screen.py:221** - reportRedeclaration (_on_toggle obscured)

**Ação:** Renomear uma das funções `_on_toggle` (provavelmente tem duplicata)

---

## **Resumo da Classificação**

| Grupo | Qtde | Estratégia |
|-------|------|------------|
| **A** | 17   | Correções seguras (guards, renames, fix calls) |
| **B** | 33   | `# pyright: ignore[...]` (stubs/libs/verboso) |
| **C** | 9    | `# pyright: ignore[...]` (áreas críticas, zero lógica) |

**Total:** 59 erros

---

## **Ordem de Execução**

1. **Grupo A primeiro** (correções seguras)
2. **Grupo B depois** (ignores em código não-crítico)
3. **Grupo C por último** (ignores em áreas críticas)
4. **Verificar errorCount = 0** após cada grupo
