# Guia Rápido de Validação - Migração CTk

Este guia fornece comandos rápidos para validar as mudanças durante a migração CTk.

---

## 🧪 Testes Automatizados

### Validação Completa (executar após cada commit)

```powershell
# 1. Validar política TTK
python scripts/validate_ttk_policy.py --ci

# 2. Testes CI
pytest tests/ci/test_ttk_policy.py -q

# 3. CTK Audit (verificar redução de ocorrências)
python -m src.ui.ctk_audit | Select-String "Total:"

# 4. Testes específicos (exemplo: Hub)
pytest tests/modules/hub/ -v --tb=short
```

### Validação Rápida (antes de commit)

```powershell
# One-liner: Política + CI
python scripts/validate_ttk_policy.py --ci && pytest tests/ci/test_ttk_policy.py -q
```

---

## 🎨 Testes Visuais Manuais

### Checklist de Dark Mode

Após modificar um arquivo, testar:

1. **Abrir o app**
   ```powershell
   python main.py
   ```

2. **Alternar modo** (pressionar `F11` ou usar menu)
   - Light → Dark
   - Dark → Light
   - Repetir 2-3 vezes

3. **Verificar componentes modificados**:
   - [ ] Cores de fundo corretas (sem branco no Dark)
   - [ ] Cores de texto legíveis
   - [ ] Bordas e sombras apropriadas
   - [ ] Treeview com zebra colorida (não branca)
   - [ ] Botões com hover funcional

### Testes por Área

#### Dashboard (FASE 1)
```powershell
# Abrir e testar Hub
python main.py
# Navegar: Hub → Dashboard
# Toggle Light/Dark (F11)
# Verificar:
# - Cards de status (Clientes, Pendências, Tarefas)
# - Radar de obrigações (quadrantes)
# - Timeline de atividades
# - Lista de hot leads
```

#### Dialogs (FASE 2)
```powershell
# Abrir e testar dialogs
python main.py
# Navegar: Hub → Notas
# Criar nova nota → verificar dialog sem flash
# Ver histórico → verificar dialog sem flash
# Toggle Light/Dark durante dialog aberto
```

#### Lista de Clientes (BUGFIX B)
```powershell
# Testar lista de clientes no Dark
python main.py
# Navegar: Clientes → Lista
# Toggle para Dark (F11)
# Verificar zebra colorida (não branca)
# Alternar Ativos/Lixeira → zebra deve manter cores Dark
```

#### UploadsBrowser (BUGFIX C)
```powershell
# Testar browser de arquivos
python main.py
# Navegar: Clientes → Selecionar cliente → Arquivos
# Observar abertura → NÃO deve haver flash branco
# Toggle Light/Dark → titlebar deve acompanhar
```

---

## 📊 Verificação de Progresso

### Contagem de Ocorrências CTK Audit

```powershell
# Antes (baseline)
python -m src.ui.ctk_audit | Select-String "Total:"
# Esperado: Total: 227 ocorrências em 28 arquivo(s)

# Após cada FASE
python -m src.ui.ctk_audit | Select-String "Total:"

# Comparar:
# - FASE 1: ~167 ocorrências (26% redução)
# - FASE 2: ~142 ocorrências (37% redução)
# - FASE 3: ~82 ocorrências (64% redução)
# - FASE 4: ~62 ocorrências (73% redução)
# - FASE 5: ~27 ocorrências (88% redução)
```

### Top 5 Arquivos com Problemas

```powershell
# Verificar quais arquivos ainda têm problemas
python -m src.ui.ctk_audit --fix | Select-String "^📄"
```

---

## 🐛 Troubleshooting

### Problema: Testes CI falhando

```powershell
# Verificar qual teste falhou
pytest tests/ci/test_ttk_policy.py -v

# Se falhar em test_no_import_ttkbootstrap:
# - Verificar se adicionou import de ttkbootstrap acidentalmente
# - Buscar por "ttkbootstrap" no código:
grep -r "ttkbootstrap" src/
```

### Problema: CTK Audit mostra mais ocorrências

```powershell
# Verificar se criou novos problemas
git diff src/

# Buscar por padrões problemáticos:
# - tk.Frame, tk.Label, tk.Button (sem ctk prefix)
# - bg=, foreground=, relief=
```

### Problema: Dark Mode não aplica

```powershell
# Verificar se __init__ chama prepare_hidden_window:
grep -A 5 "def __init__" src/path/to/file.py

# Verificar se usa show_centered_no_flash:
grep "show_centered" src/path/to/file.py
```

### Problema: Zebra da Treeview branca no Dark

```powershell
# Verificar se chama _sync_tree_theme_and_zebra:
grep "_sync_tree_theme_and_zebra" src/modules/clientes/ui/view.py

# Verificar se aplica_zebra usa cores do cache:
grep -A 3 "_on_theme_changed" src/modules/clientes/ui/view.py
```

---

## 🔄 Workflow de Commit

### Template de Commit

```bash
git add <arquivo>
git commit -m "FASE X - Commit X.Y: <arquivo> - <descrição>

- Substituir tk.Xxx por ctk.CTkXxx (N ocorrências)
- Remover atributos não suportados (bg=, relief=, etc.)
- Testes: validate_ttk_policy.py + test_ttk_policy.py passando
- CTK Audit: X → Y ocorrências (-Z%)
"
```

### Exemplo Real

```bash
git add src/modules/hub/views/dashboard_center.py
git commit -m "FASE 1 - Commit 1.1: dashboard_center.py - ScrolledText → CTkTextbox

- Substituir ScrolledText por ctk.CTkTextbox (4 ocorrências)
- Linhas: 274, 1162, 1294, 382-385 (remover função obsoleta)
- Ajustar parâmetros: wrap='word', height estimado
- Testes: validate_ttk_policy.py + test_ttk_policy.py OK
- CTK Audit: 227 → 223 ocorrências (-1.8%)
"

git push origin main
```

---

## 📋 Checklist de PR

Antes de criar Pull Request:

- [ ] Todos os testes CI passando
- [ ] `validate_ttk_policy.py --ci` retorna PASS
- [ ] CTK Audit mostra redução de ocorrências
- [ ] Testado manualmente em Light e Dark mode
- [ ] Sem flash branco em dialogs/janelas
- [ ] Treeviews com zebra correta
- [ ] Sem warnings de tipo (Pyright/mypy)
- [ ] Documentação atualizada (se aplicável)

---

## 🎯 Comandos One-Liner Úteis

```powershell
# Validação completa em uma linha
python scripts/validate_ttk_policy.py --ci && pytest tests/ci/test_ttk_policy.py -q && python -m src.ui.ctk_audit | Select-String "Total:"

# Contar ocorrências de padrões problemáticos
(sls "tk\.Frame|tk\.Label|tk\.Button" -Path src\modules\hub\views\*.py).Count

# Ver apenas arquivos com mais de 10 ocorrências
python -m src.ui.ctk_audit | sls "^📄.*\b1[0-9]\b"

# Diff das mudanças no último commit
git diff HEAD~1 -- src/

# Executar smoke test específico
pytest tests/modules/hub/test_dashboard_center_smoke.py -v
```

---

## 📞 Referência Rápida

| Comando | Propósito |
|---------|-----------|
| `F11` | Toggle Light/Dark no app |
| `python -m src.ui.ctk_audit` | Ver todas as ocorrências |
| `python -m src.ui.ctk_audit --fix` | Ver ocorrências + sugestões |
| `pytest tests/ci/ -v` | Testes CI verbose |
| `grep -r "pattern" src/` | Buscar padrão no código |

---

**Dica**: Salve esta página como favorito para consulta rápida durante a migração!
