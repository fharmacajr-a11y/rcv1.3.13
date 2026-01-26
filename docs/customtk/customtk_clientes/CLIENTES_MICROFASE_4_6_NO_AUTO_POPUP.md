# CLIENTES_MICROFASE_4_6_NO_AUTO_POPUP.md

**Data**: 2025-01-13  
**Status**: ✅ Concluída  
**Objetivo**: Parar de abrir janela "Teste Visual - Theme Clientes" automaticamente durante discovery do pytest/VS Code.

---

## Problema

Durante a coleta automática de testes (pytest discovery e VS Code Test Explorer), scripts de teste visual estavam sendo importados e executavam código GUI diretamente no escopo do módulo, causando:

1. **Popups indesejados** de janelas Tkinter/CustomTkinter durante `python -m pytest --collect-only`
2. **Interrupção do workflow** ao salvar arquivos Python (auto-discovery do VS Code)
3. **Confusão** entre testes unitários automatizados e scripts de validação visual manual

### Scripts Problemáticos Identificados

- `test_apply_theme_fix.py` (raiz do projeto) — 124 linhas
- `tests/test_theme_visual.py` — 123 linhas
- `tests/test_toolbar_ctk_visual.py` — ~80 linhas
- `tests/test_toggle_fix.py` — ~100 linhas
- `tests/modules/clientes/test_clientes_toolbar_ctk_visual_polish_smoke.py` — 200 linhas (teste unitário válido, mantido)
- `tests/modules/clientes/test_clientes_visual_polish_surface.py` — 198 linhas (teste unitário válido, mantido)

**Problema técnico**: Executavam `root.mainloop()` diretamente no escopo do módulo, sem `if __name__ == "__main__"`.

---

## Solução Implementada

### A) Scripts Visuais Refatorados e Movidos

**Ações**:
1. Criada pasta `scripts/visual/`
2. Scripts movidos e renomeados (removido prefixo `test_`):
   - `test_apply_theme_fix.py` → [`scripts/visual/apply_theme_clientes.py`](../scripts/visual/apply_theme_clientes.py)
   - `tests/test_theme_visual.py` → [`scripts/visual/theme_clientes_visual.py`](../scripts/visual/theme_clientes_visual.py)
   - `tests/test_toolbar_ctk_visual.py` → [`scripts/visual/toolbar_ctk_clientes_visual.py`](../scripts/visual/toolbar_ctk_clientes_visual.py)
   - `tests/test_toggle_fix.py` → [`scripts/visual/toggle_theme_clientes.py`](../scripts/visual/toggle_theme_clientes.py)

3. **Refatoração aplicada** (padrão seguro):
   ```python
   def main():
       """Executa teste visual."""
       # Todo código GUI dentro da função
       root = tk.Tk()
       # ...
       root.mainloop()

   if __name__ == "__main__":
       main()
   ```

**Garantia**: `import <script>` agora não executa GUI, apenas quando rodado diretamente com `python scripts/visual/<script>.py`.

### B) Configuração do pytest.ini

**Alterações em** [`pytest.ini`](../pytest.ini):
```ini
addopts =
    -q
    --tb=short
    --import-mode=importlib
    --ignore=scripts/visual        # ← NOVO: ignora scripts visuais
    --ignore=test_apply_theme_fix.py  # ← NOVO: ignora arquivo antigo (caso exista)

testpaths = tests  # ← JÁ EXISTIA (coleta apenas de tests/)
```

**Efeito**: pytest ignora explicitamente pasta `scripts/visual/` e qualquer arquivo antigo que possa ter ficado na raiz.

### C) Configuração do VS Code

**Alterações em** [`.vscode/settings.json`](../.vscode/settings.json):
```jsonc
{
    // MICROFASE 4.6: Desabilitar auto-discovery de testes e popups
    "python.testing.autoTestDiscoverOnSaveEnabled": false,  // ← NOVO
    "testing.automaticallyOpenTestResults": "neverOpen"     // ← NOVO
}
```

**Efeitos**:
- Não roda discovery ao salvar arquivos Python
- Não abre painel de resultados de testes automaticamente
- Developer precisa executar discovery manualmente (Command Palette → "Test: Refresh Tests")

### D) Documentação Criada

1. **[`docs/VSCODE_TESTS_NO_AUTO_POPUP.md`](VSCODE_TESTS_NO_AUTO_POPUP.md)** — Documentação principal explicando:
   - Por que a janela abria sozinha
   - Como rodar scripts visuais manualmente agora
   - Settings do VS Code aplicadas
   - Testes de validação

2. **[`scripts/visual/README.md`](../scripts/visual/README.md)** — Guia rápido sobre scripts disponíveis e como executá-los.

---

## Testes de Validação

### ✅ Teste 1: Import seguro
```bash
python -c "import sys; sys.path.insert(0, 'scripts/visual'); import apply_theme_clientes; print('✓ Import não abriu GUI')"
```
**Resultado**: Nenhuma janela aberta ✅

### ✅ Teste 2: Coleta pytest sem popups
```bash
python -m pytest --collect-only -q
```
**Resultado**: Nenhuma janela aberta durante coleta ✅  
**Testes coletados**: ~500+ testes de `tests/` (scripts visuais ignorados) ✅

### ✅ Teste 3: Execução manual funciona
```bash
python scripts/visual/theme_clientes_visual.py
```
**Resultado**: Janela de teste visual abre normalmente ✅

### ✅ Teste 4: Auto-discovery desabilitado
**Ação**: Salvar arquivo Python qualquer em `tests/`  
**Resultado**: Nenhuma janela aberta, nenhum discovery automático ✅

---

## Como Rodar Scripts Visuais Agora

### Terminal (recomendado)
```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python scripts/visual/theme_clientes_visual.py
python scripts/visual/toolbar_ctk_clientes_visual.py
python scripts/visual/apply_theme_clientes.py
python scripts/visual/toggle_theme_clientes.py
```

### VS Code
1. Abra o script em `scripts/visual/`
2. Botão direito no editor → "Run Python File in Terminal"

---

## Scripts Visuais Disponíveis

| Script | Descrição | Uso Principal |
|--------|-----------|---------------|
| [`theme_clientes_visual.py`](../scripts/visual/theme_clientes_visual.py) | Testa alternância Light/Dark com preview de cores | Validar paleta de cores |
| [`toolbar_ctk_clientes_visual.py`](../scripts/visual/toolbar_ctk_clientes_visual.py) | Testa toolbar CustomTkinter isolada | Validar visual moderno (cantos arredondados) |
| [`apply_theme_clientes.py`](../scripts/visual/apply_theme_clientes.py) | Testa que `apply_theme()` não causa ValueError de 'bg' | Validar fix da Microfase 2.1 |
| [`toggle_theme_clientes.py`](../scripts/visual/toggle_theme_clientes.py) | Testa que toggle de tema aparece e funciona sem TclError | Validar integração do switch |

---

## Arquivos Alterados

### Criados
- ✅ `scripts/visual/apply_theme_clientes.py` (138 linhas)
- ✅ `scripts/visual/theme_clientes_visual.py` (137 linhas)
- ✅ `scripts/visual/toolbar_ctk_clientes_visual.py` (98 linhas)
- ✅ `scripts/visual/toggle_theme_clientes.py` (112 linhas)
- ✅ `scripts/visual/README.md` (documentação)
- ✅ `docs/VSCODE_TESTS_NO_AUTO_POPUP.md` (documentação principal)
- ✅ `docs/CLIENTES_MICROFASE_4_6_NO_AUTO_POPUP.md` (este arquivo)

### Modificados
- ✅ [`pytest.ini`](../pytest.ini) — Adicionado `--ignore=scripts/visual` e `--ignore=test_apply_theme_fix.py`
- ✅ [`.vscode/settings.json`](../.vscode/settings.json) — Adicionado `autoTestDiscoverOnSaveEnabled: false` e `automaticallyOpenTestResults: "neverOpen"`

### Removidos
- ✅ `test_apply_theme_fix.py` (raiz)
- ✅ `tests/test_theme_visual.py`
- ✅ `tests/test_toolbar_ctk_visual.py`
- ✅ `tests/test_toggle_fix.py`

---

## Observações Importantes

### Para Desenvolvedores

1. **Novos scripts visuais**: Sempre crie em `scripts/visual/` (não em `tests/`)
2. **Nomenclatura**: Evite prefixo `test_` em scripts manuais (pytest não deve coletá-los)
3. **Padrão obrigatório**: Use `if __name__ == "__main__":` para código GUI
4. **Import seguro**: Nunca execute GUI no escopo do módulo

### Recarregar VS Code

Se popups ainda ocorrerem após as mudanças:
1. `Ctrl+Shift+P` → "Developer: Reload Window"
2. Isso força VS Code a recarregar settings

### Testes Unitários vs. Scripts Visuais

| Aspecto | Teste Unitário | Script Visual |
|---------|----------------|---------------|
| **Localização** | `tests/` | `scripts/visual/` |
| **Nomenclatura** | `test_*.py` | Sem prefixo `test_` |
| **Execução** | Automática via pytest | Manual via `python` |
| **GUI** | ❌ Não pode abrir | ✅ Pode abrir janelas |
| **CI/CD** | ✅ Headless | ❌ Requer display |
| **Propósito** | Validação automática | Validação manual/demo |

---

## Microfases Relacionadas

- [CLIENTES_THEME_IMPLEMENTATION.md](CLIENTES_THEME_IMPLEMENTATION.md) — Implementação do sistema de temas
- [CLIENTES_MICROFASE_2_1_FIX_APPLY_THEME.md](CLIENTES_MICROFASE_2_1_FIX_APPLY_THEME.md) — Fix do ValueError de 'bg' em CustomTkinter
- [CLIENTES_MICROFASE_2_2_TOOLBAR_POLISH.md](CLIENTES_MICROFASE_2_2_TOOLBAR_POLISH.md) — Polimento visual da toolbar
- [VSCODE_TESTING_CONFIG.md](VSCODE_TESTING_CONFIG.md) — Configuração de testes no VS Code

---

## Resultado Final

✅ **Nenhum popup visual durante pytest discovery**  
✅ **Auto-discovery do VS Code desabilitado**  
✅ **Scripts visuais organizados em `scripts/visual/`**  
✅ **Documentação completa criada**  
✅ **Testes unitários continuam funcionando normalmente**

**Status**: Microfase concluída com sucesso! 🎉

---

**Autor**: GitHub Copilot  
**Projeto**: RCGestor v1.5.42  
**Microfase**: 4.6 — Parar de abrir "Teste Visual" automaticamente
