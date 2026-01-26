# MICROFASE 20 — Pylance "openFilesOnly" (Opção A) + Baseline Leve

**Data:** 15 de janeiro de 2026  
**Objetivo:** Reduzir o "1K+ Problems" do Pylance limitando diagnósticos aos arquivos abertos no editor.

---

## 📋 Alterações realizadas

### 1. `.vscode/settings.json`

Foram adicionadas/atualizadas as seguintes configurações do Pylance:

```json
{
  "python.analysis.diagnosticMode": "openFilesOnly",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.stubPath": "typings"
}
```

**Antes:**
- `"python.analysis.diagnosticMode": "workspace"` — analisava **todos os arquivos** do workspace

**Depois:**
- `"python.analysis.diagnosticMode": "openFilesOnly"` — analisa **somente arquivos abertos** no editor
- `"python.analysis.typeCheckingMode": "basic"` — verificação de tipos leve (vs "standard" ou "strict")
- `"python.analysis.stubPath": "typings"` — mantém stubs customizados

### 2. Pasta `typings/`

A pasta `typings/` já existe no workspace com stubs customizados para:
- `customtkinter/`
- `openpyxl/`
- `postgrest/`
- `supabase/`
- `tkinter/`
- `ttkbootstrap/`

**Nenhuma alteração foi necessária nos stubs.**

---

## 🔄 Como aplicar as mudanças no VS Code

### Opção 1: Recarregar a janela (recomendado)

1. Abra a Command Palette: `Ctrl+Shift+P` (Windows/Linux) ou `Cmd+Shift+P` (Mac)
2. Digite e selecione: **`Developer: Reload Window`**
3. Aguarde o VS Code recarregar — o Pylance aplicará as novas configurações

### Opção 2: Reiniciar o Pylance Language Server

1. Command Palette → **`Pylance: Restart Server`**
2. Se não encontrar, use **`Developer: Reload Window`**

### Verificação

Após recarregar:
- O painel "Problems" (Problemas) deve exibir **muito menos erros/warnings**
- Apenas arquivos **abertos no editor** serão analisados
- Ao abrir um arquivo, o Pylance reportará problemas para aquele arquivo especificamente

---

## ⚙️ Como voltar ao modo antigo

Se preferir analisar **todo o workspace** novamente:

1. Edite `.vscode/settings.json`
2. Altere:
   ```json
   "python.analysis.diagnosticMode": "workspace"
   ```
3. Salve e recarregue a janela (`Developer: Reload Window`)

---

## 📊 Impacto esperado

| Aspecto | Antes (workspace) | Depois (openFilesOnly) |
|---------|-------------------|------------------------|
| **Problems exibidos** | 1K+ | Apenas arquivos abertos (~10-50) |
| **Performance do Pylance** | Lenta (analisa tudo) | Rápida (analisa só o necessário) |
| **Detecção de problemas** | Todos os arquivos | Sob demanda (ao abrir) |
| **Runtime/Testes** | Não afetado | Não afetado |

---

## ⚠️ Observações importantes

1. **Isso NÃO altera o comportamento do código em runtime** — é apenas uma configuração de análise estática do VS Code.

2. **Testes continuam funcionando normalmente** — pytest, mypy, ruff, etc. são ferramentas independentes.

3. **Se você abrir um arquivo com problemas**, o Pylance reportará os erros daquele arquivo no painel "Problems".

4. **Para análise completa do workspace**, execute manualmente:
   - `mypy src/` (verificação de tipos)
   - `ruff check src/` (linting)
   - `pytest` (testes)

5. **`stubPath` mantido em `typings/`** — stubs customizados continuam funcionando normalmente.

---

## ✅ Validação

Smoke test executado com sucesso:

```bash
python -m pytest -c pytest_cov.ini --no-cov -q tests/modules/clientes
```

**Resultado:** Testes passaram sem problemas — nenhuma funcionalidade foi afetada.

---

## 🔗 Referências

- [Python in VS Code - Settings Reference](https://code.visualstudio.com/docs/python/settings-reference)
- [Pylance Settings and Customization](https://github.com/microsoft/pylance-release/blob/main/CONFIGURATION.md)
- [Type Checking Modes](https://github.com/microsoft/pylance-release#type-checking-modes)

---

**Microfase 20 concluída com sucesso.** ✅
