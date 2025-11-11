# Checklist de Validação Rápida - HOTFIX File Dialog

## ✅ Validação Técnica (Automática)

### Testes Unitários
```bash
# Testar novo módulo file_select
pytest tests/test_file_select.py -v
# ✅ Esperado: 15 passed

# Testar módulo archives (regressão)
pytest tests/test_archives.py -v
# ✅ Esperado: 12 passed, 1 skipped

# Executar todos os testes
pytest tests/ -v
# ✅ Esperado: 27+ passed
```

**Status**: ✅ PASSOU (15 + 12 = 27 testes)

---

## 🔬 Validação Manual (Crítica)

### Teste 1: Arquivos RAR Aparecem no Diálogo

**Passos**:
1. Executar: `python -m src.app_gui`
2. Navegar até **Auditoria**
3. Clicar em **"Enviar ZIP/RAR p/ Auditoria"**
4. No diálogo do Windows, verificar:
   - [ ] Filtro padrão: **"Arquivos compactados (*.zip; *.rar)"**
   - [ ] Arquivos `.rar` **APARECEM** na lista
   - [ ] Arquivos `.zip` aparecem na lista
   - [ ] Filtro "RAR" isolado funciona
   - [ ] Filtro "ZIP" isolado funciona

**Evidência**: Screenshot do diálogo mostrando arquivos `.rar` visíveis.

---

### Teste 2: Logs de Debug Corretos

**Passos**:
1. Configurar logging em DEBUG (se necessário)
2. Executar aplicação
3. Abrir diálogo de arquivo
4. Verificar logs no console:

```
DEBUG - rc.ui.file_select - Abrindo askopenfilename | caller=.../view.py:673 | filetypes=[('Arquivos compactados', ('*.zip', '*.rar')), ...]
```

**Checklist**:
- [ ] Log mostra `filetypes=` com valor completo
- [ ] Padrão é **tupla**: `('*.zip', '*.rar')` (não string)
- [ ] Log mostra `caller=` com arquivo e linha
- [ ] Log de retorno aparece após seleção

---

### Teste 3: Validação de Extensão

**Passos**:
1. Abrir diálogo
2. Mudar filtro para: **"Todos os arquivos (*.*)"**
3. Selecionar arquivo com extensão inválida (ex: `.txt`, `.7z`, `.tar.gz`)
4. Verificar mensagem de erro:

```
Arquivo não suportado

Apenas arquivos .zip e .rar são aceitos.
Arquivo selecionado: teste.txt
```

**Checklist**:
- [ ] Mensagem aparece imediatamente após seleção
- [ ] Nome do arquivo está na mensagem
- [ ] Operação é cancelada (não prossegue)

---

## 🚀 Teste Rápido (Script Automático)

```bash
python scripts/test_file_dialog_manual.py
```

**O que faz**:
- Abre o diálogo automaticamente
- Mostra logs em DEBUG
- Mostra informações do arquivo selecionado
- Valida extensão

**Checklist após execução**:
- [ ] Diálogo abriu corretamente
- [ ] Logs mostraram tupla de padrões
- [ ] Arquivos `.rar` visíveis
- [ ] Validação funcionou

---

## 📋 Validação de Código

### Estrutura do ARCHIVE_FILETYPES

```python
from src.ui.dialogs.file_select import ARCHIVE_FILETYPES

# Deve ser exatamente:
[
    ("Arquivos compactados", ("*.zip", "*.rar")),  # ← Tupla de padrões
    ("ZIP", "*.zip"),
    ("RAR", "*.rar"),
    ("Todos os arquivos", "*.*"),
]
```

**Verificar**:
- [ ] Primeiro item usa **tupla** `("*.zip", "*.rar")`
- [ ] **NÃO** usa string `"*.zip *.rar"`
- [ ] **NÃO** usa ponto-e-vírgula `"*.zip;*.rar"`

---

## 🔍 Comparação: Antes vs Depois

### ANTES (Bugado)
```python
# ❌ String concatenada - Tkinter ignora após espaço
filetypes=[("Arquivos compactados", "*.zip *.rar")]
```
**Resultado**: Apenas `.zip` visível no diálogo.

### DEPOIS (Corrigido)
```python
# ✅ Tupla de padrões - Tkinter reconhece ambos
filetypes=[("Arquivos compactados", ("*.zip", "*.rar"))]
```
**Resultado**: Tanto `.zip` quanto `.rar` visíveis.

---

## ✅ Checklist Final

### Funcionalidade Core
- [x] Helper `file_select.py` criado
- [x] Tupla de padrões implementada
- [x] Logging de debug funciona
- [x] Validação de extensão funciona
- [x] Integração em `view.py`

### Testes
- [x] 15 testes unitários (file_select)
- [x] 12 testes integração (archives)
- [ ] Teste manual: RAR visível ⚠️ **CRÍTICO**
- [ ] Teste manual: Logs corretos
- [ ] Teste manual: Validação funciona

### Documentação
- [x] `.docs/HOTFIX_FILE_DIALOG.md`
- [x] Script de teste manual
- [x] Checklist de validação

### Git
- [x] Branch `fix/rar-dialog-filetypes` criada
- [x] Commit com mensagem descritiva
- [x] Push para origin
- [ ] Pull Request aberto
- [ ] Code review aprovado
- [ ] Merge para main

---

## 🎯 Critério de Sucesso

**O hotfix é considerado bem-sucedido se**:

1. ✅ Arquivos `.rar` **APARECEM** no diálogo do Windows
2. ✅ Logs mostram tupla: `('*.zip', '*.rar')`
3. ✅ Validação rejeita extensões inválidas
4. ✅ 27+ testes passando
5. ✅ Zero regressões (funcionalidade existente intacta)

---

## 📞 Se Algo Falhar

### RAR não aparece no diálogo
- Verificar que está usando `select_archive_file()` e não `filedialog` direto
- Verificar logs: deve mostrar tupla, não string
- Verificar que não há override de `filetypes` em outro lugar

### Logs não aparecem
- Configurar logging: `logging.basicConfig(level=logging.DEBUG)`
- Verificar import: `from src.ui.dialogs.file_select import select_archive_file`

### Validação não funciona
- Verificar que `validate_archive_extension()` foi chamado após seleção
- Verificar que mensagem de erro está sendo exibida

---

**Data**: 11/11/2025  
**Status**: ✅ IMPLEMENTADO - AGUARDANDO VALIDAÇÃO MANUAL  
**Próximo Passo**: Executar teste manual e abrir PR
