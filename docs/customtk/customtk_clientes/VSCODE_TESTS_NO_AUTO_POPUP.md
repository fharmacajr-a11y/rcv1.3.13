# VSCODE_TESTS_NO_AUTO_POPUP.md

**Microfase 4.6** — Documentação sobre configuração de testes no VS Code para evitar popups automáticos de scripts visuais.

---

## Problema Original

Durante a coleta/discovery automática de testes pelo pytest e VS Code, scripts de teste visual (aqueles que criam janelas Tkinter/CustomTkinter) estavam sendo importados e executavam código GUI **no momento do import**, causando:

1. **Popups indesejados** de janelas de teste durante a descoberta de testes
2. **Interrupção do workflow** ao salvar arquivos Python (auto-discovery)
3. **Confusão** sobre quais testes eram unitários vs. scripts de validação manual

### Scripts Problemáticos Identificados

Localizados originalmente em:
- `test_apply_theme_fix.py` (raiz do projeto)
- `tests/test_theme_visual.py`
- `tests/test_toolbar_ctk_visual.py`
- `tests/test_toggle_fix.py`
- `tests/modules/clientes/test_clientes_toolbar_ctk_visual_polish_smoke.py`
- `tests/modules/clientes/test_clientes_visual_polish_surface.py`

**Problema técnico**: Esses scripts executavam `root.mainloop()` diretamente no escopo do módulo, sem proteção `if __name__ == "__main__"`.

---

## Solução Implementada

### A) Scripts Visuais Movidos e Corrigidos

Os scripts visuais manuais foram:

1. **Movidos para `scripts/visual/`** (fora da coleta do pytest)
2. **Renomeados** removendo prefixo `test_`:
   - `test_apply_theme_fix.py` → `scripts/visual/apply_theme_clientes.py`
   - `tests/test_theme_visual.py` → `scripts/visual/theme_clientes_visual.py`
   - `tests/test_toolbar_ctk_visual.py` → `scripts/visual/toolbar_ctk_clientes_visual.py`
   - `tests/test_toggle_fix.py` → `scripts/visual/toggle_theme_clientes.py`

3. **Refatorados** para usar padrão seguro:
   ```python
   def main():
       """Executa teste visual."""
       # Todo código GUI aqui
       root = tk.Tk()
       # ...
       root.mainloop()

   if __name__ == "__main__":
       main()
   ```

**Garantia**: Agora `import <script>` não executa GUI, apenas quando rodado diretamente.

### B) Configuração do pytest.ini

Adicionado cinto de segurança no `pytest.ini`:

```ini
addopts =
    -q
    --tb=short
    --import-mode=importlib
    --ignore=scripts/visual
    --ignore=test_apply_theme_fix.py  # caso arquivo antigo ainda exista

testpaths = tests
```

- **`testpaths = tests`**: pytest só coleta de `tests/`
- **`--ignore=scripts/visual`**: ignora explicitamente scripts visuais
- **`--ignore=test_apply_theme_fix.py`**: ignora arquivo antigo na raiz (caso exista)

### C) Configuração do VS Code

Adicionado em `.vscode/settings.json`:

```jsonc
{
    // MICROFASE 4.6: Desabilitar auto-discovery de testes e popups
    "python.testing.autoTestDiscoverOnSaveEnabled": false,
    "testing.automaticallyOpenTestResults": "neverOpen"
}
```

**Efeitos**:
- **`autoTestDiscoverOnSaveEnabled: false`**: não roda discovery ao salvar arquivos
- **`automaticallyOpenTestResults: "neverOpen"`**: não abre painel de resultados automaticamente

---

## Como Rodar Scripts Visuais Agora

Os scripts visuais são **manuais** e devem ser executados diretamente:

### Opção 1: Terminal (recomendado)
```bash
# Ative o ambiente virtual
.\.venv\Scripts\Activate.ps1  # PowerShell
# ou
source .venv/bin/activate  # Linux/macOS

# Execute o script desejado
python scripts/visual/theme_clientes_visual.py
python scripts/visual/toolbar_ctk_clientes_visual.py
python scripts/visual/apply_theme_clientes.py
python scripts/visual/toggle_theme_clientes.py
```

### Opção 2: VS Code Run
- Abra o script em `scripts/visual/`
- Clique com botão direito no editor
- Escolha "Run Python File in Terminal"

### Opção 3: Linha de comando absoluta
```bash
python C:\Users\Pichau\Desktop\v1.5.42\scripts\visual\theme_clientes_visual.py
```

---

## Validação da Solução

### Teste 1: Coleta sem popups
```bash
python -m pytest --collect-only -q
```
**Esperado**: Nenhuma janela GUI abre durante a coleta.

### Teste 2: Execução normal
```bash
python -m pytest -q
```
**Esperado**: Testes rodam normalmente, sem popups.

### Teste 3: Salvar arquivo Python
1. Abra qualquer arquivo `.py` em `tests/`
2. Adicione um espaço e salve (Ctrl+S)
3. **Esperado**: Nenhuma janela de teste visual abre

### Teste 4: Script visual manual
```bash
python scripts/visual/theme_clientes_visual.py
```
**Esperado**: Janela de teste visual abre normalmente.

---

## Observações Importantes

### Para Desenvolvedores

1. **Novos scripts visuais**: Sempre crie em `scripts/visual/` (não em `tests/`)
2. **Nomenclatura**: Evite prefixo `test_` em scripts manuais
3. **Padrão obrigatório**: Use `if __name__ == "__main__":` para código GUI
4. **Import seguro**: Nunca execute GUI no escopo do módulo

### Recarregar VS Code

Se os popups ainda ocorrerem após as mudanças:
1. Pressione `Ctrl+Shift+P`
2. Digite "Reload Window"
3. Execute "Developer: Reload Window"

Isso força o VS Code a recarregar as configurações.

### Scripts de Teste Unitário vs. Visual

| Aspecto | Teste Unitário | Script Visual |
|---------|----------------|---------------|
| **Localização** | `tests/` | `scripts/visual/` |
| **Nomenclatura** | `test_*.py` | Sem prefixo `test_` |
| **Execução** | Automática via pytest | Manual via `python` |
| **GUI** | Não pode abrir | Pode abrir janelas |
| **Propósito** | Validação automática | Validação manual/demo |

---

## Scripts Visuais Disponíveis

### 1. `scripts/visual/theme_clientes_visual.py`
**Descrição**: Testa alternância de tema Light/Dark com preview de cores.  
**Uso**: Verificar que paleta de cores muda corretamente.

### 2. `scripts/visual/toolbar_ctk_clientes_visual.py`
**Descrição**: Testa toolbar CustomTkinter isolada.  
**Uso**: Validar visual moderno (cantos arredondados, cores, interatividade).

### 3. `scripts/visual/apply_theme_clientes.py`
**Descrição**: Testa que `apply_theme()` não causa ValueError de 'bg' em widgets CustomTkinter.  
**Uso**: Verificar fix da Microfase 2.1.

### 4. `scripts/visual/toggle_theme_clientes.py`
**Descrição**: Testa que toggle de tema aparece na toolbar e funciona sem TclError.  
**Uso**: Validar integração do switch de tema.

---

## Documentação Relacionada

- [CLIENTES_THEME_IMPLEMENTATION.md](CLIENTES_THEME_IMPLEMENTATION.md) — Implementação do sistema de temas
- [CLIENTES_MICROFASE_2_1_FIX_APPLY_THEME.md](CLIENTES_MICROFASE_2_1_FIX_APPLY_THEME.md) — Fix do ValueError de 'bg'
- [VSCODE_TESTING_CONFIG.md](VSCODE_TESTING_CONFIG.md) — Configuração de testes no VS Code

---

## Histórico de Mudanças

**2025-01-13** — Microfase 4.6
- Scripts visuais movidos para `scripts/visual/`
- Adicionado `if __name__ == "__main__"` em todos os scripts
- Configurado pytest.ini com `--ignore`
- Configurado VS Code com `autoTestDiscoverOnSaveEnabled: false`
- Documentação criada

---

**Autor**: GitHub Copilot  
**Projeto**: RCGestor v1.5.42  
**Microfase**: 4.6 — Parar de abrir "Teste Visual" automaticamente
