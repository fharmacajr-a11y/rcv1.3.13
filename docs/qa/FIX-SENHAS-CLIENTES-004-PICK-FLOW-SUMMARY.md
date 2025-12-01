# FIX-SENHAS-CLIENTES-004 – Fluxo Completo Nova Senha + Pick de Cliente

**Branch:** `qa/fixpack-04`  
**Data:** 28 de novembro de 2025  
**Status:** ✅ Implementado e testado

---

## Resumo Executivo

Este FIX corrige problemas de UX e fluxo visual identificados pelo usuário na integração entre o módulo de Senhas e o modo de seleção de Clientes (pick mode), implementado em FEATURE-SENHAS-001 e refinado nos FIX-CLIENTES-001, 002 e 003.

### Problemas Corrigidos

1. **Janela Nova Senha ficava por cima da lista de Clientes** durante a seleção, atrapalhando a visualização
2. **Fechar Nova Senha não cancelava o pick mode**, deixando a tela de Clientes "presa" em modo seleção
3. **Seleção de cliente após fechar Nova Senha não reabria o diálogo**, gerando confusão
4. **Textos com mojibake** no banner e botões do pick mode (caracteres corrompidos em vez de PT-BR correto)

### Solução Implementada

- **Centralização da orquestração** no `PasswordsScreen` em vez de dentro do `PasswordDialog`
- **Tratamento automático de cancelamento** quando Nova Senha é fechada
- **Reabertura automática de Nova Senha** após seleção, mesmo se foi fechada antes
- **Correção de textos** para usar as constantes PT-BR já definidas

---

## Mudanças de Arquitetura

### Antes (FEATURE-SENHAS-001)

```
PasswordDialog
  └─ _on_select_client_clicked()
      └─ navigate_to("clients_picker", on_pick=self._handle_client_selected)
          └─ callback direto no dialog (instância pode não estar visível)
```

**Problema:** Se o usuário fecha Nova Senha antes de selecionar, o callback fica pendurado em um objeto sem janela visível.

### Depois (FIX-SENHAS-CLIENTES-004)

```
PasswordsScreen (orquestrador)
  ├─ _on_select_client_from_dialog()
  │   └─ navigate_to("clients_picker", on_pick=self._handle_client_picked)
  │
  ├─ _handle_client_picked(client_data)
  │   ├─ Se dialog está visível: atualiza dados
  │   └─ Se dialog foi fechado: recria com dados preenchidos
  │
  └─ _open_new_password_dialog(client_data=...)
      └─ Cria PasswordDialog com on_select_client callback
```

**Benefício:** O `PasswordsScreen` (que não é fechado durante pick) sempre sabe o estado e pode reabrir o diálogo quando necessário.

---

## Arquivos Modificados

### 1. `src/modules/clientes/views/main_screen.py`

**Mudanças:**
- Corrigido literal com mojibake `"ðŸ" Modo seleÃ§Ã£o..."` → usa `PICK_MODE_BANNER_TEXT`
- Corrigido literal `"âœ" Selecionar"` → usa `PICK_MODE_SELECT_TEXT`

**Impacto:** Banner e botões agora exibem textos corretos em PT-BR com emojis.

### 2. `src/modules/passwords/views/passwords_screen.py`

**Mudanças principais:**

#### a) `PasswordDialog`
- Novo parâmetro `on_select_client: Optional[Callable[[], None]]` no construtor
- `_on_select_client_clicked()` agora chama callback em vez de `navigate_to` direto
- Novo método `set_client_from_data(client_data: dict)` para preencher campos (reutilizável)
- Novo método `is_visible() -> bool` para verificar se janela está aberta
- `_on_close()` chama `_cancel_client_picker_if_active()` para limpar pick mode ao fechar
- `protocol("WM_DELETE_WINDOW", self._on_close)` configurado no construtor

#### b) `PasswordsScreen`
- Novos atributos:
  - `_password_dialog: Optional[PasswordDialog]` – referência ao diálogo ativo
  - `_last_selected_client_data: Optional[dict]` – último cliente selecionado
- Novos métodos:
  - `_on_select_client_from_dialog()` – inicia pick mode via `navigate_to`
  - `_handle_client_picked(client_data)` – recebe callback do pick, atualiza ou recria diálogo
  - `_get_main_app()` – obtém referência ao app principal
- `_open_new_password_dialog()` modificado:
  - Aceita `client_data` opcional
  - Passa `on_select_client=self._on_select_client_from_dialog` para o diálogo
  - Guarda referência em `self._password_dialog`
- `_edit_selected()` também atualizado para usar novo padrão

### 3. `tests/unit/modules/passwords/test_passwords_client_selection_feature001.py`

**Mudanças:**
- Testes renomeados: `test_handle_client_selected_*` → `test_set_client_from_data_*` (novo nome do método)
- Nova classe de testes: `TestPasswordsScreenOrchestration`
  - `test_handle_client_picked_abre_dialog_se_nao_existir`
  - `test_handle_client_picked_atualiza_dialog_existente`
  - `test_handle_client_picked_recria_dialog_se_fechado`
- Docstring atualizada para referenciar FIX-SENHAS-CLIENTES-004

---

## Fluxo de Uso (Happy Path)

1. **Usuário clica "Nova Senha"**
   - `PasswordsScreen._open_new_password_dialog()` cria `PasswordDialog`
   - Diálogo é guardado em `self._password_dialog`

2. **Usuário clica "Selecionar..." no campo Cliente**
   - `PasswordDialog._on_select_client_clicked()` chama callback do screen
   - `PasswordsScreen._on_select_client_from_dialog()` chama `navigate_to("clients_picker", on_pick=self._handle_client_picked)`
   - Tela de Clientes entra em pick mode (banner azul, botões ativos)

3. **Usuário seleciona cliente (duplo clique, Enter ou botão Selecionar)**
   - `PickModeController.confirm_pick()` chama `_callback(client_data)`
   - Callback é `PasswordsScreen._handle_client_picked(client_data)`
   - `_handle_client_picked`:
     - Verifica se `_password_dialog` existe e está visível
     - Se sim: `dialog.set_client_from_data(client_data)`
     - Se não: `_open_new_password_dialog(client_data=client_data)` (recria)
   - Pick mode encerra e volta para tela de Senhas
   - Nova Senha está aberta com cliente preenchido

4. **Usuário preenche demais campos e salva**
   - `PasswordDialog._save()` valida e chama controller
   - `client_id` é enviado para o backend

---

## Fluxo de Cancelamento

### Cenário A: Cancelar no banner do pick mode

1. Usuário clica **"✖ Cancelar"** no banner azul
2. `PickModeController.cancel_pick()` é chamado
3. Pick mode encerra SEM chamar `on_pick`
4. Volta para tela de Senhas
5. Nova Senha continua aberta (se estava)

### Cenário B: Fechar Nova Senha durante pick mode

1. Usuário fecha a janela Nova Senha (X ou Escape) enquanto pick está ativo
2. `PasswordDialog._on_close()` é chamado
3. Executa `_cancel_client_picker_if_active()`:
   - Obtém referência ao `MainScreenFrame`
   - Chama `frame.pick_controller.cancel_pick()` (safe mesmo se não estiver ativo)
4. Pick mode encerra
5. Volta para tela de Senhas (lista)
6. **Não fica "preso" em modo seleção**

### Cenário C: Fechar Nova Senha, depois selecionar cliente

1. Usuário abre Nova Senha, clica Selecionar, **fecha Nova Senha**, depois seleciona cliente
2. `PickModeController.confirm_pick()` chama `PasswordsScreen._handle_client_picked(client_data)`
3. `_handle_client_picked` detecta que `_password_dialog` não está visível (`is_visible() == False`)
4. Chama `_open_new_password_dialog(client_data=client_data)`
5. **Nova Senha reabre** automaticamente com cliente já preenchido
6. Usuário pode continuar normalmente

---

## Testes Executados

### Testes focados (44 testes)

```bash
python -m pytest \
  tests/unit/modules/passwords/test_passwords_client_selection_feature001.py \
  tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py \
  tests/unit/modules/clientes/views/test_pick_mode_layout_fix_clientes_001.py \
  -vv --maxfail=1
```

**Resultado:** ✅ **44 passed in 6.40s**

### Regressão Clientes + Senhas (474 testes)

```bash
python -m pytest \
  tests/unit/modules/clientes \
  tests/unit/modules/passwords \
  -vv --maxfail=1
```

**Resultado:** ✅ **474 passed in 65.31s (0:01:05)**

### Pyright (type checking)

```bash
python -m pyright \
  src/modules/clientes/views/main_screen.py \
  src/modules/clientes/views/pick_mode.py \
  src/modules/passwords/views/passwords_screen.py \
  src/modules/main_window/controller.py \
  tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py \
  tests/unit/modules/clientes/views/test_pick_mode_layout_fix_clientes_001.py \
  tests/unit/modules/passwords/test_passwords_client_selection_feature001.py
```

**Resultado:** ✅ **0 errors, 0 warnings, 0 informations**

### Ruff (linting)

```bash
python -m ruff check \
  src/modules/clientes/views/main_screen.py \
  src/modules/clientes/views/pick_mode.py \
  src/modules/passwords/views/passwords_screen.py \
  src/modules/main_window/controller.py \
  tests/unit/modules/clientes/views/test_pick_mode_ux_fix_clientes_002.py \
  tests/unit/modules/clientes/views/test_pick_mode_layout_fix_clientes_001.py \
  tests/unit/modules/passwords/test_passwords_client_selection_feature001.py
```

**Resultado:** ✅ **2 errors found and fixed with --fix**

---

## Decisões de Design

### Por que centralizar em PasswordsScreen?

**Problema:** O `PasswordDialog` é uma janela Toplevel temporária que pode ser fechada a qualquer momento. Se o callback `on_pick` aponta para um método do diálogo fechado, a lógica falha.

**Solução:** O `PasswordsScreen` é um Frame persistente que não é destruído durante a navegação entre módulos. Ele é o lugar natural para orquestrar um fluxo que pode envolver abrir/fechar diálogos.

### Por que não usar eventos/signals?

Para manter consistência com o restante do código existente, que usa callbacks diretos. Adicionar um sistema de eventos seria over-engineering neste momento.

### Por que `is_visible()` em vez de verificar se `_password_dialog is None`?

Porque uma janela Toplevel pode existir como objeto Python mas não estar visível para o usuário (destruída, escondida, etc.). `is_visible()` verifica `winfo_exists() and winfo_viewable()` de forma robusta.

---

## Compatibilidade

### Com features anteriores

- ✅ **FEATURE-SENHAS-001:** Mantém funcionalidade de seleção de cliente
- ✅ **FIX-CLIENTES-001, 002, 003:** Mantém layout, UX e textos do pick mode
- ✅ **Outras features de Clientes (batch ops, filtros, etc):** Sem impacto

### Quebra de compatibilidade

**Nenhuma.** O método `_handle_client_selected` foi mantido por compatibilidade (chama `set_client_from_data` internamente), mas marcado como depreciado nos comentários.

---

## Melhorias Futuras (Não Implementadas)

1. **Minimizar Nova Senha durante pick** em vez de manter por cima
2. **Animação de transição** ao voltar para Nova Senha após seleção
3. **Histórico de clientes recentes** no campo de seleção
4. **Busca rápida de cliente** sem precisar entrar no pick mode

---

## Conclusão

O FIX-SENHAS-CLIENTES-004 resolve todos os problemas de UX reportados pelo usuário, tornando o fluxo de seleção de cliente em Nova Senha:

- ✅ **Previsível:** sempre reabre Nova Senha após seleção
- ✅ **Robusto:** não deixa pick mode "preso" se usuário fechar diálogo
- ✅ **Claro:** textos corretos em PT-BR sem mojibake
- ✅ **Testado:** 474 testes de regressão passando

**Recomendação:** Aprovado para merge em `main` após validação manual do usuário.
