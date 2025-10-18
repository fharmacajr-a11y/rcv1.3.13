# 🎨 Guia Rápido - Polimento Visual RC-Gestor

## ✅ O que foi implementado?

### 1. Sistema de Tema Centralizado
- **18 temas** disponíveis (13 claros + 5 escuros)
- **Scaling automático** para DPI 125% (ajustável)
- **Fonte padrão:** Segoe UI 10

### 2. Overlay de Carregamento
- Barra de progresso indeterminada
- Semi-transparente
- Não trava a UI

### 3. Login Não-Bloqueante
- Usa threading
- Mostra overlay durante autenticação
- UI sempre responsiva

### 4. Ícone Oficial
- Configurado em `assets/app.ico` e `rc.ico`
- Aparece na janela e no executável

### 5. Título Padronizado
- "RC — Gestor de Clientes"

---

## 🚀 Como Usar

### Testar Tudo de Uma Vez
```powershell
python scripts/test_ui_polish.py
```

### Executar o App
```powershell
python app_gui.py
```

### Build para Produção
```powershell
pyinstaller build/rc_gestor.spec
```

---

## 🎨 Trocar Tema

### No Código (Permanente)
Edite `ui/theme.py`:
```python
DEFAULT_THEME = "darkly"  # Tema escuro
DEFAULT_SCALING = 1.5     # 150% DPI
```

### Em Runtime (Dinâmico)
```python
from ui.theme_toggle import toggle_theme
toggle_theme(style)  # Alterna claro/escuro
```

### Temas Disponíveis

**Claros:**
- flatly (padrão)
- cosmo, journal, litera, lumen, minty
- pulse, sandstone, united, yeti, morph, simplex, cerulean

**Escuros:**
- darkly
- cyborg, superhero, vapor, solar

---

## 💡 Usar o Overlay em Outras Partes

```python
from ui.widgets.busy import BusyOverlay
import threading

def alguma_operacao_longa():
    overlay = BusyOverlay(janela_pai, "Processando...")
    overlay.show()

    def worker():
        # Fazer operação pesada
        resultado = processar_dados()

        # Voltar pra thread principal
        def finish():
            overlay.hide()
            # Atualizar UI com resultado
        janela_pai.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()
```

---

## 🔧 Ajustar DPI/Scaling

Para monitores com diferentes escalas:

**100% DPI (Full HD):**
```python
DEFAULT_SCALING = 1.0
```

**125% DPI (Full HD / 4K recomendado):**
```python
DEFAULT_SCALING = 1.25  # PADRÃO
```

**150% DPI (4K):**
```python
DEFAULT_SCALING = 1.5
```

---

## 📋 Checklist de Validação

Antes de fazer build final:

- [ ] ✅ Teste passou: `python scripts/test_ui_polish.py`
- [ ] ✅ App abre sem erros: `python app_gui.py`
- [ ] ✅ Login mostra overlay "Conectando..."
- [ ] ✅ Tema aplicado corretamente
- [ ] ✅ Ícone aparece na janela
- [ ] ✅ Título é "RC — Gestor de Clientes"
- [ ] ✅ UI não trava durante login
- [ ] ✅ Build gera .exe: `pyinstaller build/rc_gestor.spec`
- [ ] ✅ Executável tem ícone correto

---

## 🐛 Problemas Comuns

### "BusyOverlay não encontrado"
```python
# Verificar se o pacote foi criado
from ui.widgets.busy import BusyOverlay
```

### "Tema não muda"
```python
# Reiniciar o app após trocar DEFAULT_THEME em ui/theme.py
```

### "Scaling muito grande/pequeno"
```python
# Ajustar DEFAULT_SCALING em ui/theme.py
# Valores típicos: 1.0, 1.25, 1.5
```

### "Ícone não aparece no .exe"
```bash
# Rebuildar
pyinstaller build/rc_gestor.spec --clean
```

---

## 📊 Status dos Testes

Execute `python scripts/test_ui_polish.py` e espere ver:

```
✅ PASSOU - Módulo de tema
✅ PASSOU - Alternância de tema
✅ PASSOU - Overlay de carregamento
✅ PASSOU - Arquivos de ícone
✅ PASSOU - Imports do login
```

---

## 🎯 Próximos Passos

1. **Testar:** `python scripts/test_ui_polish.py`
2. **Executar:** `python app_gui.py`
3. **Fazer login** com e-mail/senha do Supabase
4. **Observar:** Overlay "Conectando..." + tema aplicado
5. **Build:** `pyinstaller build/rc_gestor.spec`
6. **Validar:** Executável com ícone e tema corretos

---

## 📚 Documentação Completa

Veja `docs/PROMPT-3-CHANGES.md` para detalhes técnicos completos.

---

**✨ Aproveite o RC-Gestor com a nova cara profissional!**
