# Scripts Visuais - Módulo Clientes

Esta pasta contém scripts de **teste visual manual** para o módulo Clientes.

⚠️ **IMPORTANTE**: Estes scripts abrem janelas GUI e **NÃO devem** ser executados via pytest.

---

## Scripts Disponíveis

### 1. `theme_clientes_visual.py`
Testa alternância de tema Light/Dark com preview de cores.

**Como rodar**:
```bash
python scripts/visual/theme_clientes_visual.py
```

**O que faz**:
- Exibe janela com preview das cores do tema atual
- Permite alternar entre Light/Dark via switch CustomTkinter
- Valida que preferência é salva automaticamente

---

### 2. `toolbar_ctk_clientes_visual.py`
Testa toolbar CustomTkinter isolada (visual moderno).

**Como rodar**:
```bash
python scripts/visual/toolbar_ctk_clientes_visual.py
```

**O que faz**:
- Exibe toolbar com design CustomTkinter
- Permite testar busca, filtros, ordenação
- Valida cantos arredondados, cores harmonizadas

---

### 3. `apply_theme_clientes.py`
Testa que `apply_theme()` não causa ValueError de 'bg'.

**Como rodar**:
```bash
python scripts/visual/apply_theme_clientes.py
```

**O que faz**:
- Cria ClientesFrame completo
- Testa alternância de tema múltiplas vezes
- Valida que não há ValueError relacionado a 'bg'

---

### 4. `toggle_theme_clientes.py`
Testa que toggle de tema aparece e funciona sem TclError.

**Como rodar**:
```bash
python scripts/visual/toggle_theme_clientes.py
```

**O que faz**:
- Cria ClientesFrame em janela ttkbootstrap
- Valida que toggle aparece à direita da toolbar
- Verifica texto do switch (🌙 Escuro / ☀️ Claro)

---

### 5. `modal_ctk_clientes_visual.py` ⭐ **NOVO (Microfase 6)**
Testa modals CustomTkinter (confirm/alert/error/info).

**Como rodar**:
```bash
python scripts/visual/modal_ctk_clientes_visual.py
```

**O que faz**:
- Exibe app com botões para testar cada tipo de modal
- Testa `ClientesModalCTK.confirm()` (Sim/Não)
- Testa `ClientesModalCTK.alert()` (Aviso)
- Testa `ClientesModalCTK.error()` (Erro)
- Testa `ClientesModalCTK.info()` (Informação)
- Permite alternar tema Light/Dark em tempo real
- Valida ícones (❓⚠️❌ℹ️), cores, atalhos (Enter/Escape)

⚠️ **Requer CustomTkinter instalado**: `pip install customtkinter`

---

## Por Que Não São Testes Pytest?

Estes scripts:
- ✅ Abrem janelas GUI interativas (Tkinter/CustomTkinter)
- ✅ Requerem validação visual humana
- ✅ Não são determinísticos (cores dependem de tema ativo)
- ❌ Não podem rodar em CI/CD headless
- ❌ Não devem ser coletados pelo pytest

---

## Como Adicionar Novo Script Visual

1. **Crie arquivo** em `scripts/visual/` (sem prefixo `test_`)
2. **Use padrão obrigatório**:
   ```python
   def main():
       # Todo código GUI aqui
       root = tk.Tk()
       # ...
       root.mainloop()
   
   if __name__ == "__main__":
       main()
   ```
3. **Documente** neste README

---

## Documentação Relacionada

- [docs/VSCODE_TESTS_NO_AUTO_POPUP.md](../../docs/VSCODE_TESTS_NO_AUTO_POPUP.md) — Por que scripts foram movidos aqui
- [docs/CLIENTES_THEME_IMPLEMENTATION.md](../../docs/CLIENTES_THEME_IMPLEMENTATION.md) — Sistema de temas
- [docs/CLIENTES_MICROFASE_6_SUBDIALOGS_CUSTOMTKINTER.md](../../docs/CLIENTES_MICROFASE_6_SUBDIALOGS_CUSTOMTKINTER.md) — Modals CustomTkinter ⭐ **NOVO**

---

**Projeto**: RCGestor v1.5.42  
**Microfases**: 4.6, 6
