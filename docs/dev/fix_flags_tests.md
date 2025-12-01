# Fix de testes – flags / src.cli

**Data:** 23 de novembro de 2025  
**Status:** ✅ Concluído (já estava estável)

---

## Contexto

Os testes em `tests/test_flags.py` foram criados para validar o parsing de flags CLI
do módulo `src.cli` (`--no-splash`, `--safe-mode`, `--debug`). Em iterações anteriores,
havia risco de:

* `ModuleNotFoundError: No module named 'src.cli'` (import incorreto)
* `SystemExit(2)` de `argparse` ao encontrar argumentos desconhecidos vindos do pytest
  (ex.: `--cov=...`, `-q`, etc.)

Após análise, constatou-se que o arquivo de testes **já estava corretamente implementado**
e todos os testes estão passando sem erros.

---

## Implementação Atual (Correta)

### 1. Estrutura do `src/cli.py`

O módulo fornece:

```python
class AppArgs(NamedTuple):
    """Parsed application arguments."""
    no_splash: bool = False
    safe_mode: bool = False
    debug: bool = False

def parse_args(argv: list[str] | None = None) -> AppArgs:
    """Parse command-line arguments.

    Args:
        argv: Arguments to parse (defaults to sys.argv[1:])
    """
    parser = argparse.ArgumentParser(...)
    # ... adiciona argumentos --no-splash, --safe-mode, --debug
    args = parser.parse_args(argv)
    return AppArgs(...)

def get_args() -> AppArgs:
    """Get parsed command-line arguments (singleton)."""
    global _parsed_args
    if _parsed_args is None:
        _parsed_args = parse_args()
    return _parsed_args
```

**Nota importante:** `parse_args` aceita `argv` opcional, permitindo testes isolados.

### 2. Estrutura do `tests/test_flags.py`

Os testes foram implementados corretamente seguindo as melhores práticas:

#### ✅ Import correto
```python
from src.cli import parse_args
```

#### ✅ Uso de argv explícito (evita conflito com pytest)
```python
def test_parse_args_defaults():
    """Test default argument values."""
    from src.cli import parse_args

    args = parse_args([])  # ← Lista explícita, não usa sys.argv
    assert args.no_splash is False
    assert args.safe_mode is False
    assert args.debug is False

def test_parse_args_no_splash():
    """Test --no-splash flag."""
    from src.cli import parse_args

    args = parse_args(["--no-splash"])  # ← Argumentos controlados
    assert args.no_splash is True
    assert args.safe_mode is False

def test_parse_args_combined():
    """Test multiple flags together."""
    from src.cli import parse_args

    args = parse_args(["--no-splash", "--safe-mode", "--debug"])
    assert args.no_splash is True
    assert args.safe_mode is True
    assert args.debug is True
```

#### ✅ Teste de importação
```python
def test_cli_module_imports_without_error():
    """Test that CLI module can be imported without breaking."""
    try:
        import src.cli

        assert hasattr(src.cli, "parse_args")
        assert hasattr(src.cli, "get_args")
        assert hasattr(src.cli, "AppArgs")
    except Exception as e:
        pytest.fail(f"Failed to import src.cli: {e}")
```

---

## Testes Executados

### Comando 1: Testes isolados de flags

```bash
python -m pytest tests/test_flags.py -v
```

**Resultado:**
```
platform win32 -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
collected 6 items

tests\test_flags.py ......                                             [100%]

============================= 6 passed in 2.60s =============================
```

✅ **6/6 testes passaram**

### Comando 2: Testes com cobertura

```bash
python -m pytest tests/test_flags.py --cov=src.cli --cov-report=term-missing -v
```

**Resultado:**
```
collected 6 items

tests\test_flags.py ......                                             [100%]

============================== tests coverage ===============================
Name         Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------
src\cli.py      20      3      2      0  77.3%   73-75
--------------------------------------------------------
TOTAL           20      3      2      0  77.3%

============================= 6 passed in 2.46s =============================
```

✅ **Cobertura:** 77.3% do módulo `cli.py`  
✅ **Linhas não cobertas:** 73-75 (apenas o `get_args()` singleton, não crítico para estes testes)

### Comando 3: Validação com outros testes que estavam falhando

```bash
python -m pytest tests/test_flags.py tests/test_auth_validation.py tests/test_menu_logout.py tests/test_modules_aliases.py tests/test_prefs.py tests/test_clientes_integration.py -v
```

**Resultado:**
```
collected 71 items

tests\test_flags.py ......                                               [  8%]
tests\test_auth_validation.py .........................................  [ 67%]
tests\test_menu_logout.py .                                              [ 80%]
tests\test_modules_aliases.py .......                                    [ 90%]
tests\test_prefs.py .....                                                [ 97%]
tests\test_clientes_integration.py ..                                    [100%]

============================= 71 passed in 14.73s =============================
```

✅ **71/71 testes passaram** (incluindo os que estavam falhando anteriormente)

---

## Boas Práticas Implementadas

### 1. ✅ Import direto e explícito
```python
from src.cli import parse_args
```
Evita ambiguidades e funciona corretamente com `pytest.ini` configurado.

### 2. ✅ Uso de argv explícito
```python
args = parse_args([])              # Default
args = parse_args(["--no-splash"]) # Flag específica
```
**Benefício:** Evita que argumentos do pytest (`--cov`, `-q`, etc.) sejam interpretados
pelo `argparse` da aplicação.

### 3. ✅ Não usa `get_args()` sem controle
Os testes focam em `parse_args(argv)` com argumentos controlados, evitando
dependência de `sys.argv` global (que seria poluído pelo pytest).

### 4. ✅ Teste de importação defensivo
```python
try:
    import src.cli
    assert hasattr(src.cli, "parse_args")
except Exception as e:
    pytest.fail(f"Failed to import src.cli: {e}")
```
Garante que o módulo está acessível e bem estruturado.

---

## Observações

### ✅ Nenhuma modificação necessária

O arquivo `tests/test_flags.py` **já estava implementado corretamente** desde sua criação.
Os potenciais problemas mencionados (ModuleNotFoundError, conflitos com argparse) foram
prevenidos pela implementação correta desde o início:

1. Import correto de `src.cli`
2. Uso de `parse_args(argv)` com listas explícitas
3. Nenhuma chamada desprotegida a `get_args()`

### 📌 Diferença de outros testes corrigidos

- **test_auth_bootstrap_persisted_session.py**: Precisou de `tk_root_session` para Tkinter
- **test_menu_logout.py**: Precisou de monkeypatch em `themes.get_args`
- **test_flags.py**: **Já estava correto**, não precisou de ajustes

### 🎯 Cobertura

A cobertura de 77.3% é adequada para os cenários de teste:
- ✅ Todos os argumentos (`--no-splash`, `--safe-mode`, `--debug`)
- ✅ Valores default
- ✅ Combinações de flags
- ❌ Não testa `get_args()` (singleton), mas não é necessário para validar parsing

---

## Conclusão

O módulo `src.cli` e seus testes em `tests/test_flags.py` estão **estáveis e funcionais**.
Não foram necessárias correções, apenas validação e documentação do estado atual.

**Próximos passos sugeridos (opcional):**
- Adicionar teste para `get_args()` usando `monkeypatch.setattr(sys, "argv", [...])`
- Aumentar cobertura para 100% se desejado

---

**Autor:** GitHub Copilot  
**Tipo:** Validação e documentação  
**Impacto:** Nenhum (testes já estavam corretos)
