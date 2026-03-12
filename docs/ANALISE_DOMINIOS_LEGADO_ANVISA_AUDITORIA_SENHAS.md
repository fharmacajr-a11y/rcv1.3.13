# Análise Técnica — Domínios Legado: Anvisa, Auditoria, Senhas

**Data**: 2025-07  
**Branch**: `chore/cleanup-artifacts`  
**Baseline**: 928/928 testes passando  
**Objetivo**: mapeamento puro — sem implementação

---

## 1. Resumo Executivo

| Domínio | Status da UI | Status do DB | Dificuldade | Risco |
|---------|—————|————|————|-------|
| **Anvisa** | Morta (botão disabled, branch dead) | N/A | ★☆☆ Baixo | Um fragmento vivo no Sites screen e um campo em `MANDATORY_SUBPASTAS` |
| **Senhas** | Morta (stub → placeholder, não registrado) | **Vivo** (1 caller externo) | ★★☆ Médio | `delete_passwords_by_client` chamado em `lixeira_service` |
| **Auditoria** | Morta (go_to_pending sempre cai em clientes) | N/A (puro log Python) | ★★☆ Médio | `log_client_action` é chamado em `clientes_service` — é inofensivo remover, mas requer edição do chamador |

**Ordem recomendada de remoção**: Anvisa (sobras de UI + constantes) → Senhas (UI + DB em separado) → Auditoria (ajuste de chamadores).

---

## 2. Mapa por Domínio

### 2.1 Anvisa

O módulo de negócio já foi removido anteriormente. O que resta é:

#### 2.1.1 Fragmentos mortos — UI Hub

| Arquivo | Símbolo / Linha | Evidência |
|---------|----------------|-----------|
| `src/modules/hub/views/hub_quick_actions_view.py:136` | `btn_anvisa = mk_btn(inner_regulatorio, "Anvisa", None)` | Callback explicitamente `None`; comentário "módulo removido" |
| `src/modules/hub/helpers/modules.py` | `build_module_buttons(has_anvisa=False, …)` | Sempre cria `ModuleButton("Anvisa", enabled=False)` |
| `src/modules/hub/dashboard/models.py` | `DashboardSnapshot.anvisa_only: bool = False` | Campo existe; nunca recebe `True` em produção |
| `src/modules/hub/dashboard/service.py:493,582` | `snapshot.anvisa_only = False` | Dois pontos de atribuição explícita para `False` |
| `src/modules/hub/views/dashboard_center.py:135-137` | `if snapshot.anvisa_only: tasks_title_text = "…ANVISA…"` | Branch morto (condição nunca verdadeira) |
| `src/modules/hub/recent_activity_store.py:600` | `format_anvisa_event()` | Docstring "legado — mantido para compatibilidade"; **zero callers** no codebase |

#### 2.1.2 Fragmentos mortos — constantes

| Arquivo | Símbolo | Callers em src/ |
|---------|---------|----------------|
| `src/modules/hub/views/hub_screen_view_constants.py:27` | `SECTION_GESTAO_LABEL = "Gestão / Auditoria"` | 0 — não importado em lugar nenhum |
| `src/modules/hub/constants.py:20` | `HUB_BTN_STYLE_AUDITORIA = "info"` | 0 — definido, nunca referenciado |

#### 2.1.3 Vivo — Sites screen

| Arquivo | Símbolo | Status |
|---------|---------|--------|
| `src/modules/sites/views/sites_screen.py:56` | `CATEGORY_ANVISA` (4 URLs gov.br) | **LIVE** — renderizado no painel Sites |
| `src/modules/sites/views/sites_screen.py:114` | `CATEGORY_ANVISA` em `ALL_CATEGORIES` | **LIVE** |
| `self.anvisa_buttons: list` | instância da classe | **LIVE** |

> ⚠️ A aba Sites é funcional e os links da Anvisa são usados pelos usuários. Esta seção **não deve ser removida**.

#### 2.1.4 Vivo — `MANDATORY_SUBPASTAS`

| Arquivo | Símbolo | Status |
|---------|---------|--------|
| `src/utils/subpastas_config.py:6` | `MANDATORY_SUBPASTAS = ("SIFAP", "ANVISA", "FARMACIA_POPULAR", "AUDITORIA")` | **LIVE** — retornado por `get_mandatory_subpastas()` |
| `src/utils/subfolders.py:16` | `get_mandatory_subpastas` importado | **LIVE** — chamado por `lixeira_service._ensure_mandatory_subfolders()` |

> ⚠️ A tupla e a função `get_mandatory_subpastas` são **live** (criam subpastas Supabase ao restaurar clientes). A string `"ANVISA"` dentro da tupla é um nome de pasta no storage, não um módulo — **não remover**.

---

### 2.2 Auditoria

Não existe módulo de auditoria real. `src/core/logs/audit.py` é um arquivo de stubs puro.

#### 2.2.1 O módulo `audit.py`

```
src/core/logs/audit.py
```

| Função | Implementação real | Observação |
|--------|--------------------|------------|
| `ensure_schema()` | `return None` (no-op) | Nunca persistiu DDL |
| `log_client_action()` | `_audit_logger.info(…)` | Apenas Python logging; sem banco |
| `last_action_of_user()` | `return None` | Sempre retorna None |
| `last_client_activity_many()` | `return {}` | Sempre retorna dict vazio |

#### 2.2.2 Callers de `log_client_action`

| Arquivo | Linha | Efeito real se removido |
|---------|-------|------------------------|
| `src/core/services/clientes_service.py:288` | `log_client_action(org_id, user_id, cid, action)` | Apenas perde uma linha de log Python; sem side-effect no banco |

#### 2.2.3 Callers de `last_action_of_user`

| Arquivo | Uso | Callers do próprio arquivo |
|---------|-----|---------------------------|
| `src/ui/users/users.py` | `UserManagerDialog` chama `last_action_of_user` | **Zero** — `UserManagerDialog` não tem caller em todo `src/` |

> `UserManagerDialog` é exportado via `src/ui/users/__init__.py` mas **jamais instanciado** pela aplicação.

#### 2.2.4 Navegação `go_to_pending`

| Arquivo | Linha | O que acontece |
|---------|-------|----------------|
| `src/modules/hub/views/hub_navigation.py:65` | `callback = getattr(self._hub, "open_auditoria", None)` | Sempre `None` (screen_registry nunca passa `open_auditoria`) |
| `src/modules/hub/services/hub_screen_builder.py:74,146` | `open_auditoria` param aceito pelo builder | Recebe `None` de `screen_registry.py` |
| `src/modules/main_window/controllers/screen_registry.py` | Registro do Hub | Não passa `open_auditoria` → fallback para `open_clientes` |

#### 2.2.5 Constantes de secção (label vivo com nome legado)

| Arquivo | Símbolo | Status |
|---------|---------|--------|
| `src/modules/hub/views/modules_panel.py:131` | `"gestao": "Gestão / Auditoria"` | **LIVE** — string hardcoded na UI, mas o label é uma string arbitrária; pode ser renomeado para "Gestão" sem risco |
| `src/modules/hub/viewmodels/quick_actions_vm.py:113` | `category="gestao"` com item `fluxo_caixa` | **LIVE** — só Fluxo de Caixa usa a categoria |

---

### 2.3 Senhas

#### 2.3.1 A UI (100% stubs)

| Arquivo | Estado |
|---------|--------|
| `src/modules/passwords/__init__.py` | `PasswordsFrame = SenhasPlaceholder` |
| `src/modules/passwords/views/__init__.py` | vazio |
| `src/modules/passwords/views/passwords_screen.py` | `PasswordsScreen = SenhasPlaceholder` |
| `src/modules/passwords/utils.py` | apenas re-exporta `format_cnpj` |
| `src/ui/placeholders.py` → `SenhasPlaceholder` | CTkFrame com texto "SENHAS - Em breve" |

#### 2.3.2 Roteamento — completamente desconectado

| Arquivo | Evidência |
|---------|-----------|
| `src/modules/main_window/controller.py` | `_show_passwords()` definido (linhas 197-242), mas **ausente** do dict `navigate_to` (linhas 308-316) |
| `src/modules/main_window/controllers/screen_registry.py` | Registra `hub`, `main`, `cashflow`, `sites`, `placeholder` — **não registra "passwords"** |

> A tela de senhas é inacessível; nenhum botão ou navegação a invoca.

#### 2.3.3 Camada DB — parcialmente viva

| Símbolo | Arquivo | Callers em src/ |
|---------|---------|----------------|
| `list_passwords` | `src/db/supabase_repo.py` | 0 (somente em `__all__`) |
| `add_password` | `src/db/supabase_repo.py` | 0 |
| `update_password` | `src/db/supabase_repo.py` | 0 |
| `delete_password` | `src/db/supabase_repo.py` | 0 |
| `decrypt_for_view` | `src/db/supabase_repo.py` | 0 |
| **`delete_passwords_by_client`** | `src/db/supabase_repo.py` | **1 — `lixeira_service.py:200`** |

```python
# src/core/services/lixeira_service.py:17
from src.db.supabase_repo import delete_passwords_by_client

# src/core/services/lixeira_service.py:200
deleted_count = delete_passwords_by_client(org_id, str(cid))
```

> Chamado na exclusão permanente de clientes. Se removido sem adaptar `lixeira_service`, senhas do cliente ficam órfãs no banco.

#### 2.3.4 Dependências de `crypto.py`

| Arquivo | Funções | Únicos callers |
|---------|---------|---------------|
| `src/security/crypto.py` | `encrypt_text`, `decrypt_text` | **Apenas** `supabase_repo.py` (funções de senha) |

> Se todas as funções de senha do `supabase_repo` forem removidas, `crypto.py` fica sem callers e pode ser removido também — **mas somente depois**.

#### 2.3.5 TypedDict

| Arquivo | Símbolo | Dependência |
|---------|---------|-------------|
| `src/db/domain_types.py` | `PasswordRow(TypedDict)` | Usado apenas por `supabase_repo.py` funções de senha |

---

## 3. Matriz de Remoção

| # | Domínio | Arquivo | Símbolo | Classificação | Evidência resumida |
|---|---------|---------|---------|---------------|--------------------|
| 1 | Anvisa | `hub_quick_actions_view.py:136` | `btn_anvisa` | REMOVER | callback=None, comentário explícito |
| 2 | Anvisa | `hub/helpers/modules.py` | param `has_anvisa` | REMOVER | sempre False |
| 3 | Anvisa | `hub/dashboard/models.py` | `anvisa_only: bool = False` | REMOVER | nunca True |
| 4 | Anvisa | `hub/dashboard/service.py:493,582` | `snapshot.anvisa_only = False` | REMOVER | junto com o campo |
| 5 | Anvisa | `hub/views/dashboard_center.py:135-137` | `if snapshot.anvisa_only:` | REMOVER | branch morto |
| 6 | Anvisa | `hub/recent_activity_store.py:600` | `format_anvisa_event()` | REMOVER | zero callers |
| 7 | Anvisa | `hub_screen_view_constants.py:27` | `SECTION_GESTAO_LABEL` | REMOVER | importado em zero lugares |
| 8 | Anvisa | `hub/constants.py:20` | `HUB_BTN_STYLE_AUDITORIA` | REMOVER | zero callers |
| 9 | Anvisa | `sites_screen.py:56` | `CATEGORY_ANVISA` + botões | **PRESERVAR** | UI viva e útil |
| 10 | Anvisa | `subpastas_config.py:6` | `MANDATORY_SUBPASTAS` tupla | **PRESERVAR** | live via `lixeira_service` |
| 11 | Senhas | `src/modules/passwords/` (pasta inteira) | módulo stub | REMOVER | 100% stubs, inacessível |
| 12 | Senhas | `controller.py:197-242` | `_show_passwords()` | REMOVER | não está em `navigate_to` |
| 13 | Senhas | `supabase_repo.py` | `list_passwords`, `add_password`, `update_password`, `delete_password`, `decrypt_for_view` | REMOVER (5 funções) | zero callers |
| 14 | Senhas | `supabase_repo.py` | `delete_passwords_by_client` | REMOVER DEPOIS de adaptar `lixeira_service` | 1 caller real |
| 15 | Senhas | `domain_types.py` | `PasswordRow` | REMOVER DEPOIS dos itens 13-14 | só usada por supabase_repo senhas |
| 16 | Senhas | `src/security/crypto.py` | módulo inteiro | REMOVER DEPOIS dos itens 13-14-15 | sem callers restantes |
| 17 | Senhas | `placeholders.py` | `SenhasPlaceholder` | REMOVER | só usada pelo módulo senha |
| 18 | Auditoria | `src/core/logs/audit.py` | módulo inteiro | REMOVER (stubs) | todas funções são no-ops |
| 19 | Auditoria | `clientes_service.py:288` | `log_client_action(…)` chamada | REMOVER a chamada | caller único; sem banco |
| 20 | Auditoria | `src/ui/users/users.py` | `UserManagerDialog` / `last_action_of_user` | REMOVER (ou manter o dialog sem a chamada) | dialog sem caller na app |
| 21 | Auditoria | `hub_screen_builder.py:74,146` | param `open_auditoria` | REMOVER | nunca passado |
| 22 | Auditoria | `hub_navigation.py:65` | `getattr(…, "open_auditoria", None)` | REMOVER (simplificar `go_to_pending`) | sempre None |
| 23 | Auditoria | `modules_panel.py:131` | label "Gestão / Auditoria" | MANTER ou renomear | label UI live, só renomear |

---

## 4. Dependências Compartilhadas

```
lixeira_service.py
  ├── get_mandatory_subpastas()  ← MANTER (Anvisa/Auditoria são nomes de pasta cloud)
  └── delete_passwords_by_client()  ← ADAPTAR antes de remover senhas DB
```

```
supabase_repo.py (password functions)
  └── encrypt_text / decrypt_text  ← src/security/crypto.py
        └── só callers = funções de senha → remover crypto.py POR ÚLTIMO
```

```
domain_types.py → PasswordRow
  └── só usada por supabase_repo password fns → remover DEPOIS do supabase_repo cleanup
```

```
UserManagerDialog (users.py)
  └── last_action_of_user ← audit.py
        └── zero callers no app → pode remover audit.py e cleanup users.py juntos
```

---

## 5. Riscos e Armadilhas

| Risco | Probabilidade | Mitigação |
|-------|--------------|----------|
| `delete_passwords_by_client` removida sem adaptar `lixeira_service` → exceção em runtime ao deletar cliente permanentemente | Alta se esquecida | Sempre adaptar `lixeira_service` na mesma PR |
| `MANDATORY_SUBPASTAS` tocada para remover "ANVISA"/"AUDITORIA" → subpastas deixam de ser criadas no Supabase | Médio | **Não tocar** — os strings são nomes de pasta cloud, não referências ao módulo |
| `SenhasPlaceholder` removida → `ComingSoonScreen` impactada | Baixo | São classes independentes em `placeholders.py`; verificar se `ComingSoonScreen` tem outros usos |
| `SECTION_GESTAO_LABEL` removida enquanto `modules_panel.py` usa a string hardcoded | Zero | `modules_panel.py` já usa a string hardcoded, não importa a constante |
| Testes `test_clientes_audit_trail.py` ou `test_create_user_password_policy.py` removidos por engano | Médio | **NÃO remover** — não testam os módulos legado; testam `clientes_service` (audit trail de DB triggers) e `auth.py` (política de senha de login) |

---

## 6. Inventário de Testes — O que NÃO Tocar

| Arquivo de teste | O que testa | Relação com legado |
|-----------------|------------|-------------------|
| `tests/test_clientes_audit_trail.py` | Colunas `created_by`/`updated_by` preenchidas por triggers de DB em `clientes_service` | **Nenhuma** — "audit trail" aqui é trigger Supabase, não `audit.py` |
| `tests/test_create_user_password_policy.py` | `create_user()` em `core/auth/auth.py` — força senha forte | **Nenhuma** — "password" aqui é senha de login do app, não o módulo de senhas de clientes |

---

## 7. Ordem Recomendada das Próximas Fases

### Fase A — Anvisa (sobras de UI)
**Escopo**: remover os 8 itens mortos (itens 1-8 da matriz).  
**Não tocar**: `CATEGORY_ANVISA` no Sites screen, `MANDATORY_SUBPASTAS`.  
**Risco**: mínimo — todos os itens são UI morta ou constantes sem caller.  
**Testes afetados**: nenhum previsto.

Símbolos a remover:
- `hub_quick_actions_view.py` → `btn_anvisa` (linha 136)
- `hub/helpers/modules.py` → param `has_anvisa`
- `dashboard/models.py` → campo `anvisa_only`
- `dashboard/service.py:493,582` → atribuição `snapshot.anvisa_only = False`
- `dashboard_center.py:135-137` → branch `if snapshot.anvisa_only:`
- `recent_activity_store.py:600` → função `format_anvisa_event()`
- `hub_screen_view_constants.py:27` → constante `SECTION_GESTAO_LABEL`
- `hub/constants.py:20` → constante `HUB_BTN_STYLE_AUDITORIA`

---

### Fase B — Senhas UI (stub + controller)
**Escopo**: remover módulo passwords, `_show_passwords` em `controller.py`.  
**Não tocar ainda**: camada DB (`supabase_repo` password fns, `crypto.py`).  
**Risco**: mínimo — tela inacessível.  
**Testes afetados**: nenhum previsto.

Passos:
1. Deletar `src/modules/passwords/` (pasta inteira)
2. Remover `_show_passwords()` de `controller.py`
3. Remover `SenhasPlaceholder` de `placeholders.py` (verificar `ComingSoonScreen` primeiro)

---

### Fase C — Senhas DB
**Escopo**: remover funções de senha do `supabase_repo`, adaptar `lixeira_service`, remover `crypto.py` e `PasswordRow`.  
**Dependência**: Fase B concluída.  
**Risco**: médio — `lixeira_service` precisa ser adaptado; decisão de negócio: ao deletar cliente permanentemente, senhas ficam órfãs no banco **ou** é necessário migração de dados antes.

Passos:
1. Adaptar `lixeira_service.py`: remover chamada + import de `delete_passwords_by_client` (aceitar que senhas órfãs no banco serão tratadas por migration)
2. Remover 5 funções dead: `list_passwords`, `add_password`, `update_password`, `delete_password`, `decrypt_for_view` de `supabase_repo.py`
3. Remover `delete_passwords_by_client` de `supabase_repo.py`
4. Remover `PasswordRow` de `domain_types.py`
5. Remover `src/security/crypto.py`

> **Pré-condição de negócio**: confirmar se há dados de senha no banco que precisam ser migrados antes da remoção da função de deleção.

---

### Fase D — Auditoria
**Escopo**: remover `audit.py`, limpar chamadores, simplificar `hub_navigation`, remover `UserManagerDialog` se não tiver outro uso futuro.  
**Risco**: baixo (stubs puros) — apenas requer remover 1 chamada em `clientes_service`.

Passos:
1. Remover import e chamada `log_client_action` em `clientes_service.py:288`
2. Remover `src/core/logs/audit.py`
3. Remover param `open_auditoria` de `hub_screen_builder.py`
4. Simplificar `go_to_pending()` em `hub_navigation.py` (remover `getattr(…, "open_auditoria", None)`)
5. Avaliar `UserManagerDialog` em `users.py` (zero callers → pode deletar ou manter sem chamar `last_action_of_user`)
6. (Opcional) renomear label "Gestão / Auditoria" → "Gestão" em `modules_panel.py`

---

## 8. Resumo de Ficheiros por Ação Final

### Deletar inteiramente
- `src/modules/passwords/` (pasta)
- `src/core/logs/audit.py`
- `src/security/crypto.py` (Fase C)

### Editar — remoção de símbolos
- `src/modules/hub/views/hub_quick_actions_view.py`
- `src/modules/hub/helpers/modules.py`
- `src/modules/hub/dashboard/models.py`
- `src/modules/hub/dashboard/service.py`
- `src/modules/hub/views/dashboard_center.py`
- `src/modules/hub/recent_activity_store.py`
- `src/modules/hub/views/hub_screen_view_constants.py`
- `src/modules/hub/constants.py`
- `src/modules/main_window/controller.py`
- `src/modules/hub/services/hub_screen_builder.py`
- `src/modules/hub/views/hub_navigation.py`
- `src/core/services/clientes_service.py`
- `src/db/supabase_repo.py`
- `src/db/domain_types.py`
- `src/ui/users/users.py` (se `UserManagerDialog` for removido)
- `src/ui/placeholders.py` (remover `SenhasPlaceholder`)

### Preservar sem alteração
- `src/modules/sites/views/sites_screen.py` (CATEGORY_ANVISA)
- `src/utils/subpastas_config.py` (MANDATORY_SUBPASTAS)
- `src/utils/subfolders.py`
- `tests/test_clientes_audit_trail.py`
- `tests/test_create_user_password_policy.py`
- `src/modules/hub/views/modules_panel.py` (apenas label, renomear se quiser)
