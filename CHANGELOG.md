# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.72] - 2025-12-20

### Changed
- **[BUMP-VERSION]**: Atualização de versão 1.4.52 → 1.4.72
- Notificações: timezone local, "marcar tudo como lido", coluna Por, toast winotify, ícones, alinhamento
- QA: cobertura alta em módulos de Notificações, ANVISA, db_client e network
- Upload ANVISA: sistema completo de upload de PDFs por processo com organização automática
- Melhorias diversas de UX e tratamento de erros

## [Unreleased]

### Added
- **[ANVISA-UPLOAD]**: Sistema completo de upload de PDFs por processo ANVISA
  - Footer condicional no browser de arquivos para upload ANVISA
  - Seleção de múltiplos PDFs com dialog nativo
  - Organização automática em pastas: `GERAL/anvisa/{process_slug}/`
  - Slugificação de nomes de processos (helper `process_slug.py`)
  - Componente `AnvisaFooter` com interface completa (240 linhas)
  - Upload com feedback visual e tratamento de erros
  - Callback automático para refresh após upload
  - Documentação completa em `docs/ANVISA_UPLOAD_FEATURE.md`
  - Testes unitários (6 testes) e integração (2 testes)
  - Arquivos criados:
    - `src/modules/anvisa/views/anvisa_footer.py`
    - `src/modules/anvisa/helpers/process_slug.py`
    - `tests/modules/anvisa/test_anvisa_footer.py`
    - `tests/modules/uploads/test_browser_anvisa_integration.py`
    - `docs/ANVISA_UPLOAD_FEATURE.md`
  - Arquivos modificados:
    - `src/modules/uploads/views/browser.py` (+20 linhas)
    - `src/modules/anvisa/views/anvisa_screen.py` (+152 linhas)

### Fixed
- **[FIX-ANVISA-PATH]**: Path de upload ANVISA corrigido para dentro de GERAL (18/12/2025)
  - Path alterado de `org/client/anvisa/...` para `org/client/GERAL/anvisa/...`
  - Mantém organização consistente com estrutura de pastas do cliente
  - Mensagem de sucesso atualizada para refletir caminho correto
  - Arquivos modificados:
    - `src/modules/anvisa/views/anvisa_footer.py`
    - `docs/ANVISA_UPLOAD_FEATURE.md`

- **[FIX-ANVISA-UPLOAD]**: Correção de TypeError no upload de arquivos ANVISA (18/12/2025)
  - Corrigida chamada de `upload_file()` para usar assinatura correta: `(local_path, remote_key, content_type)`
  - Removido parâmetro `bucket` desnecessário do `AnvisaFooter.__init__()`
  - Bucket agora é gerenciado automaticamente pelo adapter (padrão: 'rc-docs')
  - Testes atualizados para refletir nova assinatura
  - Arquivos modificados:
    - `src/modules/anvisa/views/anvisa_footer.py`
    - `src/modules/uploads/views/browser.py`
    - `tests/modules/anvisa/test_anvisa_footer.py`
    - `docs/ANVISA_UPLOAD_FEATURE.md`

## [1.4.52] - 2025-12-17

### Changed
- **[BUMP-VERSION]**: Atualização de versão 1.4.26 → 1.4.52
  - Atualização de `src/version.py` com nova versão
  - Atualização de metadados do executável em `version_file.txt`
  - Atualização de comentários em `requirements.txt` e `requirements-dev.txt`
  - Atualização de badge e referências no `README.md`
  - Atualização de exemplos em `docs/BUILD.md`

### Fixed
- **[FIX-DEPS]**: Correção de dependência com typo
  - Corrigido `plugggy` → `pluggy` em `requirements-dev.txt`
  - Plugin system do pytest agora com nome correto

### Security
- Varredura de segurança realizada (Bandit, ruff, deptry)
- Confirmação do módulo ANVISA funcional e integrado

## [1.4.26] - 2025-12-11

### Fixed
- **[FIX-HUB-BLANK-001]**: Correção de Dashboard e Notas ficando em branco
  - **Estado inicial de loading**: Dashboard e Notas agora mostram "Carregando..." logo após construção
  - **Tratamento de erros robusto**: Mensagens amigáveis exibidas em caso de erro ao carregar dados
  - **Estado vazio tratado**: Quando não há dados, mensagens informativas são exibidas
  - **Tratamento de autenticação**: Mensagem "Aguardando autenticação..." exibida quando org_id não disponível
  - **Prevenção de painéis em branco**: Garantia que NUNCA fiquem completamente vazios
  - Arquivos modificados:
    - `src/modules/hub/views/hub_screen.py`: Renderização inicial de loading
    - `src/modules/hub/services/hub_async_tasks_service.py`: Tratamento de erros e estados vazios

### Changed
- **[BUMP-VERSION]**: Atualização de versão 1.4.19 → 1.4.26
  - Atualização de `src/version.py` com nova versão
  - Atualização de metadados do executável em `version_file.txt`
  - Atualização de comentários em `requirements.txt` e `requirements-dev.txt`
  - Atualização de badge e changelog em `README.md`

## [1.3.61] - 2025-12-04

### Changed
- **[BUMP-VERSION]**: Bump de versão v1.3.51 → v1.3.61
  - Atualização de `src/version.py` com nova versão
  - Atualização de metadados do executável em `version_file.txt`
  - Atualização de comentários em `requirements.txt` e `requirements-dev.txt`
  - Atualização de `installer/rcgestor.iss` com nova versão
  - Atualização de documentação em `README.md` e `docs/BUILD.md`

## [1.3.51] - 2025-12-02

### Fixed
- **[FIX-HUB-CORES-002]**: Botões Clientes e Senhas com azul claro
  - **Cor azul claro**: Botões Clientes e Senhas agora usam `bootstyle="info"` (azul claro)
  - Substituído `bootstyle="primary"` (azul escuro) por `bootstyle="info"` (azul claro)
  - Demais botões mantêm suas cores originais (Auditoria verde, etc.)

- **[FIX-HUB-001]**: Reordenação de botões do Hub e cor azul padronizada
  - **Botão Senhas reordenado**: Movido para ficar imediatamente após Clientes
  - Nova ordem: Clientes → Senhas → Auditoria → Fluxo de Caixa → (demais)
  - **Cor azul padronizada**: Botões Clientes e Senhas agora usam `bootstyle="primary"` (azul)
  - Substituído `highlight=True` e `yellow=True` por estilo consistente
  - **Diálogo Sair já padronizado**: Confirmado uso de `custom_dialogs.ask_ok_cancel()`
  - Ícone RC já aplicado via `_apply_icon()` em todos os custom dialogs
  - Não requer alterações adicionais no diálogo de saída

- **[FIX-SENHAS-015]**: Filtro Serviço somente leitura e exclusão cascata de senhas
  - **Filtro Serviço readonly**: Combobox de serviço agora com `state="readonly"`
  - Não é mais possível digitar no campo, apenas selecionar da lista
  - Comportamento idêntico ao filtro Status da tela de Clientes
  - **Exclusão cascata**: Ao excluir cliente definitivamente da Lixeira, senhas são removidas automaticamente
  - Implementado em `hard_delete_clients()` de `lixeira_service.py`
  - Chama `delete_passwords_by_client(org_id, client_id)` antes de excluir o cliente do DB
  - Evita senhas órfãs no banco de dados
  - Falhas na exclusão de senhas não impedem a exclusão do cliente (erro registrado mas continua)
  - **Testes atualizados**: Todos os testes de `lixeira_service` incluem mock de `delete_passwords_by_client`
  - Total de 121 testes no módulo passwords + 24 no módulo lixeira passando
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-014]**: Padronização do formato Cliente, bloqueio de clique em cabeçalhos e reposicionamento do filtro Serviço
  - **Formato Cliente padronizado**: Campo Cliente em Nova/Editar Senha agora usa o mesmo formato do cabeçalho
  - Nova formatação: "ID 336 – A DE LIMA FARMACIA – 05.788.603/0001-13" (sem parênteses, CNPJ pontuado)
  - **Helper compartilhado**: Criado `src/modules/passwords/utils.py` com função `format_cnpj()`
  - Função movida de `client_passwords_dialog.py` para reutilização em `password_dialog.py`
  - **Bloqueio de clique em cabeçalhos**: Implementado `region in {"separator", "heading"}` nas trees
  - `PasswordsScreen`: Tree "Clientes com Senhas" não responde a cliques no cabeçalho
  - `ClientPasswordsDialog`: Tree "Senhas do Cliente" não responde a cliques no cabeçalho
  - Elimina sort indesejado e pulo de scroll ao clicar acidentalmente no header
  - **Reposicionamento de filtros**: Buscar e Serviço agora lado a lado, à esquerda
  - Filtro Serviço com `width=20` (reduzido de 30), posicionado ao lado do Buscar
  - Removida expansão de colunas (`weight=0` para todas), filtros compactos e alinhados
  - Layout mais limpo e consistente com design pretendido
  - Total de 121 testes passando
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-013]**: Ícone RC em messageboxes e eliminação de flash ao abrir diálogos de senha
  - **Messageboxes com ícone**: Modificado `apply_rc_icon()` para adicionar `iconbitmap(default=icon_path)`
  - Todos os messageboxes (sucesso, confirmação, erro) agora exibem o ícone RC automaticamente
  - Propagação de ícone funciona via parâmetro `default=` no `iconbitmap()`
  - **Eliminação de flash visual**: Adicionado `withdraw()/deiconify()` em `PasswordDialog` e `ClientPasswordsDialog`
  - `withdraw()` chamado logo após `super().__init__(parent)` para esconder janela durante setup
  - `deiconify()` chamado após `_center_on_parent()` para mostrar janela já centralizada
  - **Correção de import**: Movido `import tkinter as tk` para o topo de `app_gui.py` (antes estava dentro da função)
  - Elimina flash de janela aparecendo no canto superior esquerdo antes da centralização
  - Total de 121 testes passando
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-ÍCONES-LOCAL]**: Aplicação consistente de ícone rc.ico nas janelas do módulo Senhas
  - **Helper `apply_rc_icon()`**: Criado em `src/app_gui.py` para reaproveitar lógica da janela principal
  - Copia exatamente a mesma lógica de `main_window.py`: `iconbitmap()` com fallback para `iconphoto()`
  - Seguro de chamar múltiplas vezes, não quebra UI em caso de erro
  - **ClientPasswordsDialog**: Ícone RC aplicado na janela "Senhas – ID ..."
  - **PasswordDialog**: Ícone RC aplicado nas janelas "Nova Senha" e "Editar Senha"
  - Removido helper `_apply_dialog_icon()` obsoleto do `client_passwords_dialog.py`
  - Centralização da lógica de ícone em um único local (`src/app_gui.py`)
  - **Obs**: PasswordsScreen é `tb.Frame`, não Toplevel, logo não precisa de ícone
  - **Obs**: Messageboxes "Sucesso" usam `tkinter.messagebox` padrão (sem Toplevel customizado)
  - Total de 121 testes passando
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-012]**: Ícone da aplicação no ClientPasswordsDialog e ajuste de largura do filtro Serviço
  - **ClientPasswordsDialog**: Agora exibe o ícone da aplicação (rc.ico) na barra de título
  - Helper `_apply_dialog_icon()` criado para evitar import circular
  - Aplica ícone via `iconbitmap()` com fallback para `iconphoto()` e parent icon
  - **Tela principal Senhas**: Combobox de filtro "Serviço" com largura fixa (width=30)
  - Combobox não se expande mais até o fim da tela (sticky="w" ao invés de "ew")
  - **Configuração de grid**: Apenas coluna de Buscar (column=1) expande (weight=1)
  - Colunas de labels e Serviço não expandem (weight=0)
  - Layout visualmente mais balanceado e consistente
  - Total de 121 testes passando
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-011]**: Ajuste no cabeçalho do ClientPasswordsDialog para CNPJ único e formatado
  - **Título da janela**: Simplificado para "Senhas – ID 336 – A DE LIMA FARMACIA" (sem CNPJ)
  - **Label principal**: Formato limpo "Cliente: ID 336 – A DE LIMA FARMACIA – 05.788.603/0001-13"
  - Removida duplicação de CNPJ (antes aparecia entre parênteses e após "CNPJ:")
  - **Helper `_format_cnpj()`**: Formata CNPJ de "05788603000113" para "05.788.603/0001-13"
  - **Propriedade `display_name`**: Modificada para **não incluir** CNPJ (apenas ID + Razão Social)
  - CNPJ formatado aparece **exclusivamente** no label principal do diálogo
  - Removidos parênteses e texto "| CNPJ:" do cabeçalho
  - **Novo teste**: `test_client_passwords_summary_display_name_never_includes_cnpj()`
  - **Teste atualizado**: `test_client_passwords_summary_display_name_uses_external_id_razao_social_and_cnpj` validando ausência de CNPJ
  - Total de 121 testes passando (1 novo teste adicionado)
  - Todos os checks ruff e bandit OK

- **[FIX-SENHAS-010]**: Balanceamento harmônico de larguras das colunas na tela Senhas
  - **Larguras base ajustadas**: Distribuição mais equilibrada entre todas as colunas
  - ID: 60px, Razão Social: 230px, CNPJ: 150px, Nome: 200px, WhatsApp: 170px, Qtd. Senhas: 90px, Serviços: 200px
  - **Algoritmo de distribuição de largura extra**: Reescrito `_on_clients_tree_configure()`
  - Largura extra da tela agora é **dividida entre 3 colunas**: Razão Social, Nome e Serviços
  - Evita que apenas "Serviços" fique gigante em telas largas
  - **Distribuição proporcional**: `per_col = extra // 3` para cada coluna de compartilhamento
  - Remainder aplicado à coluna "Serviços" para evitar pixels perdidos
  - Largura mínima de 60px por segurança em todas as colunas
  - Removido `stretch=True` da coluna "Serviços" (controle total via `<Configure>`)
  - **Novo teste**: `test_clients_tree_width_distribution_is_balanced()` valida distribuição
  - Total de 120 testes passando (1 novo teste adicionado)

- **[FIX-SENHAS-009]**: Travamento de colunas do diálogo e centralização completa da tela principal
  - **ClientPasswordsDialog**: Adicionado bloqueio de redimensionamento de colunas
  - Método `_on_passwords_tree_heading_click()` impede arrastar separadores
  - Import `tkinter as tk` adicionado para suporte ao evento
  - **Tela principal Senhas**: Todas as colunas completamente centralizadas
  - Headers e dados com `anchor="center"` em todas as 7 colunas
  - Coluna `#0` garantida como oculta (`width=0, stretch=False`)
  - Eliminado qualquer recuo/espaço à esquerda causado por coluna raiz
  - Ajustadas larguras: WhatsApp (160px) e Serviços (220px) para melhor distribuição
  - Coluna "Serviços" mantém `stretch=True` para ocupar espaço restante
  - Total de 119 testes passando

- **[FIX-SENHAS-008]**: Melhorias de alinhamento e eliminação de espaço em branco
  - **Tela principal Senhas**: Coluna "Serviços" agora se ajusta dinamicamente via `<Configure>` event
  - Método `_on_clients_tree_configure()` calcula e aplica largura restante automaticamente
  - Elimina completamente o espaço em branco à direita da grade "Clientes com Senhas"
  - **ClientPasswordsDialog**: Todas as colunas (Serviço, Usuário/Login, Senha, Anotações) centralizadas
  - Headers e dados alinhados consistentemente com `anchor="center"`
  - Coluna "Anotações" com `stretch=True` para ocupar espaço restante no diálogo
  - Corrigido bug em `_on_password_saved()`: campos faltantes em `ClientPasswordsSummary`
  - Total de 119 testes passando

- **[FIX-SENHAS-007]**: Correções de UX e usabilidade na tela de Senhas
  - Adicionada propriedade `display_name` ao `ClientPasswordsSummary` para compatibilidade com `ClientPasswordsDialog`
  - Título do diálogo "Gerenciar Senhas" agora exibe formato: "Senhas – ID 336 – A DE LIMA FARMACIA (05788603000113)"
  - Travado redimensionamento de colunas na lista "Clientes com Senhas" (não é mais possível arrastar separadores)
  - Ajustado alinhamento das colunas: ID/CNPJ/WhatsApp/Qtd. Senhas centralizados, textos à esquerda
  - Coluna "Serviços" agora estica (`stretch=True`) para eliminar espaço em branco à direita
  - Adicionados 3 novos testes unitários para `display_name`
  - Total de 119 testes passando no módulo passwords

- **[HOTFIX-SENHAS-006A]**: Corrigido erro de JOIN em `list_passwords`
  - Campo `whatsapp` não existe na tabela `clients` - corrigido para usar `numero`
  - Ajustado SELECT no JOIN para: `clients!client_id(id, razao_social, cnpj, nome, numero)`
  - Mapeamento de `numero` para `whatsapp` no layer de aplicação mantém compatibilidade
  - Todos os 116 testes do módulo Senhas passando
  - Verificações ruff e bandit OK

### Changed
- Bump de versão: v1.3.28 → v1.3.51
- Alinhamento de versionamento em `src/version.py`, `version_file.txt`, `requirements.txt` e `requirements-dev.txt`

## [1.3.28] - 2025-11-30

### Added
- **[TEST-PASSWORDS-001]**: Nova suíte de testes unitários para `PasswordsController`
  - 33 testes cobrindo todas as operações do controller
  - Cobertura de `load_all_passwords`, `filter_passwords`, `decrypt_password`, `list_clients`
  - Testes de delegação para `create_password`, `update_password`, `delete_password`
  - Aumenta significativamente a cobertura do módulo Senhas

### Fixed
- **[FIX-CLIENTES-007]**: Ajustes no modo seleção (pick mode) do módulo Clientes
  - Lixeira, Conversor PDF e rodapé desativados quando em modo seleção
  - Restauração correta do estado após seleção de cliente

### Changed
- Bump de versão: v1.2.97 → v1.3.28

## [1.2.0] - 2025-11-17

### Fixed
- Corrigidos caracteres incorretos no browser de arquivos (mojibake como `â€¢`, `â–¼`, `âœ”`), normalizando títulos, cabeçalhos e ícones de status.
- Ajustado o comportamento do browser para impedir múltiplas janelas abertas para o mesmo cliente, reutilizando a janela existente quando já estiver aberta.

### Notes
- Nenhuma alteração funcional adicional além dessas correções de UI.

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

[Unreleased]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.3.61...HEAD
[1.3.61]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.3.51...v1.3.61
[1.3.51]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.3.28...v1.3.51
[1.3.28]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.2.0...v1.3.28
[1.2.0]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/v1.0.99...v1.1.0
[1.0.99]: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.99
