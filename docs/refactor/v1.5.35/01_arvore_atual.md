# 01 - Árvore de Diretórios Atual

> **Versão de referência:** v1.5.35  
> **Data:** 2025-01-02  
> **Foco:** Pastas que serão movidas ou impactadas pela refatoração

---

## 📂 Visão Geral da Raiz

```
v1.5.35/
├── main.py                  # Entrypoint principal
├── sitecustomize.py         # Manipula sys.path (CRÍTICO)
├── rcgestor.spec            # Build PyInstaller
├── pyproject.toml           # Configuração do projeto
├── requirements.txt         # Dependências
│
├── src/                     # ✅ Código principal (destino)
├── infra/                   # ⚠️  A ser movido → src/infra/
├── data/                    # ⚠️  A ser movido → src/data/
├── adapters/                # ⚠️  A ser movido → src/adapters/
├── security/                # ⚠️  A ser movido → src/security/
│
├── tests/                   # Testes (não mover)
├── docs/                    # Documentação (não mover)
├── assets/                  # Assets UI (não mover)
├── config/                  # Configurações (não mover)
└── ...
```

---

## 📁 Estrutura: src/

```
src/
├── __init__.py
├── app_core.py              # Core do aplicativo
├── app_gui.py               # GUI principal (entrypoint real)
├── app_status.py            # Status do app
├── app_utils.py             # Utilitários do app
├── version.py               # Versão do app
│
├── clientes_docs/           # Documentos de clientes
├── config/                  # Configurações
├── core/                    # Núcleo da aplicação
│   ├── api/
│   ├── auth/
│   ├── db_manager/
│   ├── logs/
│   ├── search/
│   ├── services/
│   └── session/
│
├── db/                      # Database
├── features/                # Features específicas
│   ├── cashflow/
│   ├── regulations/
│   └── tasks/
│
├── helpers/                 # Helpers compartilhados
├── infrastructure/          # Infraestrutura interna
│   └── repositories/
│
├── modules/                 # Módulos de negócio
│   ├── anvisa/
│   │   ├── controllers/
│   │   ├── helpers/
│   │   ├── services/
│   │   ├── utils/
│   │   └── views/
│   ├── auditoria/
│   │   ├── application/
│   │   └── views/
│   ├── cashflow/
│   │   └── views/
│   ├── chatgpt/
│   │   └── views/
│   ├── clientes/
│   │   ├── components/
│   │   ├── controllers/
│   │   ├── forms/
│   │   └── views/
│   ├── forms/
│   ├── hub/
│   │   ├── controllers/
│   │   ├── dashboard/
│   │   ├── helpers/
│   │   ├── infrastructure/
│   │   ├── services/
│   │   ├── viewmodels/
│   │   └── views/
│   ├── lixeira/
│   │   └── views/
│   ├── login/
│   ├── main_window/
│   │   ├── controllers/
│   │   └── views/
│   │       └── components/
│   ├── notas/
│   ├── passwords/
│   │   └── views/
│   ├── pdf_preview/
│   │   ├── controllers/
│   │   ├── helpers/
│   │   └── views/
│   ├── pdf_tools/
│   ├── sites/
│   │   └── views/
│   ├── tasks/
│   │   └── views/
│   └── uploads/
│       ├── components/
│       └── views/
│
├── shared/                  # Código compartilhado
├── ui/                      # Componentes UI
│   ├── components/
│   │   └── notifications/
│   ├── controllers/
│   ├── dialogs/
│   ├── files_browser/
│   ├── forms/
│   ├── hub/
│   ├── lixeira/
│   ├── login/
│   ├── main_window/
│   ├── progress/
│   ├── subpastas/
│   └── widgets/
│
└── utils/                   # Utilitários
    ├── file_utils/
    └── helpers/
```

---

## 📁 Estrutura: infra/ (a ser movido)

```
infra/
├── __init__.py
├── archive_utils.py         # Utilitários de arquivamento
├── db_schemas.py            # Schemas de banco
├── healthcheck.py           # Health check
├── net_session.py           # Sessão de rede
├── net_status.py            # Status de rede
├── settings.py              # Configurações
├── supabase_auth.py         # Auth Supabase
├── supabase_client.py       # Cliente Supabase
│
├── bin/
│   └── 7zip/                # Binários 7zip
│       ├── 7z.dll
│       ├── 7z.exe
│       └── README.md
│
├── http/
│   ├── __init__.py
│   └── retry.py             # Retry HTTP
│
├── repositories/
│   ├── __init__.py
│   ├── activity_events_repository.py
│   ├── anvisa_requests_repository.py
│   ├── notifications_repository.py
│   └── passwords_repository.py
│
└── supabase/
    ├── __init__.py
    ├── auth_client.py
    ├── db_client.py
    ├── http_client.py
    ├── storage_client.py
    ├── storage_helpers.py
    └── types.py
```

---

## 📁 Estrutura: data/ (a ser movido)

```
data/
├── __init__.py
├── auth_bootstrap.py        # Bootstrap de autenticação
├── domain_types.py          # Tipos de domínio
└── supabase_repo.py         # Repositório Supabase
```

---

## 📁 Estrutura: adapters/ (a ser movido)

```
adapters/
├── __init__.py
└── storage/
    ├── __init__.py
    ├── api.py               # API de storage
    ├── port.py              # Port (interface)
    └── supabase_storage.py  # Implementação Supabase
```

---

## 📁 Estrutura: security/ (a ser movido)

```
security/
├── __init__.py
└── crypto.py                # Criptografia
```

---

## 📊 Resumo de Arquivos por Pasta

| Pasta | Arquivos .py | Subpastas |
|-------|--------------|-----------|
| `src/` | ~150+ | 20+ |
| `infra/` | 17 | 4 |
| `data/` | 4 | 0 |
| `adapters/` | 5 | 1 |
| `security/` | 2 | 0 |

**Total a mover:** ~28 arquivos .py em 4 pastas
