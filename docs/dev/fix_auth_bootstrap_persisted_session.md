# Fix de testes – auth_bootstrap persisted session

**Data:** 23 de novembro de 2025  
**Status:** ✅ Concluído

---

## Contexto

O teste `test_ensure_logged_with_persisted_session_initializes_org` em
`tests/test_auth_bootstrap_persisted_session.py` estava falhando com:

```
AttributeError: 'DummyApp' object has no attribute 'tk'
```

### Stack Trace

```
src/core/auth_bootstrap.ensure_logged
  -> _ensure_session
  -> LoginDialog(app)
  -> Tkinter/ttkbootstrap Toplevel
  -> BaseWidget._setup()
  -> self.tk = master.tk
  -> DummyApp não tem .tk
```

Isso acontecia porque `auth_bootstrap.ensure_logged()` chama internamente
`LoginDialog(app)`, que cria um `ttkbootstrap.Toplevel`/`tkinter.Toplevel`.
O Tkinter espera que o `master` tenha o atributo `.tk` (instância do interpreter Tcl/Tk),
mas o `DummyApp` usado no teste não expunha esse atributo.

---

## Solução

### 1. Reutilização do fixture `tk_root_session`

Reutilizado o fixture `tk_root_session` definido em `tests/conftest.py`, que
cria uma única instância global de `tk.Tk()` para a sessão de testes.

Este fixture já existia no projeto (criado em ciclos anteriores para testes de splash)
e foi projetado especificamente para evitar erros intermitentes do Tkinter ao
criar/destruir múltiplas instâncias de Tk.

### 2. Modificação do `DummyApp`

O `DummyApp` foi modificado para:

1. Receber `master` no construtor (`DummyApp(tk_root_session)`)
2. Expor `self.tk = master.tk` para compatibilidade com Toplevel
3. Manter os métodos esperados (`deiconify`, `_update_user_status`) e o `footer`

**Código anterior:**
```python
class DummyApp:
    def __init__(self):
        self._status_monitor = None
        self.footer = DummyFooter()

    def deiconify(self):
        self.deiconified = True

    def _update_user_status(self):
        self.status_updated = True
```

**Código atualizado:**
```python
class DummyApp:
    def __init__(self, master):
        # master é o tk_root_session (instância de tk.Tk())
        # Precisamos expor .tk para que LoginDialog / Toplevel funcionem.
        self._root = master
        self.tk = master.tk

        self._status_monitor = None
        self.footer = DummyFooter()

    def deiconify(self):
        self.deiconified = True

    def _update_user_status(self):
        self.status_updated = True
```

### 3. Assinatura do teste atualizada

```python
def test_ensure_logged_with_persisted_session_initializes_org(monkeypatch, tmp_path, tk_root_session):
    # ...
    app = DummyApp(tk_root_session)
    ok = auth_bootstrap.ensure_logged(app)
```

---

## Testes Executados

### Comando 1: Execução completa do arquivo de testes

```bash
python -m pytest tests/test_auth_bootstrap_persisted_session.py -v
```

**Resultado:**
```
platform win32 -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
collected 5 items

tests\test_auth_bootstrap_persisted_session.py .....                   [100%]

============================= 5 passed in 2.68s =============================
```

✅ **5/5 testes passaram**, sem erros de Tkinter.

### Comando 2: Cobertura do módulo auth_bootstrap

```bash
python -m pytest --cov=src.core.auth_bootstrap --cov-report=term-missing tests/test_auth_bootstrap_persisted_session.py -q
```

**Resultado:**
```
src\core\auth_bootstrap.py     153     59     36     14  59.3%
```

- **Cobertura:** 59.3% do módulo `auth_bootstrap`
- **Objetivo:** Validar que o teste exercita o código sem crash (meta de cobertura não aplicável nesta tarefa)

---

## Arquivos Modificados

### 1. `tests/test_auth_bootstrap_persisted_session.py`

**Mudanças:**
- Adicionado parâmetro `tk_root_session` na assinatura do teste
- `DummyApp.__init__` agora recebe `master` e expõe `self.tk = master.tk`
- Instanciação alterada de `app = DummyApp()` para `app = DummyApp(tk_root_session)`

### 2. `dev/fix_auth_bootstrap_persisted_session.md` (este arquivo)

Documentação da correção.

### 3. `docs/dev/checklist_tarefas_priorizadas.md`

Item `AUTH-BOOTSTRAP-TESTS-001` adicionado para registro histórico.

---

## Observações

### ✅ Código de produção preservado

Nenhuma alteração foi feita em:
- `src/core/auth_bootstrap.py`
- `src/ui/login_dialog.py`

O fix é **específico para o ambiente de testes** e aproveita a infraestrutura
de Tk global (`tk_root_session`) já existente no projeto.

### 📌 Fixture `tk_root_session` não modificado

O fixture em `tests/conftest.py` permaneceu inalterado conforme requisitado.
Apenas foi reutilizado no novo contexto.

### 🎯 Escopo da correção

Esta tarefa focou exclusivamente em:
1. Eliminar o crash `AttributeError: 'DummyApp' object has no attribute 'tk'`
2. Validar que todos os testes de `test_auth_bootstrap_persisted_session.py` passam
3. Não alterar lógica de produção

---

## Próximos Passos (Opcional)

Se necessário aumentar a cobertura de `auth_bootstrap.py`:
- Adicionar testes para fluxos de login falho
- Testar `_ensure_session` com diferentes estados de sessão persistida
- Cobrir branches de timeout e erros de rede

**Nota:** Este não era o objetivo da tarefa atual, que focou apenas na estabilização do teste existente.

---

**Autor:** GitHub Copilot  
**Tipo:** Fix de testes  
**Impacto:** Baixo (apenas testes)
