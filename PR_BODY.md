# fix(gui): corrige crashes de import CTK e instanciação ClientesV2Frame

## Descrição

Corrige dois crashes críticos que impediam o funcionamento da interface:

1. **NameError ao inicializar**: `ctk not defined` na definição da classe `App`
2. **TypeError ao abrir tela Clientes**: `ClientesV2Frame.__init__() missing 1 required positional argument: 'master'`

## Como reproduzir (antes da correção)

```bash
python .\main.py
# ❌ NameError: name 'ctk' is not defined. Did you mean: 'tk'?

# Ou após login, clicar no botão "Clientes":
# ❌ TypeError: ClientesV2Frame.__init__() missing 1 required positional argument: 'master'
```

## O que foi corrigido

### 📁 `src/modules/main_window/views/main_window.py`
- **Adicionado import**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
- **BaseApp segura**: `BaseApp = ctk.CTk if (HAS_CUSTOMTKINTER and ctk is not None) else tk.Tk`
- **Herança corrigida**: `class App(BaseApp)` em vez de conditional inline

### 📁 `src/modules/main_window/controllers/screen_registry.py`
- **Argumentos corretos**: `ClientesV2Frame(parent=...)` → `ClientesV2Frame(master=...)`
- **Consistência**: Alinha com padrão usado por todos os outros frames no projeto

## Risco

**🟢 Baixo risco**
- Correções pontuais e conservadoras
- Mantém compatibilidade total com fallback tk.Tk quando CustomTkinter indisponível
- Não altera funcionalidades existentes
- Segue padrão já estabelecido no projeto (HubFrame, PasswordsFrame, etc. usam `master`)

## Testes

**Gate local completo executado:**
```bash
✅ pre-commit run --all-files: PASSOU (20 hooks)
✅ python -X utf8 -m bandit -c .bandit -r src: PASSOU (0 issues, 62180 linhas)
✅ python -X utf8 -m pytest tests/modules/clientes_v2/ -v --tb=short --maxfail=1: PASSOU (113 testes em 35.93s)
✅ git status: clean
```

**Testes específicos validados:**
- `tests/modules/clientes_v2/test_shortcuts.py` - instanciação com argumentos posicionais
- `tests/modules/clientes_v2/test_smoke.py` - 7 testes de funcionalidade básica
- Todos os 113 testes do módulo clientes_v2 passando

## Rollback plan

**Se necessário, reverter com:**
```bash
git revert f428d5f --no-edit
git push origin main
```

**Ou reset para commit anterior:**
```bash
git reset --hard 4c2edc7
git push --force-with-lease origin refactor/estrutura-pdf-v1.5.35
```
