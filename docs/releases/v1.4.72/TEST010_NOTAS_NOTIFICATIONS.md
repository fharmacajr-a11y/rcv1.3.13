# TEST-010 — Notifications Service

**Data**: 2025-12-21  
**Fase**: 67 (v1.4.72)

## Alvo Selecionado

**Arquivo**: `src/core/notifications_service.py`

Serviço headless de notificações (sem GUI, sem rede real, sem DB real).

## Funções/Métodos Mapeados

### Classe NotificationsService

**Métodos Públicos:**

1. `__init__(repository, org_id_provider, user_provider, logger=None)`
   - Inicializa serviço com dependências injetadas

2. `fetch_latest(limit: int = 20) -> list[dict[str, Any]]`
   - Busca notificações mais recentes
   - Retorna lista vazia se sem org_id ou erro

3. `fetch_latest_for_ui(limit: int = 20) -> list[dict[str, Any]]`
   - Busca com formatação para UI
   - Adiciona: created_at_local_str, request_id_short, actor_display_name, actor_initial
   - Converte timezone para America/Sao_Paulo

4. `fetch_unread_count() -> int`
   - Conta notificações não lidas
   - Retorna 0 se sem org_id ou erro

5. `mark_all_read() -> bool`
   - Marca todas como lidas
   - Retorna False se sem org_id ou erro

6. `publish(module, event, message, *, client_id=None, request_id=None, metadata=None) -> bool`
   - Publica nova notificação
   - Obtém actor_user_id e actor_email do user_provider
   - Retorna False se sem org_id ou erro

**Métodos Internos:**

7. `_load_initials_map() -> dict[str, str]`
   - Carrega mapa de iniciais do .env (RC_INITIALS_MAP)
   - Cache interno
   - Normaliza emails para lowercase

8. `_resolve_actor_info(actor_email: str | None) -> tuple[str, str]`
   - Resolve (display_name, initial) do autor
   - Usa RC_INITIALS_MAP se disponível
   - Fallback: prefixo do email (antes do @)
   - Fallback final: email completo

## Dependências Identificadas

- **Repository Protocol**: NotificationsRepository (mock necessário)
- **org_id_provider**: Callable[[], str | None] (mock necessário)
- **user_provider**: Callable[[], dict[str, Any] | None] (mock necessário)
- **os.getenv**: Para RC_INITIALS_MAP (monkeypatch necessário)
- **ZoneInfo**: Para timezone (America/Sao_Paulo)
- **datetime**: Para conversão de timestamps

## Estratégia de Teste

### A) _resolve_actor_info (helper interno)

**Cenários:**
- ✅ Email None → ("?", "")
- ✅ Email vazio "" → ("?", "")
- ✅ Email só espaços "   " → ("?", "")
- ✅ Email no mapa → (nome_do_mapa, inicial)
- ✅ Email não no mapa → (prefixo.capitalize(), inicial)
- ✅ Email sem @ → fallback seguro
- ✅ Email com unicode/acentos → não explode

**Mocks:**
- `os.getenv("RC_INITIALS_MAP")` via monkeypatch

### B) _load_initials_map

**Cenários:**
- ✅ RC_INITIALS_MAP não definido → {}
- ✅ RC_INITIALS_MAP vazio → {}
- ✅ RC_INITIALS_MAP válido → dict normalizado
- ✅ RC_INITIALS_MAP inválido (JSON mal formado) → {} + log debug
- ✅ Cache funciona (segunda chamada não re-parseia)

### C) fetch_latest / fetch_latest_for_ui

**Cenários:**
- ✅ org_id None → []
- ✅ org_id válido + repo OK → retorna lista
- ✅ org_id válido + repo exception → [] + log exception
- ✅ fetch_latest_for_ui: adiciona campos formatados
- ✅ fetch_latest_for_ui: converte timezone
- ✅ fetch_latest_for_ui: trata created_at inválido

**Mocks:**
- repository.list_notifications
- org_id_provider
- ZoneInfo (se necessário)

### D) fetch_unread_count

**Cenários:**
- ✅ org_id None → 0
- ✅ org_id válido + repo OK → número correto
- ✅ org_id válido + repo exception → 0 + log exception

### E) mark_all_read

**Cenários:**
- ✅ org_id None → False + log warning
- ✅ org_id válido + repo OK → True
- ✅ org_id válido + repo exception → False + log exception

### F) publish

**Cenários:**
- ✅ org_id None → False + log warning
- ✅ org_id válido + user_provider None → continua (sem actor)
- ✅ org_id válido + user_provider OK → insere com actor
- ✅ repo.insert_notification sucesso → True + log info
- ✅ repo.insert_notification falha → False + log error
- ✅ repo.insert_notification exception → False + log exception

**Mocks:**
- repository.insert_notification
- org_id_provider
- user_provider

### G) Observabilidade (caplog)

- ✅ Logs debug em falhas de parsing
- ✅ Logs warning em operações sem org_id
- ✅ Logs exception em erros de repo

## Arquivo de Teste

`tests/unit/core/test_notifications_service_fase67.py`

## Comando de Execução

```bash
pytest -q tests/unit/core/test_notifications_service_fase67.py
```
