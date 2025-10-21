# PR6 - Split utils/file_utils

## Arquivos criados/alterados
- utils/file_utils/__init__.py
- utils/file_utils/file_utils.py
- utils/file_utils/path_utils.py
- utils/file_utils/bytes_utils.py
- utils/file_utils/zip_utils.py

## Mapa de símbolos
- ensure_dir, safe_copy, open_folder, ensure_subtree, ensure_subpastas → utils/file_utils/path_utils.py
- read_pdf_text, find_cartao_cnpj_pdf, list_and_classify_pdfs, write_marker, read_marker_id, migrate_legacy_marker, get_marker_updated_at, format_datetime → utils/file_utils/bytes_utils.py
- (sem funções zip no momento) → utils/file_utils/zip_utils.py

## Compatibilidade
- `from utils.file_utils.file_utils import ...` continua válido via reexport.

## Ponte
- `utils/file_utils/file_utils.py` agora reexporta dos novos módulos sem manter funções extras.
