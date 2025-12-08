# Devlog FASE 3 – UX/Performance – UI Blocks Removidos

**Data:** 2025-12-02  
**Autor:** Copilot (Claude Opus 4.5)  
**Branch:** qa/fixpack-04

---

## Objetivo

Identificar e corrigir pontos de bloqueio na UI (Tkinter) onde operações de rede/IO
pesadas estavam sendo executadas na thread principal, causando travamentos.

---

## Pontos de bloqueio identificados

### 1. `src/modules/clientes/forms/client_picker.py`

| Método | Problema | Marcador |
|--------|----------|----------|
| `_load_initial()` | Chamava `list_clients_for_picker()` direto na UI | `TODO-UI-BLOCK` |
| `_do_search()` | Chamava `list_clients_for_picker()` e `search_clients()` direto na UI | `TODO-UI-BLOCK` |

Ambos os métodos faziam requisições Supabase síncronas na thread principal do Tkinter,
travando a interface durante a busca (especialmente com muitos clientes).

---

## Padrão de solução aplicado

Baseado no padrão já existente em:
- `src/ui/dialogs/upload_progress.py`
- `src/ui/files_browser/main.py`
- `src/ui/components/progress_dialog.py` (`BusyDialog`)

### Fluxo implementado:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   UI Event  │────▶│  BusyDialog  │     │   Thread    │
│  (click/key)│     │ (Carregando) │     │  (network)  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       │                   │                    │
       ▼                   ▼                    ▼
  Desabilita          Mostra               Executa
   botões            "Aguarde"           list_clients()
       │                   │                    │
       │                   │                    │
       │                   ▼                    │
       │              UI continua              │
       │              responsiva               │
       │                   │                    │
       │                   │                    ▼
       │                   │             after(0, _on_done)
       │                   │                    │
       ▼                   ▼                    ▼
  Reabilita            Fecha              Atualiza
   botões             BusyDialog          Treeview
```

### Componentes utilizados:

1. **`BusyDialog`** - Diálogo de progresso indeterminado existente
2. **`threading.Thread(daemon=True)`** - Thread de background
3. **`after(0, callback)`** - Retorno seguro para thread de UI
4. **`_safe_after()`** - Wrapper que verifica se widget existe
5. **`_destroyed` flag** - Evita atualizações em widgets destruídos

---

## Mudanças no `client_picker.py`

### Imports adicionados:
```python
import threading
from src.ui.components.progress_dialog import BusyDialog
```

### Novos atributos:
```python
self._busy_dialog: Optional[BusyDialog] = None
self._search_pending = False  # Evita múltiplas buscas simultâneas
self._destroyed = False  # Flag para widgets destruídos
```

### Novos métodos:
- `_safe_after(delay, callback)` - Agenda callback com verificação de existência
- `_close_busy()` - Fecha BusyDialog de forma segura
- `_set_search_enabled(enabled)` - Habilita/desabilita controles de busca
- `destroy()` override - Marca janela destruída e limpa recursos

### Métodos modificados:
- `_load_initial()` - Agora executa em thread com BusyDialog
- `_do_search()` - Agora executa em thread (BusyDialog apenas para lista completa)

---

## QA

```bash
# Lint
ruff check src/modules/clientes/forms/client_picker.py
# ✅ All checks passed!

# Tipos
pyright src/modules/clientes/forms/client_picker.py
# ✅ 0 errors, 0 warnings, 0 informations

# Testes
pytest tests/modules/clientes --no-cov -q
# ✅ 21 passed
```

---

## Testes manuais recomendados

1. **Abrir o client picker**
   - [ ] UI mostra "Carregando clientes..."
   - [ ] Interface continua responsiva durante carregamento
   - [ ] Lista popula corretamente após término

2. **Pesquisar clientes**
   - [ ] Digitação não trava a interface
   - [ ] Resultados aparecem após busca completar
   - [ ] Busca por Enter funciona

3. **Fechar durante carregamento**
   - [ ] Fechar janela no meio de uma busca não causa crash
   - [ ] Nenhum erro no console

---

## Outros pontos analisados

Os demais pontos com chamadas Supabase estão em:
- Camadas de serviço (`service.py`)
- Repositórios (`repository.py`)
- Já são chamados de contextos assíncronos ou têm tratamento adequado

**Não foram identificados outros `TODO-UI-BLOCK` ou comentários similares.**

---

## Conclusão

✅ **FASE 3 completa**

- 1 arquivo modificado: `client_picker.py`
- 2 métodos refatorados para padrão assíncrono
- 0 erros de lint/tipo
- 21 testes passando
- UI permanece responsiva durante operações de rede
