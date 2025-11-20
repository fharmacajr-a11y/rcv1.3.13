## Etapa: API pública do módulo clientes (2025-11-15)

**Objetivo desta etapa**
- Consolidar `src.modules.clientes` como ponto único de import para a UI de clientes.
- Validar que não restaram dependências internas de `src.modules.clientes.view`.

**Arquivos alterados**
- docs/dev/modularizacao_clientes.md — adicionada documentação desta etapa e checklist de verificação.

**Impacto na modularização**
- Reforça que o app inteiro consulta o módulo Clientes via `src.modules.clientes`, permitindo trocar a implementação interna (views, serviços) sem tocar os consumidores.
- Facilita futuros passos (por exemplo, mover formulários e fluxos auxiliares) porque já existe um pacote com API pública bem definida.

**Próximos passos sugeridos**
- Expor views secundárias (forms específicos, diálogos) via `src.modules.clientes.views`.
- Investigar dependências diretas de `src.core` para movê-las para `modules.clientes.service`.
- Padronizar acesso a forms e actions dentro do pacote de clientes.
## Etapa: Inventário e exposição de views secundárias de clientes (2025-11-15)

**Objetivo desta etapa**
- Levantar todas as telas/diálogos ligados ao domínio de clientes.
- Garantir que as views já presentes em `src.modules.clientes.views` sejam reexportadas pelo pacote.
- Padronizar imports internos para consumir essas views via `src.modules.clientes.views`.

**Inventário de views/diálogos de clientes**
- `MainScreenFrame` — definido em `src/modules/clientes/views/main_screen.py` — instanciado via `ClientesFrame` e usado pelo router/app principal (`src/ui/main_window/app.py`, `router.py`).
- `ClientesFrame` — alias em `src/modules/clientes/view.py` que herda de `MainScreenFrame` — importado pelo app e router para montar a aba Clientes.
- `form_cliente` (função) — definido em `src/ui/forms/forms.py`, reexportado via `src/ui/forms/__init__.py` e `src/modules/forms/view.py`, usado por `app_core` para o diálogo de novo/editar cliente (ainda fora de `modules.clientes`).

**Arquivos alterados**
- src/ui/main_screen.py — import agora usa `src.modules.clientes.views` em vez do módulo concreto.
- docs/dev/modularizacao_clientes.md — adicionada documentação do inventário e próximos passos.

**Impacto na modularização**
- Consolida o pacote `src.modules.clientes.views` como ponto único para expor as telas, evitando dependências diretas de submódulos concretos.
- O inventário deixa explícito o que ainda está preso a `src/ui/forms`, preparando a migração desses diálogos para dentro do pacote de clientes.
- Padronizar imports simplifica futuras refatorações, pois consumidores já dependem apenas da API pública do pacote de views.

**Próximos passos sugeridos**
- Migrar `form_cliente` e seus fluxos auxiliares de `src/ui/forms` para um submódulo em `src/modules/clientes`.
- Criar um namespace (ex.: `src.modules.clientes.forms`) que reúna diálogos e ações específicas de clientes.
- Avaliar outras telas relacionadas (ex.: integrações com lixeira ou pickers) para movê-las ao pacote de clientes.

## Etapa: Migracao do form_cliente para src.modules.clientes.forms (2025-11-15)

**Objetivo desta etapa**
- Centralizar o formulario de clientes dentro do pacote de dominio `src.modules.clientes`.
- Manter compatibilidade com os caminhos antigos (`src/ui/forms`, `src/modules/forms`).

**Arquivos alterados**
- src/modules/clientes/forms/client_form.py - novo modulo contendo a implementacao de `form_cliente`.
- src/modules/clientes/forms/__init__.py - expoe `form_cliente` como API publica do subpacote.
- src/ui/forms/forms.py - convertido para shim que delega a `modules.clientes.forms`.
- src/modules/forms/view.py - passa a importar `form_cliente` do pacote de clientes.

**Impacto na modularizacao**
- O formulario de clientes agora pertence ao modulo de dominio, mantendo a estrategia de modular monolith por area de negocio.
- A UI externa continua importando dos mesmos caminhos (`src/ui/forms`, `src/modules/forms`), mas a implementacao real fica dentro de `modules.clientes`.
- Essa separacao permite evoluir regras e dependencias de clientes sem expor detalhes para o restante da aplicacao.

**Proximos passos sugeridos**
- Mover outros formularios ou dialogos especificos de clientes para `src/modules/clientes/forms`.
- Iniciar um modulo `modules.clientes.service` dedicado a regras de negocio consumidas por views/forms.
- Revisar integracoes auxiliares (lixeira, pickers, uploads) para aproxima-las do pacote de clientes.

## Etapa: Criacao do primeiro service de dominio em modules.clientes.service (2025-11-15)

**Objetivo desta etapa**
- Extrair as chamadas de negocio usadas pelo formulario de clientes para um modulo de servicos dedicado.
- Manter `form_cliente` focado em UI, delegando validacoes de CNPJ e persistencia para o service.

**Arquivos alterados**
- src/modules/clientes/service.py - novo modulo com funcoes de verificacao e salvamento do cliente.
- src/modules/clientes/forms/client_form.py - passa a consumir o service ao validar/salvar.
- src/modules/clientes/__init__.py - exposto o service na API publica do pacote.

**Impacto na modularizacao**
- Camadas de UI deixam de conversar diretamente com `src.core`, fortalecendo o encapsulamento do dominio Clientes.
- A logica de validacao de CNPJ e de orquestracao de salvamento agora vive junto do modulo, permitindo reuso pelas views.
- Este e o primeiro passo para migrar regras de negocio para `modules.clientes`, alinhado ao modelo de modular monolith.

**Proximos passos sugeridos**
- Mover outras operacoes de negocio (exclusao, restauracao, lixeira) para `modules.clientes.service`.
- Criar testes especificos para o service de clientes, cobrindo fluxos de duplicidade e salvamento.
- Avaliar migracao de outros formularios/integacoes para consumir o novo service.

## Etapa: Testes unitarios do service de clientes (2025-11-15)

**Objetivo desta etapa**
- Adicionar testes unitarios para validar os fluxos principais de `modules.clientes.service`.
- Garantir que mudancas internas nao quebrem o contrato usado por `form_cliente` e outras views.

**Arquivos alterados**
- tests/test_clientes_service.py - novos testes cobrindo checagem de duplicidade e salvamento.
- src/modules/clientes/service.py - sem mudancas funcionais, mas verificado para garantir compatibilidade com os testes.

**Impacto na modularizacao**
- Com os testes, conseguimos refatorar o service mantendo o boundary de dominio protegido contra regressao.
- O pacote de clientes passa a ter cobertura minima para duplicidade e para o wrapper de salvamento, reforcando o encapsulamento do core.
- Futuras extracoes de regras para o service podem seguir o mesmo padrao de testes para manter confianca.

**Proximos passos sugeridos**
- Adicionar testes de integracao leve combinando `form_cliente` com o novo service.
- Migrar outras operacoes (exclusao, restauracao, lixeira) para o service e cobrir com testes semelhantes.
- Avaliar cobertura para pickers/integrafos auxiliares relacionados ao modulo de clientes.

## Etapa: Extracao de exclusao/restauracao/lixeira para modules.clientes.service (2025-11-15)

**Objetivo desta etapa**
- Centralizar no service as funcoes de envio para lixeira, restauracao e exclusao definitiva de clientes.
- Reduzir o acoplamento das views com `src.core`/`infra` nas operacoes de lixeira.

**Arquivos alterados**
- src/modules/clientes/service.py - adiciona funcoes para mover clientes para a lixeira e wrappers para restaurar/apagar definitivamente.
- src/modules/clientes/__init__.py - reexporta as novas funcoes do service.
- src/ui/main_window/app.py - handler de exclusao passa a chamar o service diretamente.
- src/ui/lixeira/lixeira.py - a UI da lixeira de clientes delega ao service de clientes.
- tests/test_clientes_service.py - cobrimos os novos fluxos com testes unitarios.

**Impacto na modularizacao**
- As operacoes de lixeira agora vivem no dominio de clientes, ocultando detalhes de Supabase e do core legado.
- As views ficam responsaveis apenas por confirmacoes e feedback visual, enquanto o service concentra a regra de negocio.
- Esse passo prepara o terreno para mover outras regras de clientes (e.g. listagem da lixeira) para `modules.clientes`.

**Proximos passos sugeridos**
- Encaminhar a listagem da lixeira (`list_clientes_deletados`) para o service de clientes.
- Migrar outros fluxos (pickers, uploads especificos) para os submodulos de clientes e acrescentar testes.
- Avaliar testes de integracao UI + service para validar o fluxo completo de exclusao/restauracao.

## Etapa: Listagem da lixeira via modules.clientes.service (2025-11-15)

**Objetivo desta etapa**
- Centralizar a consulta de clientes na lixeira no service do dominio de clientes.
- Manter a UI responsavel apenas por apresentar resultados e ler filtros.

**Arquivos alterados**
- src/modules/clientes/service.py - adicionada a funcao `listar_clientes_na_lixeira`.
- src/modules/clientes/__init__.py - expoe a nova funcao na API publica.
- src/ui/lixeira/lixeira.py - passa a consumir o service ao carregar a lixeira.
- tests/test_clientes_service.py - inclui testes para a listagem.

**Impacto na modularizacao**
- Toda a cadeia lixeira (listar, mover, restaurar, excluir) agora passa pelo pacote de clientes antes de chegar ao core, mantendo o boundary de dominio consistente.
- A UI continua fornecendo filtros e exibindo resultados, mas nao conhece mais os detalhes de acesso a dados.
- Isso abre caminho para migrar a propria tela de lixeira para `modules.clientes` no futuro, ja que o backend ja esta encapsulado.

**Proximos passos sugeridos**
- Migrar dialogs/forms remanescentes (pickers, subpastas) para `modules.clientes.forms`.
- Encapsular uploads e outras integracoes especificas de clientes em submodulos proprios.
- Criar testes de integracao (UI + service) para validar fluxos completos de lixeira e restauracao.

## Etapa: Migracao do primeiro picker/dialogo de clientes para src.modules.clientes.forms (2025-11-15)

**Objetivo desta etapa**
- Iniciar a migracao de pickers/dialogos especificos de clientes para `src.modules.clientes.forms`.
- Manter compatibilidade com os caminhos antigos em `src.ui.widgets`.

**Dialogo/picker migrado**
- `ClientPicker` — antes em `src/ui/widgets/client_picker.py` — agora implementado em `src/modules/clientes/forms/client_picker.py` e exposto via `modules.clientes.forms`.

**Arquivos alterados**
- src/modules/clientes/forms/client_picker.py - novo modulo contendo a implementacao do picker.
- src/modules/clientes/forms/__init__.py - passa a reexportar `ClientPicker`.
- src/ui/widgets/client_picker.py - convertido em shim para manter import legado.
- src/ui/passwords_screen.py - passa a importar `ClientPicker` do pacote de dominio.

**Impacto na modularizacao**
- Dialogos/pickers de clientes comecam a viver ao lado de `form_cliente` dentro do pacote de dominio, reduzindo dependencias diretas de `src.ui`.
- A UI legada continua funcionando via shim, mas novos consumidores podem importar direto de `modules.clientes.forms`.
- Esse passo estabelece o padrao para migrar os demais dialogos/pickers relacionados a clientes.

**Proximos passos sugeridos**
- Migrar outros dialogos/pickers de clientes seguindo o mesmo modelo.
- Revisar dialogos que interagem com o service para usa-lo diretamente via `modules.clientes.service`.
- Encapsular demais integracoes (subpastas, uploads) em submodulos dentro de `modules.clientes`.

## Etapa: Endurecimento do boundary do modulo Clientes (2025-11-15)

**Objetivo desta etapa**
- Remover dependencias diretas de core/Supabase relacionadas ao dominio de clientes fora de `src.modules.clientes`.
- Garantir que CRUD, lixeira e uploads de clientes sejam acessados apenas via API publica de `modules.clientes`.

**Arquivos alterados**
- src/modules/clientes/forms/pipeline.py — recebe o pipeline real de salvar + upload (antes em `src/ui/forms/pipeline.py`).
- src/ui/forms/pipeline.py — convertido em shim que reexporta as funcoes do pipeline hospedado em `modules.clientes`.
- src/modules/clientes/service.py — passa a expor `get_cliente_by_id` e faz import lazy do service de lixeira para evitar ciclos.
- src/app_core.py — agora delega `get_cliente_by_id`/`mover_cliente_para_lixeira` ao service em vez de tocar Supabase direto.
- tests/test_clientes_service.py — ajustado para o novo helper `_get_lixeira_service`.

**Impacto na modularizacao**
- Toda operacao de clientes (salvar, carregar, lixeira, upload) passa pela API de `modules.clientes`, reforcando o boundary do dominio.
- A UI deixa de importar diretamente `src.core.*` para fluxos de clientes; ela apenas chama services/dialogos do pacote de dominio.
- Esse endurecimento abre espaco para futuras refatoracoes internas sem quebrar consumidores.

**Pendencias identificadas**
- Monitorar scripts/API legados que eventualmente ainda importem `src.core.db_manager` diretamente; mover para `modules.clientes` em rodadas futuras.

## Etapa: Testes de integracao do modulo Clientes (2025-11-15)

**Objetivo desta etapa**
- Validar fluxos completos do dominio de clientes (salvar + upload + lixeira) usando apenas a API publica de `modules.clientes`.
- Adotar a pratica de testes de integracao por modulo, recomendada para modular monoliths, garantindo confianca durante futuras refatoracoes.

**Arquivos alterados**
- tests/test_clientes_integration.py — novos testes cobrindo pipeline de upload e servicos de lixeira.
- src/modules/clientes/forms/pipeline.py — pequenos ajustes de testabilidade (ex.: imports reorganizados) para facilitar monkeypatch.
- src/modules/clientes/service.py — exposto `_get_lixeira_service` lazy utilizado nos testes de integracao.
- docs/dev/modularizacao_clientes.md — documentacao desta etapa.

**Impacto na modularizacao**
- Alem dos testes unitarios, o modulo Clientes passa a ter testes de integracao exercitando seu boundary (forms/pipeline + service) sem depender da UI.
- Isso reforca o contrato publico de `modules.clientes` e reduz risco de regressao quando mexermos na orquestracao de uploads ou na lixeira.

**Proximos passos sugeridos**
- Expandir os cenarios de integracao conforme surgirem bugs de clientes ou novas features.
- Considerar testes que simulem pequenas chamadas da UI (ex.: wrappers que acionam o pipeline) para cobrir fluxos ainda nao exercitados.
## Etapa: Segunda migracao de dialogos/pickers de clientes para src.modules.clientes.forms (2025-11-15)

**Objetivo desta etapa**
- Continuar movendo dialogos/pickers exclusivos de clientes do pacote `src.ui` para `src.modules.clientes.forms`.
- Manter shims nos modulos antigos para preservar compatibilidade de import.

**Dialogos/pickers migrados**
- `SubpastaDialog` (formulario simples de subpasta) — antes em `src/ui/forms/actions.py` — agora em `src/modules/clientes/forms/client_subfolder_prompt.py`.
- `open_subpastas_dialog` — antes em `src/ui/subpastas/dialog.py` — agora em `src/modules/clientes/forms/client_subfolders_dialog.py`.

**Arquivos alterados**
- src/modules/clientes/forms/client_subfolder_prompt.py — implementacao do dialogo simples de subpasta.
- src/modules/clientes/forms/client_subfolders_dialog.py — implementacao do dialogo de subpastas locais.
- src/modules/clientes/forms/__init__.py — passa a reexportar os novos dialogos/pickers.
- src/ui/forms/actions.py — convertido para shim que importa `SubpastaDialog` do pacote de dominio.
- src/ui/subpastas/dialog.py — convertido em shim para manter o caminho antigo de `open_subpastas_dialog`.
- src/modules/forms/view.py — agora importa `SubpastaDialog` direto de `modules.clientes.forms`.

**Impacto na modularizacao**
- Os dialogos de subpasta usados pelos fluxos de clientes passam a residir no pacote de dominio, alinhando-os com `form_cliente` e reduzindo dependencias de `src.ui`.
- Os modulos de UI legada viram shims, garantindo compatibilidade enquanto novos consumidores podem importar diretamente de `modules.clientes.forms`.
- Esse movimento reforca que tanto formularios quanto dialogos especificos de clientes ficam concentrados no mesmo pacote.

**Proximos passos sugeridos**
- Migrar os ultimos dialogos/pickers de clientes (ex.: subpastas auxiliares, integrações com uploads) para `modules.clientes.forms`.
- Revisar onde esses dialogos deveriam conversar diretamente com `modules.clientes.service` para evitar acessos ao core/infra.
- Planejar testes focados nesses dialogos/pickers conforme forem migrados.
## Referencia cruzada com o scan global

O diagnostico amplo da modularizacao (dominios, hotspots e proximos passos) esta consolidado em `docs/dev/modularizacao_scan_global.md`. Use o modulo Clientes como template para replicar a mesma estrutura de API publica, views/forms dedicados, services e testes nos demais dominios priorizados pelo scan.
