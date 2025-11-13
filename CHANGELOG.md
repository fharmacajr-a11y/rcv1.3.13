# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Auditoria**: Suporte a arquivos `.rar` (além de `.zip`)
  - Preserva estrutura de subpastas no Storage
  - Requer `rarfile` + UnRAR/unar/bsdtar no PATH
  - Mensagem de erro amigável quando ferramenta de extração não está disponível

### Changed
- **Auditoria**: Mensagem de sucesso agora inclui Razão Social + CNPJ formatado
- **UI**: Botão renomeado para "Enviar ZIP/RAR p/ Auditoria"
- **ZIP**: Estratégia otimizada - leitura direta de membros (sem extração temporária)
- v1.1.19-dev-auditoria-ui: duplo clique Treeview; viewer centralizado; botões dinâmicos; fix tela preta subpastas

### Removed
- **Auditoria**: Removido suporte a arquivos `.7z`
  - Removida dependência `py7zr` do requirements.txt
  - Simplificado código de upload para manter apenas ZIP e RAR
  - Removido script `validate_7z_support.py`

## [1.0.99] - 2025-11-11

### Added
- **Auditoria**: Suporte completo a arquivos `.7z` (além de `.zip`)
  - Preserva estrutura de subpastas no Storage
  - Usa `py7zr.SevenZipFile.extractall()` (API oficial)
  - Extração temporária com cleanup automático
  - Mensagem amigável quando py7zr não está instalado
- **Dependencies**: `py7zr>=0.21.0` com dependências transitivas
- **Docs**: `INSTALACAO.md` com instruções completas de setup
- **Docs**: `.docs/RESUMO_TECNICO_7Z.md` com detalhes técnicos
- **Scripts**: `scripts/validate_7z_support.py` para validação automatizada

### Fixed
- **Pylance**: Import `py7zr` com `# type: ignore[import]` elimina warning
- **Uploads**: Correção de `upsert` para usar string `"true"` (não booleano)

### Changed
- **UI**: Botão renomeado para "Enviar ZIP/7z p/ Auditoria"
- **Import**: `py7zr` com type ignore para suprimir warnings antes da instalação

## [1.1.0] - 2025-11-10

### Added
- **Security**: Supabase timeout variants (LIGHT/HEAVY) for better failure detection
  - `HTTPX_TIMEOUT_LIGHT` (30s) for health checks, auth, RPC calls
  - `HTTPX_TIMEOUT_HEAVY` (60s) for file uploads/downloads
  - Backward-compatible alias `HTTPX_TIMEOUT` → `HTTPX_TIMEOUT_LIGHT`
- **Concurrency**: Optional file locking in `prefs.py` (filelock integration)
- **Logging**: Exception logging in 4 critical utility points (validators, subpastas_config, text_utils)
- **Testing**: 5 new tests for prefs.py concurrency, 3 tests for timeout alias compatibility
- **Docs**: Comprehensive quality campaign documentation (5 reports in `docs/releases/v1.1.0/`)

### Changed
- **Tests**: Replaced hardcoded `/tmp/` paths with `tmp_path` fixture (cross-platform)
- **Dependencies**: Updated to fix 6 CVEs (see Security section)

### Security
- **CRITICAL**: Updated `pdfminer-six` from 20250506 to 20251107
  - Fixed GHSA-wf5f-4jwr-ppcp (HIGH)
  - Fixed GHSA-f83h-ghpp-7wcc (HIGH)
- **CRITICAL**: Updated `pypdf` from 6.1.0 to 6.2.0
  - Fixed GHSA-vr63-x8vc-m265 (HIGH)
  - Fixed GHSA-jfx9-29x2-rv3j (HIGH)
- **HIGH**: Updated `starlette` from 0.38.6 to 0.49.3
  - Fixed GHSA-f96h-pmfr-66vw (MEDIUM)
  - Fixed GHSA-2c2j-9gv5-cj73 (HIGH)
- **Validation**: All 6 CVEs verified fixed via pip-audit

### Fixed
- Health monitoring fallback when Supabase unreachable (timeout + exception handling)
- Race condition in preferences file writes (optional filelock)
- Import compatibility for legacy code using `HTTPX_TIMEOUT`

### Technical Debt
- Identified 50 linting issues (37 E402, 10 F401, 2 E501, 1 E741) - not blocking
- Identified 10+ type annotation gaps (mypy) - not blocking
- 5 instances of weak MD5/SHA1 hashes (non-cryptographic use, acceptable)

### Documentation
- Quality Campaign: 3 sprints (10 commits, 15+ fixes)
- Medium Priority: 5 tasks (file locking, logging, test paths, timeouts)
- Security Scan: Comprehensive BUGSCAN_SUMMARY.md (pip-audit, bandit, ruff, mypy)
- Hotfix: HTTPX_TIMEOUT backward compatibility
- ADR-0001: Architectural Decision Record for timeout strategy

### Validation
- ✅ 41 tests passing, 1 skipped (test_prefs.py filelock optional)
- ✅ Zero syntax errors (compileall)
- ✅ Zero known CVEs (pip-audit)
- ✅ No breaking changes in public API

---

## [1.0.99] - 2025-10-XX

### Added
- Initial stable release
- Core features: Client management, document upload, PDF preview
- Supabase integration for backend storage
- Tkinter GUI with ttkbootstrap themes

[Unreleased]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.0.99...v1.1.0
[1.0.99]: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.99
