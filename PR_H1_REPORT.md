# PR-H1 - HTTP/1.1 + Retries PostgREST

## HTTP client ajustes
- `infra/http/retry.py`: utilitário `retry_call` com backoff exponencial e exceções de rede conhecido.
- `infra/supabase_client.py`: `_HTTPX_CLIENT` criado com `httpx.Client(http2=False, timeout=Timeout(connect=10.0, read=60.0, write=60.0, pool=None))` e passado via `ClientOptions` ao `create_client`.

## Chamadas PostgREST agora via `exec_postgrest`
- `app_core.py`: envio para lixeira usa o wrapper.
- `data/supabase_repo.py`: membership precheck, listagem/inserção/atualização/remoção e buscas reutilizam `exec_postgrest`.
- `core/db_manager/db_manager.py`: listagens, fetches e operações CRUD de clientes migradas.
- `gui/main_window.py`: cache de role e org resolve via wrapper.
- `core/services/notes_service.py`: listagens/inserções de notas com retry central.
- `core/services/clientes_service.py`: contagem de clientes (tabela `clients`).
- `core/services/profiles_service.py`: consultas de perfis e display names.
- `core/services/upload_service.py`: mapeamento org e inserts/updates de documentos/versões.
- `core/services/lixeira_service.py`: resolução de org + restauração/exclusão definitiva.
- `ui/forms/actions.py`: pipeline de upload (`memberships`, `documents`, `document_versions`) usa `exec_postgrest`.
- `ui/forms/forms.py`: listagem de documentos existentes por cliente.
- `infra/supabase_client.py`: health-check `rpc`/`table` protegidos pelo wrapper.

## Parâmetros de retry
- `retry_call`: padrão `tries=3`, `backoff=0.6`, `jitter=0.2`.
- `exec_postgrest`: chama `retry_call` com `tries=3`, `backoff=0.7`, `jitter=0.3`.
