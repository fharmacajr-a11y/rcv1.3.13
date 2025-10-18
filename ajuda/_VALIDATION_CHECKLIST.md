# ✅ Checklist de Validação - Code Janitor

**Projeto:** RC-Gestor v1.0.37  
**Data:** 18 de outubro de 2025

---

## 📋 Pré-Limpeza

- [ ] Backup completo do projeto criado
- [ ] Commit atual do Git (se versionado)
- [ ] Nenhum processo Python rodando (fechar VSCode Python Extensions, etc.)
- [ ] Leitura completa do relatório `_CODE_JANITOR_REPORT.md`
- [ ] Revisão dos comandos em `_CLEANUP_DRYRUN_POWERSHELL.ps1` ou `_CLEANUP_DRYRUN_BASH.sh`

---

## 🗑️ Durante a Limpeza

### Passo 1: Executar Dry-Run

**PowerShell (Windows):**
```powershell
cd "c:\Users\Pichau\Desktop\v1.0.37 (limpar e ok)"
.\_CLEANUP_DRYRUN_POWERSHELL.ps1
```

**Bash (Linux/macOS):**
```bash
cd "/caminho/para/v1.0.37 (limpar e ok)"
chmod +x _CLEANUP_DRYRUN_BASH.sh
./_CLEANUP_DRYRUN_BASH.sh
```

- [ ] Script executado sem erros
- [ ] Pasta `_trash_YYYYMMDD_HHMM/` criada
- [ ] Todos os itens esperados foram movidos

---

### Passo 2: Validação de Compilação

```powershell
# PowerShell
python -m compileall . 2>&1 | Select-String "SyntaxError"
```

```bash
# Bash
python -m compileall . 2>&1 | grep "SyntaxError"
```

- [ ] Nenhum erro de sintaxe encontrado
- [ ] Todos os `.py` compilam corretamente

---

### Passo 3: Smoke Test - Execução

```powershell
python app_gui.py
```

**Checklist de Funcionalidades Básicas:**

- [ ] Aplicação inicia sem erros
- [ ] Splash screen aparece
- [ ] Tela de login aparece
- [ ] Login funciona (se credenciais disponíveis)
- [ ] Tela principal carrega
- [ ] Ícone `rc.ico` aparece na janela
- [ ] Menu superior funciona
- [ ] Status de rede aparece (ONLINE/OFFLINE/LOCAL)
- [ ] Pode abrir formulário de novo cliente
- [ ] Pode listar clientes existentes
- [ ] Tema escuro/claro alterna corretamente
- [ ] Funcionalidade de busca responde
- [ ] Logs não apresentam erros críticos

**Se algum item falhar:**
```powershell
# PowerShell - Reverter
$trash = "_trash_YYYYMMDD_HHMM"  # Use o nome correto
Move-Item -Path "$trash\*" -Destination . -Force -Recurse
Remove-Item -Path $trash -Force
```

```bash
# Bash - Reverter
trash="_trash_YYYYMMDD_HHMM"  # Use o nome correto
mv "$trash"/* .
rm -rf "$trash"
```

---

### Passo 4: Testes Adicionais (Opcional)

- [ ] Testar upload de arquivo
- [ ] Testar download de arquivo
- [ ] Testar criação de cliente
- [ ] Testar edição de cliente
- [ ] Testar exclusão de cliente (lixeira)
- [ ] Verificar integração com Supabase
- [ ] Testar subpastas (se aplicável)
- [ ] Testar leitura de PDF (se aplicável)
- [ ] Verificar CHANGELOG em runtime (`runtime_docs/CHANGELOG.md`)

---

## ✅ Pós-Limpeza (Se tudo passou)

### Finalização

- [ ] Deletar pasta de quarentena:
  ```powershell
  # PowerShell
  Remove-Item -Recurse -Force "_trash_YYYYMMDD_HHMM"
  ```
  ```bash
  # Bash
  rm -rf "_trash_YYYYMMDD_HHMM"
  ```

- [ ] Commit das mudanças no Git (se versionado):
  ```bash
  git add .
  git commit -m "chore: limpeza de código - remover caches, build artifacts e dev docs"
  ```

- [ ] Atualizar `.gitignore` se necessário:
  ```gitignore
  # Caches
  __pycache__/
  .ruff_cache/
  .import_linter_cache/

  # Build
  build/
  dist/
  *.spec.bak

  # IDE
  .vscode/
  .idea/

  # Env
  .env
  .venv/
  venv/

  # Temp
  _trash_*/
  ```

---

## 📊 Resultados Esperados

### Antes da Limpeza
```
Tamanho total: ~XXX MB
Arquivos Python: ~XXX
Pastas: ~XXX
```

### Depois da Limpeza
```
Tamanho total: ~(XXX - 60-220) MB
Arquivos Python: ~(redução de arquivos .pyc)
Pastas: ~(menos ~8-10 pastas)
```

### Benefícios
- ✅ Projeto mais limpo e organizado
- ✅ Menor uso de disco (~60-220 MB liberados)
- ✅ Mais rápido para backup/clone
- ✅ Mais fácil de navegar
- ✅ Sem caches obsoletos
- ✅ Build artifacts limpos (rebuild fresh)

---

## 🚨 Troubleshooting

### Problema: "ModuleNotFoundError: No module named 'X'"
**Solução:** Verifique se acidentalmente moveu uma pasta importante. Restaure da quarentena.

### Problema: "FileNotFoundError: rc.ico"
**Solução:** Verifique se `rc.ico` ainda está na raiz. Se movido acidentalmente, restaure.

### Problema: "FileNotFoundError: runtime_docs/CHANGELOG.md"
**Solução:** NÃO deve acontecer (whitelist). Se acontecer, restaure da quarentena.

### Problema: Aplicação não inicia
**Solução:** Restaure tudo da quarentena e revise o relatório.

---

## 📝 Notas

- **Caches são regeneráveis:** `__pycache__`, `.ruff_cache` - podem ser deletados a qualquer momento
- **Build é regenerável:** `build/`, `dist/` - rode PyInstaller novamente
- **Docs de dev:** `ajuda/`, `scripts/` - guarde backup externo se precisar depois
- **Modules vazios:** `detectors/`, `infrastructure/` - podem ser removidos se não planejados para uso futuro

---

## ✍️ Assinatura

- [ ] Limpeza executada por: _______________
- [ ] Data: _______________
- [ ] Todos os testes passaram: ☐ SIM  ☐ NÃO
- [ ] Quarentena deletada: ☐ SIM  ☐ NÃO (motivo: ____________)

---

**Fim do Checklist**
