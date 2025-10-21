# PR3 - Split de infra/supabase_client

## Arquivos criados/alterados
- infra/supabase_client.py (facade)
- infra/supabase/http_client.py
- infra/supabase/db_client.py
- infra/supabase/auth_client.py
- infra/supabase/storage_client.py
- infra/supabase/types.py

## Mapa de símbolos movidos
- `HTTPX_CLIENT`, `HTTPX_TIMEOUT` → infra/supabase/http_client.py
- `get_supabase`, `supabase`, `_start_health_checker`, `_health_check_once`, `is_supabase_online`, `is_really_online`, `get_supabase_state`, `get_cloud_status_for_ui`, `exec_postgrest` → infra/supabase/db_client.py
- `bind_postgrest_auth_if_any` → infra/supabase/auth_client.py
- `DownloadCancelledError`, `_sess`, `_pick_name_from_cd`, `_downloads_dir`, `baixar_pasta_zip`, `EDGE_FUNCTION_ZIPPER_URL` → infra/supabase/storage_client.py
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_BUCKET`, variáveis RC_HEALTHCHECK_* → infra/supabase/types.py

## Reexports no facade `infra/supabase_client.py`
- `supabase`
- `get_supabase`
- `baixar_pasta_zip`
- `DownloadCancelledError`
- `is_supabase_online`
- `is_really_online`
- `get_supabase_state`
- `get_cloud_status_for_ui`
- `bind_postgrest_auth_if_any`
- `exec_postgrest`
- `HTTPX_CLIENT`
- `HTTPX_TIMEOUT`

## Blocos não movidos
- `_project_root` foi removido (estava sem uso desde antes e não fazia parte da API pública).

## Declaração
**API pública preservada**
