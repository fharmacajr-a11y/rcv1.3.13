# Relatório de Modularização – RC - Gestor de Clientes

## a) Árvore de diretórios atual
```
.
├── app_core.py
├── app_gui.py
├── app_status.py
├── app_utils.py
├── CHANGELOG.md
├── config/
│   └── __init__.py
├── core/
│   ├── auth/
│   ├── classify_document/
│   ├── db_manager/
│   ├── logs/
│   ├── search/
│   ├── services/
│   └── session/
├── detectors/
│   └── cnpj_card.py
├── infra/
│   ├── db/
│   ├── net_status.py
│   └── supabase_client.py
├── scripts/
│   └── healthcheck.py
├── ui/
│   ├── components.py
│   ├── files_browser.py
│   ├── utils.py
│   ├── forms/
│   ├── lixeira/
│   ├── login/
│   ├── menu/
│   ├── subpastas/
│   └── users/
├── utils/
│   ├── file_utils/
│   ├── helpers/
│   ├── themes.py
│   ├── theme_manager.py
│   ├── validators.py
│   └── resource_path.py
└── requirements.txt
```

Observação: diretórios auxiliares gerados em tempo de execução (.venv/, __pycache__/, logs) foram omitidos da árvore acima.

## b) Organização sugerida
```
core/
├── domain/                # modelos de negócio (clientes, usuários, etc.)
├── services/              # orquestração e regras de negócio puras
├── repositories/          # acesso a dados (Supabase, arquivos locais)
└── workflows/             # fluxos compostos (upload, classificações)

gui/
├── app.py                 # ponto de entrada da camada GUI
├── navigation.py          # helpers de troca de telas
└── screens/
    ├── hub.py             # HubScreen (pré-home)
    ├── main.py            # Tela principal (hoje App)
    ├── login.py           # Diálogo de login
    └── placeholders.py    # telas “em breve”

features/
├── sifap/                 # funcionalidades específicas (componentes + serviços)
├── anvisa/
└── senhas/

shared/
├── adapters/              # integradores externos (API SIFAP, ANVISA, etc.)
├── validators/            # validações reutilizáveis
├── utils/                 # utilitários cross-cutting (formatadores, hash, paths)
└── config/                # carregamento de configurações e .env

tests/
└── ...
```

## c) Arquivos candidatos a refactor
- `app_gui.py`: monolítico (800+ linhas). Sugestão: extrair construção da UI principal para `gui/screens/main.py` e mover lógica de navegação para `gui/navigation.py`.
- `app_core.py` e `app_status.py`: contêm lógica de domínio misturada com gerenciamento de UI; migrar para `core/services/` e expor interfaces para a camada GUI.
- `ui/components.py`: agrega múltiplos widgets compostos; dividir por contexto (`clients_tree.py`, `dialogs.py`) para facilitar manutenibilidade.
- `core/services/upload_service.py`: mistura lógica de fila, Supabase e notificações. Separar adaptadores externos (`infra/supabase_adapter.py`) e camada de orquestração (`core/workflows/upload.py`).
- `utils/themes.py` e `utils/theme_manager.py`: mover para `gui/theme/` para aproximar do contexto UI.
- `detectors/cnpj_card.py`: alinhar nomenclatura (ex.: `features/sifap/cnpj_detector.py`) e encapsular dependências.

## d) Riscos e plano de migração incremental
- **Risco de regressão na GUI**: extração da tela principal pode quebrar bindings e estados globais. Plano: criar `MainScreen` como wrapper mantendo interface pública (`carregar`, `novo_cliente`, etc.) e migrar métodos gradualmente.
- **Dependências cruzadas core/gui**: serviços chamam diretamente messageboxes. Plano: introduzir layer de eventos/notificações (ex.: callbacks injetados) antes de remover chamadas diretas.
- **Integrações externas (Supabase, ANVISA, SIFAP)**: alto risco ao mover adaptadores. Plano: encapsular clientes existentes em classes e adicionar testes de contrato antes da migração.
- **Empacotamento PyInstaller**: mudanças em paths/`resource_path` podem quebrar build. Plano: manter wrappers atuais enquanto novas estruturas são validadas em build experimental.
- **Condições offline (`RC_NO_LOCAL_FS`)**: garantir que refactors não introduzam I/O direto. Plano: documentar invariantes no módulo `core.repositories` e adicionar testes simulando modo offline.

### Próximos passos sugeridos
1. Criar módulo `gui/screens/main.py` com cópia da construção atual da UI e adaptar `app_gui.py` para usar a classe extraída.
2. Introduzir `core/workflows/` com casos de uso (ex.: `ListarClientesCase`) e mover chamadas de busca/upload para lá.
3. Revisar dependências de `utils/` e dividir entre `shared/utils` (genéricos) e `gui/theme` (específicos da interface).
4. Configurar suíte mínima de testes (`pytest`) para validar importação das telas e fluxos críticos antes da próxima fase de refatoração.
