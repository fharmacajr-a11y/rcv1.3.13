# Devlog UP-04 - Upload unificado

## Resumo
- Criado `UploadDialog` (`src/modules/uploads/views/upload_dialog.py`) com executor injetável, progresso/cancelamento e contrato `UploadError` unificado.
- Fluxo de Clientes passou a usar o novo dialog + `validate_upload_files`/`build_items_from_files`/`upload_items_for_client` (retry/classify via `upload_retry`).
- Fluxo principal de Auditoria (upload de arquivo compactado) agora roda via `UploadDialog`, mantendo pipeline do service e rollback opcional.

## Caminho oficial
- Serviços: `src/modules/uploads/service.py` (`build_items_from_files`, `upload_items_for_client`), validação em `src/modules/uploads/file_validator.py`, retry/classificação em `src/modules/uploads/upload_retry.py`.
- UI de progresso/cancel: `src/modules/uploads/views/upload_dialog.py` (usa `ProgressDialog` como base).

## Antes/Depois (entradas → uploads)
- Clientes: botão “Enviar documentos” chamava `salvar_e_upload_docs`/pipeline `_upload.py` com `ProgressDialog` legacy → agora usa `UploadDialog` + `upload_items_for_client` direto em `client_form.py` (validação de PDFs antes de abrir o dialog).
- Auditoria: `upload_archive_to_auditoria` mostrava `UploadProgressDialog` + worker thread manual → agora executa via `UploadDialog` com cancel check, feedback textual e reaproveita `execute_archive_upload` + rollback opcional de paths enviados.
- Legacy UI: `storage_uploader.py` marcado como DEPRECATED; wrappers de progresso antigos não são mais acionados pelos fluxos principais.

## Arquivos alterados
- Produção: `src/modules/uploads/views/upload_dialog.py`, `src/modules/uploads/views/__init__.py`, `src/modules/clientes/forms/client_form.py`, `src/modules/auditoria/views/upload_flow.py`, `src/ui/dialogs/storage_uploader.py`.
- Testes: `tests/unit/modules/uploads/test_upload_dialog.py`.

## Legacy / wrappers
- `src/ui/dialogs/storage_uploader.py` explicitamente DEPRECATED (compat temporária).
- Pipeline antigo de clientes (`salvar_e_upload_docs` e `_upload.py`) permanece para compatibilidade, mas o fluxo principal não depende mais dele.
- `ProgressDialog` segue como base; `UploadProgressDialog` da auditoria deixou de ser usado no fluxo principal (substituído pelo `UploadDialog`).

## Pytest
- `python -m pytest tests/unit/modules/uploads -q`
- `python -m pytest tests/unit/modules/clientes -k "upload" -q`
- `python -m pytest tests/unit/modules/auditoria -k "upload" -q`
- `python -m pytest tests -k "upload or uploader or storage" -q`

UP-04 concluída: fluxos principais de upload (Clientes e Auditoria) migrados para o novo dialog/serviço, legacy marcado como DEPRECATED e módulo uploads pronto para futuras limpezas.
