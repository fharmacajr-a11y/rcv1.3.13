# Módulo Clientes – Visão Geral

## 1. Responsabilidade do módulo

- Manter as telas principais de gestão de clientes (lista, formulário, pickers) usadas pelo app desktop.
- Encapsular regras de negócio de cadastro (validação, duplicidade, normalização de CNPJ) e persistência no Supabase.
- Centralizar o fluxo de lixeira de clientes (soft delete, restauração e exclusão definitiva).
- Orquestrar uploads/anexos de clientes (seleção de subpastas, pipeline de salvar + envio de arquivos).
- Disponibilizar uma API estável para outros módulos acessarem clientes sem conversar direto com `src.core`.

## 2. Estrutura de pastas

- `src/modules/clientes/__init__.py` — ponto único de import/export do módulo (services, forms, views).
- `src/modules/clientes/view.py` — integração com o shell principal (ClientesFrame exposto ao router/app).
- `src/modules/clientes/views/` — telas concretas de clientes (MainScreenFrame e helpers da lista).
- `src/modules/clientes/forms/`
  - `client_form.py` — implementação completa do `form_cliente`.
  - `client_picker.py` — picker modal de clientes (escolha para outros módulos).
  - `client_subfolder_prompt.py` / `client_subfolders_dialog.py` — diálogos de subpasta.
  - `pipeline.py` — pipeline de salvar cliente + upload de anexos (validate/prepare/perform/finalize).
  - `__init__.py` — reexporta todos os entrypoints de UI.
- `src/modules/clientes/service.py` — serviços de domínio (CRUD, lixeira, uploads, wrappers de core).
- `tests/test_clientes_service.py` — testes unitários focados no service.
- `tests/test_clientes_integration.py` — testes de integração exercitando pipeline + service.

## 3. API pública do módulo

### 3.1. Services (`from src.modules.clientes import service as clientes_service`)

- `salvar_cliente_a_partir_do_form(row, valores)` — normaliza campos e delega persistência para o core, disparando `ClienteCNPJDuplicadoError` em caso de duplicidade.
- `get_cliente_by_id(cliente_id)` — wrapper fino sobre o repositório legado, usado por app/router para carregar registros.
- `count_clients()` / `salvar_cliente()` / `checar_duplicatas_info()` — reexports utilizados por pipelines/relatórios (compatibilidade com código antigo).
- `checar_duplicatas_para_form(valores, row=None)` — valida duplicidades (razão/CNPJ/nome/whatsapp) sem expor o core.
- `mover_cliente_para_lixeira(cliente_id)` — executa soft delete (marca `deleted_at`/`ultima_alteracao` no Supabase).
- `listar_clientes_na_lixeira(order_by="id", descending=True)` — lista registros deletados (mesmo formato usado pela UI).
- `restaurar_clientes_da_lixeira(ids, parent=None)` / `excluir_clientes_definitivamente(ids, parent=None)` — wrappers para restaurar ou apagar registros via service de lixeira.
- (Upload) Funções internas do pipeline chamam `storage_upload_file`, mas o entrypoint recomendado é usar o pipeline (`validate_inputs` → `prepare_payload` → `perform_uploads` → `finalize_state`), que já conversa com `clientes_service`.

### 3.2. Forms & dialogs (`from src.modules.clientes.forms import ...`)

- `form_cliente` — formulário principal (novo/editar) usado pelo app e router.
- `ClientPicker` — modal de seleção de cliente (ex.: tela de senhas).
- `SubpastaDialog` (`client_subfolder_prompt`) — prompt simples para nome de subpasta.
- `open_subpastas_dialog` (`client_subfolders_dialog`) — navegador completo de subpastas locais.
- `pipeline.validate_inputs` / `prepare_payload` / `perform_uploads` / `finalize_state` — sequência usada por `salvar_e_enviar_para_supabase`; importada diretamente por handlers ou via shim `src.ui.forms.pipeline`.

### 3.3. Views principais

- `ClientesFrame` (reexportado por `src.modules.clientes.view`) encapsula `MainScreenFrame` e é o entrypoint usado pelo router/app.
- Relaciona-se com o service/forms: botões/menus disparam `form_cliente`, pickers, e chamam services (`mover_cliente_para_lixeira`, etc.) sem tocar em `src.core`.

## 4. Dependências externas encapsuladas

- Supabase (via `infra.supabase_client`) — utilizado apenas dentro de `service.py` e `forms/pipeline.py` para updates, uploads e consultas.
- `src.core.db_manager` / `clientes_service` legados — acessados somente dentro de `service.py` para manter compatibilidade com dados já existentes.
- Storage helpers (`adapters.storage.*`) — invocados apenas dentro do pipeline de upload.
- Qualquer módulo/UI fora de `src.modules.clientes` deve depender exclusivamente dessa API pública; app_core/router foram atualizados para respeitar isso.

## 5. Estratégia de testes do módulo

- **Unitários:** `tests/test_clientes_service.py` cobre checagem de duplicidade, salvar cliente, lixeira e uploads (via monkeypatch dos helpers internos).
- **Integração:** `tests/test_clientes_integration.py` executa o pipeline completo (validate → prepare → perform → finalize) e o fluxo de lixeira (mover/listar/restaurar) usando somente a API pública.
- Para executar apenas os testes do módulo: `pytest -q tests/test_clientes_service.py tests/test_clientes_integration.py`.

## 6. Como outros módulos devem usar Clientes

- Sempre importar via `src.modules.clientes` (forms, views, services). Evitar `src.core.db_manager`, `src.core.services.clientes_service` ou supabase direto.
- Para abrir diálogos/forms, usar os entrypoints do pacote (`form_cliente`, `ClientPicker`, `SubpastaDialog`, pipeline).
- Para operações de negócio (salvar, lixeira, uploads), chamar as funções de `clientes_service`.
- Novos fluxos que precisem de dados de clientes devem solicitar wrappers adicionais em `service.py` em vez de acessar o core diretamente.

## 7. Pendências e futuras melhorias

- **Fallback local em `src/app_core.py::dir_base_cliente_from_pk` ainda importa `src.core.db_manager.get_cliente_by_id` e `path_resolver`.** Continua funcionando, mas permanece como ponto legado a ser substituído por um helper de `modules.clientes` futuramente.
- **Scripts/CLI em `src/core/services/path_resolver.py`** continuam dependendo de `src.core.db_manager`; não foram tocados nesta rodada.
- Próximas melhorias possíveis:
  - fornecer helper em `modules.clientes.service` para resolução de diretórios locais (substituir `dir_base_cliente_from_pk`);
  - avaliar extração do módulo para um serviço independente ou boundary plugin.
