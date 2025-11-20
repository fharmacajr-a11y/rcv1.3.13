# Auditoria Feature

## Visão da feature Auditoria
A Auditoria garante que consultores consigam iniciar revisões formais para cada cliente, acompanhar o status e manipular os documentos que ficam armazenados no bucket dos clientes. A tela é construída em Tkinter e consome apenas dados preparados pelo serviço, mantendo o comportamento original (listagem, filtros, alteração de status, upload e abertura das subpastas no browser).

## Arquivos principais
- `src/modules/auditoria/view.py`: controla widgets, eventos e feedback visual. Todo acesso a dados passa por funções do serviço.
- `src/modules/auditoria/service.py`: encapsula queries Supabase (auditorias/clientes/memberships) e operações no Storage (listar, upload, remoção, criação de pastas) e exporta utilidades como validação/extração de arquivos compactados.

## Regra de dependência interna
`view.py` → `service.py` → `infra/*` (Supabase, storage helpers, env). A camada de UI apenas lê inputs do usuário e chama o serviço; o serviço é responsável por falhar/retornar dados adequados e só ele conhece Supabase/infra.

## Principais funções expostas pelo serviço
- `fetch_clients()` / `fetch_auditorias()`: retornam registros crus ordenados para preencher o cache e a tabela na UI.
- `start_auditoria()`, `update_auditoria_status()`, `delete_auditorias()`: criam, atualizam e removem registros, já validando indisponibilidade do Supabase.
- `get_current_org_id()` e `get_storage_context()`: calculam org_id e prefixos seguros para as operações de Storage.
- `ensure_auditoria_folder()`, `list_existing_file_names()`, `upload_storage_bytes()` e `remove_storage_objects()`: concentram toda interação com o bucket de clientes (criação de .keep, paginação de nomes, upload com upsert e remoção em lote).
- `is_supported_archive()` e `extract_archive_to()`: wrappers de `infra.archive_utils` utilizados na rotina de upload para validar e extrair arquivos .zip/.rar/.7z.
