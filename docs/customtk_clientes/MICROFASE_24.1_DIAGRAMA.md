# MICROFASE 24.1 - Diagrama de Fluxo

## 🔄 Fluxo Corrigido de Inicialização

```
┌─────────────────────────────────────────────────────────────────────┐
│ src/core/app.py (__main__)                                          │
├─────────────────────────────────────────────────────────────────────┤
│ 1. configure_logging()                                              │
│ 2. auto_enable_if_env()  ← 🛡️ Guard rails (RC_STRICT_TK_ROOT=1)   │
│    └─> tkinter.NoDefaultRoot() se modo estrito                     │
│ 3. app = App(start_hidden=True)                                     │
│    ├─> global_theme_manager.initialize()  ⚠️ ANTES de criar root   │
│    ├─> ctk.CTk.__init__(self)  ← ✅ Única root criada aqui        │
│    ├─> global_theme_manager.set_master(self)  ← 🔑 Define master   │
│    └─> bootstrap_main_window(app)                                  │
│ 4. show_splash() + ensure_logged()                                 │
│ 5. app.mainloop()                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Fluxo de Tema (ttk.Style)

### ❌ ANTES (Problema):
```
global_theme_manager.initialize()
  └─> apply_global_theme(mode, color)
      └─> apply_ttk_widgets_theme(mode)  ⚠️ master=None
          └─> ttk.Style()  ❌ Cria root implícita se não existir!
              └─> 💥 Janela "tk" aparece
```

### ✅ DEPOIS (Corrigido):
```
App.__init__()
  ├─> ctk.CTk.__init__(self)  ← Root criada PRIMEIRO
  ├─> global_theme_manager.set_master(self)  ← Master definido
  └─> Qualquer chamada futura:
      apply_ttk_widgets_theme(mode)
        └─> master = theme_manager._master_ref  ✅ Usa root existente
            └─> ttk.Style(master=master)  ✅ Não cria nova root
```

---

## 🔚 Fluxo de Shutdown

### ❌ ANTES (Problema):
```
user fecha janela (X)
  └─> app.destroy()
      ├─> destroy_window()  ← Cleanup
      └─> super().destroy()  ❌ Mas after jobs ainda ativos!
          └─> 💥 "invalid command name" errors
```

### ✅ DEPOIS (Corrigido):
```
user fecha janela (X)
  └─> app.destroy()
      ├─> if _is_destroying: return  ✅ Idempotência
      ├─> _is_destroying = True
      ├─> destroy_window()
      │   ├─> stop pollers
      │   ├─> stop status_monitor
      │   └─> cancel_all_after_jobs(app)  ✅ Cancela callbacks
      ├─> quit()  ← Para mainloop
      └─> super().destroy()  ✅ Sem erros!
```

---

## 🛡️ Guard Rails (Modo Estrito)

### Ativação:
```bash
# Windows PowerShell
$env:RC_STRICT_TK_ROOT="1"
python main.py

# Linux/macOS
export RC_STRICT_TK_ROOT=1
python main.py
```

### Comportamento:
```python
# src/ui/tk_root_guard.py
def enable_strict_mode():
    tk.NoDefaultRoot()  ← Desabilita root implícita
    
# Qualquer código que tente usar root implícita agora falha:
widget = ttk.Label()  ❌ RuntimeError: No master specified and tkinter 
                          default root has been disabled
                          
# Forçado a passar master:
widget = ttk.Label(master=app)  ✅ OK
```

### Logging:
```
[tk_root_guard] Modo estrito ativado: NoDefaultRoot() chamado
[tk_root_guard] Apenas 1 toplevel detectada (esperado)  ✅
[tk_root_guard] Múltiplas toplevels detectadas: 2 janelas!  ⚠️
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes (❌) | Depois (✅) |
|---------|-----------|------------|
| **Janela "tk"** | Aparece janela extra vazia | Apenas 1 janela (App) |
| **ttk.Style()** | `ttk.Style()` sem master | `ttk.Style(master=app)` |
| **Root implícita** | Criada automaticamente | Bloqueada em modo estrito |
| **Shutdown errors** | `invalid command name` | Sem erros (after cancelado) |
| **Cleanup** | Pode executar 2x | Idempotente (`_is_destroying`) |
| **Sequência destroy** | `destroy()` direto | `cancel_jobs → quit() → destroy()` |

---

## 🔍 Pontos de Verificação (Debug)

### 1. Verificar root única:
```python
from src.ui.tk_root_guard import check_multiple_roots

count = check_multiple_roots(app)
assert count == 1, f"Múltiplas roots detectadas: {count}"
```

### 2. Verificar master em ttk.Style:
```python
# src/ui/ttk_compat.py:66
style = ttk.Style(master=master)  # master deve ser App instance
assert master is not None, "ttk.Style sem master!"
```

### 3. Verificar after jobs cancelados:
```python
# Antes de destroy:
after_ids = app.tk.call("after", "info")
print(f"After jobs pendentes: {len(after_ids)}")

# Após cancel_all_after_jobs:
cancelled = cancel_all_after_jobs(app)
print(f"Cancelados: {cancelled} jobs")
```

---

## 🎯 Smoke Test Checklist

```
[ ] 1. Executar: python main.py
[ ] 2. Observar startup:
    [ ] Splash aparece
    [ ] Login funciona
    [ ] Hub carrega
    [ ] NENHUMA janela "tk" extra aparece  ← 🎯 CRÍTICO
    
[ ] 3. Testar toggle tema:
    [ ] Ctrl+T alterna light/dark
    [ ] Treeview mantém legibilidade
    [ ] Sem erros no console
    
[ ] 4. Testar navegação:
    [ ] Hub → Clientes
    [ ] Clientes → Uploads
    [ ] Uploads → Hub
    
[ ] 5. Fechar app:
    [ ] Clicar X ou Alt+F4
    [ ] Console NÃO mostra:
        ❌ "invalid command name"
        ❌ "can't delete Tcl command"
        ❌ TclError
    [ ] App fecha limpo  ← 🎯 CRÍTICO
    
[ ] 6. Modo estrito (opcional):
    [ ] set RC_STRICT_TK_ROOT=1
    [ ] python main.py
    [ ] Verificar log: "Modo estrito ativado"
    [ ] App funciona normalmente
```

---

## 📝 Regressões Possíveis (Monitorar)

1. **Treeview sem estilo**: Se ttk.Style não receber master, cores podem não aplicar
   - **Sintoma**: Treeview totalmente branco ou preto ilegível
   - **Fix**: Verificar que `theme_manager.set_master(app)` foi chamado

2. **After jobs não cancelados**: Se algum componente agendar after mas não registrar ID
   - **Sintoma**: Ainda aparecem erros "invalid command name" ao fechar
   - **Fix**: Componente deve armazenar after_id e cancelar em destroy

3. **Root implícita em import-time**: Se algum módulo criar widgets no import
   - **Sintoma**: Janela "tk" volta a aparecer
   - **Fix**: Modo estrito detecta (RC_STRICT_TK_ROOT=1)

---

**Fim do Diagrama**
