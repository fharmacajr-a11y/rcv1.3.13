# PR7 - Split application/api.py

## Arquivos criados/alterados
- application/api/__init__.py
- application/api/api_clients.py
- application/api/api_files.py
- application/api/api_notes.py
- application/api/router.py
- (arquivo legacy application/api.py removido; pacote substitui a API pública)

## Mapa de endpoints
- switch_theme, get_current_theme, upload_folder, create_client, update_client, delete_client, search_clients ? application/api/api_clients.py
- upload_file, download_folder_zip ? application/api/api_files.py
- list_storage_files, list_trash_clients, restore_from_trash, purge_from_trash, resolve_asset ? application/api/api_notes.py

## Compatibilidade
- URLs/métodos não sofreram alterações (expostas como helpers/facade; nenhuma rota HTTP declarativa alterada).
- rom application.api import register_endpoints, upload_file, create_client, ... continua válido via reexport no pacote pplication.api.

## Reexports em application/api/__init__.py
- register_endpoints
- switch_theme, get_current_theme
- upload_file, upload_folder, download_folder_zip
- list_storage_files, list_trash_clients, restore_from_trash, purge_from_trash, resolve_asset
- create_client, update_client, delete_client, search_clients
