# 🌳 Visualização em Árvore - Before & After

## 📂 ANTES da Limpeza

```
v1.0.37 (limpar e ok)/
├── 📄 app_core.py                          ✅ KEEP
├── 📄 app_gui.py                           ✅ KEEP (entry point)
├── 📄 app_status.py                        ✅ KEEP
├── 📄 app_utils.py                         ✅ KEEP
├── 📄 config.yml                           ✅ KEEP
├── 📄 EXCLUSOES_SUGERIDAS.md               🗑️ REMOVE (dev doc)
├── 📄 PYINSTALLER_BUILD.md                 🗑️ REMOVE (dev doc)
├── 📄 pyproject.toml                       ✅ KEEP
├── 📄 pytest.ini                           ✅ KEEP
├── 📄 rc.ico                               ✅ KEEP (runtime asset)
├── 📄 rcgestor.spec                        ✅ KEEP (build config)
├── 📄 README.md                            ✅ KEEP
├── 📄 RELATORIO_BUILD_PYINSTALLER.md       🗑️ REMOVE (dev doc)
├── 📄 RELATORIO_ONEFILE.md                 🗑️ REMOVE (dev doc)
├── 📄 requirements-min.in                  ✅ KEEP
├── 📄 requirements-min.txt                 ✅ KEEP
├── 📄 requirements.in                      ✅ KEEP
├── 📄 requirements.txt                     ✅ KEEP
├── 📄 sign_rcgestor.ps1                    ✅ KEEP (build script)
│
├── 📁 __pycache__/                         🗑️ REMOVE (cache)
│
├── 📁 adapters/                            ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   └── 📁 storage/                         ✅ KEEP
│       ├── 📄 __init__.py                  ✅ KEEP
│       ├── 📄 api.py                       ✅ KEEP
│       ├── 📄 port.py                      ✅ KEEP
│       ├── 📄 supabase_storage.py          ✅ KEEP
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
├── 📁 ajuda/                               🗑️ REMOVE (dev docs)
│   ├── 📄 .env.example.template
│   ├── 📄 *.md (40+ arquivos)
│   ├── 📁 _ferramentas/
│   ├── 📁 _quarentena_orfaos/
│   └── 📁 _scripts_dev/
│
├── 📁 application/                         ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 api.py                           ✅ KEEP
│   ├── 📄 auth_controller.py               ✅ KEEP
│   ├── 📄 commands.py                      ✅ KEEP
│   ├── 📄 keybindings.py                   ✅ KEEP
│   ├── 📄 navigation_controller.py         ✅ KEEP
│   ├── 📄 status_monitor.py                ✅ KEEP
│   └── 📁 __pycache__/                     🗑️ REMOVE (cache)
│
├── 📁 assets/                              ✅ KEEP (vazio, mas whitelist)
│
├── 📁 build/                               🗑️ REMOVE (build artifacts)
│   └── 📁 rcgestor/
│       ├── Analysis-00.toc
│       ├── base_library.zip
│       ├── EXE-00.toc
│       ├── PKG-00.toc
│       ├── PYZ-00.pyz
│       ├── rcgestor.pkg
│       └── (outros artefatos PyInstaller)
│
├── 📁 config/                              ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 constants.py                     ✅ KEEP
│   ├── 📄 paths.py                         ✅ KEEP
│   ├── 📄 runtime_manifest.yaml            ✅ KEEP
│   └── 📁 __pycache__/                     🗑️ REMOVE (cache)
│
├── 📁 core/                                ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 models.py                        ✅ KEEP
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   ├── 📁 auth/                            ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 auth.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 db_manager/                      ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 db_manager.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 logs/                            ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 audit.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 search/                          ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 search.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 services/                        ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 clientes_service.py
│   │   ├── 📄 lixeira_service.py
│   │   ├── 📄 path_resolver.py
│   │   ├── 📄 upload_service.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   └── 📁 session/                         ✅ KEEP
│       ├── 📄 __init__.py
│       ├── 📄 session.py
│       ├── 📄 session_guard.py
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
├── 📁 detectors/                           🗑️ REMOVE (vazio/unused)
│   ├── 📄 __init__.py
│   └── 📁 __pycache__/                     🗑️ REMOVE (cache)
│
├── 📁 gui/                                 ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 hub_screen.py                    ✅ KEEP
│   ├── 📄 main_screen.py                   ✅ KEEP
│   ├── 📄 main_window.py                   ✅ KEEP
│   ├── 📄 menu_bar.py                      ✅ KEEP
│   ├── 📄 placeholders.py                  ✅ KEEP
│   ├── 📄 splash.py                        ✅ KEEP
│   └── 📁 __pycache__/                     🗑️ REMOVE (cache)
│
├── 📁 infra/                               ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 healthcheck.py                   ✅ KEEP
│   ├── 📄 net_session.py                   ✅ KEEP
│   ├── 📄 net_status.py                    ✅ KEEP
│   ├── 📄 supabase_auth.py                 ✅ KEEP
│   ├── 📄 supabase_client.py               ✅ KEEP
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   └── 📁 db/                              ✅ KEEP
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
├── 📁 infrastructure/                      🗑️ REMOVE (legacy wrapper)
│   ├── 📄 __init__.py
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   └── 📁 scripts/                         🗑️ REMOVE (wrapper)
│       ├── 📄 __init__.py
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
├── 📁 runtime_docs/                        ✅ KEEP
│   └── 📄 CHANGELOG.md                     ✅ KEEP (usado em runtime!)
│
├── 📁 scripts/                             🗑️ REMOVE (dev scripts)
│   ├── 📄 audit_consolidation.py
│   ├── 📄 convert_utf16_to_utf8.py
│   ├── 📄 generate_tree.py
│   ├── 📄 make_runtime.py
│   ├── 📄 quarantine_orphans.py
│   ├── 📄 regenerate_inventario.ps1
│   ├── 📄 remove_bom.py
│   ├── 📄 smoke_runtime.py
│   └── 📁 __pycache__/                     🗑️ REMOVE (cache)
│
├── 📁 shared/                              ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   ├── 📁 config/                          ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 environment.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   └── 📁 logging/                         ✅ KEEP
│       ├── 📄 __init__.py
│       ├── 📄 audit.py
│       ├── 📄 configure.py
│       ├── 📄 filters.py
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
├── 📁 ui/                                  ✅ KEEP
│   ├── 📄 __init__.py                      ✅ KEEP
│   ├── 📄 components.py                    ✅ KEEP
│   ├── 📄 files_browser.py                 ✅ KEEP
│   ├── 📄 theme.py                         ✅ KEEP
│   ├── 📄 theme_toggle.py                  ✅ KEEP
│   ├── 📄 topbar.py                        ✅ KEEP
│   ├── 📄 utils.py                         ✅ KEEP
│   ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
│   ├── 📁 dialogs/                         ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 upload_progress.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 forms/                           ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 actions.py
│   │   ├── 📄 forms.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 login/                           ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 login.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 lixeira/                         ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 lixeira.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   ├── 📁 subpastas/                       ✅ KEEP
│   │   ├── 📄 __init__.py
│   │   ├── 📄 dialog.py
│   │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│   └── 📁 widgets/                         ✅ KEEP
│       ├── 📄 __init__.py
│       ├── 📄 busy.py
│       └── 📁 __pycache__/                 🗑️ REMOVE (cache)
│
└── 📁 utils/                               ✅ KEEP
    ├── 📄 __init__.py                      ✅ KEEP
    ├── 📄 hash_utils.py                    ✅ KEEP
    ├── 📄 net_retry.py                     ✅ KEEP
    ├── 📄 pdf_reader.py                    ✅ KEEP
    ├── 📄 resource_path.py                 ✅ KEEP (crítico!)
    ├── 📄 subpastas_config.py              ✅ KEEP
    ├── 📄 text_utils.py                    ✅ KEEP
    ├── 📄 theme_manager.py                 ✅ KEEP
    ├── 📄 themes.py                        ✅ KEEP
    ├── 📄 validators.py                    ✅ KEEP
    ├── 📁 __pycache__/                     🗑️ REMOVE (cache)
    ├── 📁 file_utils/                      ✅ KEEP
    │   ├── 📄 __init__.py
    │   ├── 📄 file_utils.py
    │   └── 📁 __pycache__/                 🗑️ REMOVE (cache)
    └── 📁 helpers/                         ✅ KEEP
        ├── 📄 __init__.py
        ├── 📄 cloud_guardrails.py
        ├── 📄 hidpi.py
        ├── 📄 rc_hotfix_no_local_fs.py
        └── 📁 __pycache__/                 🗑️ REMOVE (cache)
```

---

## 📂 DEPOIS da Limpeza

```
v1.0.37 (limpar e ok)/
├── 📄 app_core.py                          ✅ MANTIDO
├── 📄 app_gui.py                           ✅ MANTIDO (entry point)
├── 📄 app_status.py                        ✅ MANTIDO
├── 📄 app_utils.py                         ✅ MANTIDO
├── 📄 config.yml                           ✅ MANTIDO
├── 📄 pyproject.toml                       ✅ MANTIDO
├── 📄 pytest.ini                           ✅ MANTIDO
├── 📄 rc.ico                               ✅ MANTIDO
├── 📄 rcgestor.spec                        ✅ MANTIDO
├── 📄 README.md                            ✅ MANTIDO
├── 📄 requirements-min.in                  ✅ MANTIDO
├── 📄 requirements-min.txt                 ✅ MANTIDO
├── 📄 requirements.in                      ✅ MANTIDO
├── 📄 requirements.txt                     ✅ MANTIDO
├── 📄 sign_rcgestor.ps1                    ✅ MANTIDO
│
├── 📁 adapters/                            ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   └── 📁 storage/
│       ├── 📄 __init__.py
│       ├── 📄 api.py
│       ├── 📄 port.py
│       └── 📄 supabase_storage.py
│
├── 📁 application/                         ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 api.py
│   ├── 📄 auth_controller.py
│   ├── 📄 commands.py
│   ├── 📄 keybindings.py
│   ├── 📄 navigation_controller.py
│   └── 📄 status_monitor.py
│
├── 📁 assets/                              ✅ MANTIDO (vazio)
│
├── 📁 config/                              ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 constants.py
│   ├── 📄 paths.py
│   └── 📄 runtime_manifest.yaml
│
├── 📁 core/                                ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 models.py
│   ├── 📁 auth/
│   │   ├── 📄 __init__.py
│   │   └── 📄 auth.py
│   ├── 📁 db_manager/
│   │   ├── 📄 __init__.py
│   │   └── 📄 db_manager.py
│   ├── 📁 logs/
│   │   ├── 📄 __init__.py
│   │   └── 📄 audit.py
│   ├── 📁 search/
│   │   ├── 📄 __init__.py
│   │   └── 📄 search.py
│   ├── 📁 services/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 clientes_service.py
│   │   ├── 📄 lixeira_service.py
│   │   ├── 📄 path_resolver.py
│   │   └── 📄 upload_service.py
│   └── 📁 session/
│       ├── 📄 __init__.py
│       ├── 📄 session.py
│       └── 📄 session_guard.py
│
├── 📁 gui/                                 ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 hub_screen.py
│   ├── 📄 main_screen.py
│   ├── 📄 main_window.py
│   ├── 📄 menu_bar.py
│   ├── 📄 placeholders.py
│   └── 📄 splash.py
│
├── 📁 infra/                               ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 healthcheck.py
│   ├── 📄 net_session.py
│   ├── 📄 net_status.py
│   ├── 📄 supabase_auth.py
│   ├── 📄 supabase_client.py
│   └── 📁 db/
│
├── 📁 runtime_docs/                        ✅ MANTIDO
│   └── 📄 CHANGELOG.md
│
├── 📁 shared/                              ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📁 config/
│   │   ├── 📄 __init__.py
│   │   └── 📄 environment.py
│   └── 📁 logging/
│       ├── 📄 __init__.py
│       ├── 📄 audit.py
│       ├── 📄 configure.py
│       └── 📄 filters.py
│
├── 📁 ui/                                  ✅ MANTIDO (limpo)
│   ├── 📄 __init__.py
│   ├── 📄 components.py
│   ├── 📄 files_browser.py
│   ├── 📄 theme.py
│   ├── 📄 theme_toggle.py
│   ├── 📄 topbar.py
│   ├── 📄 utils.py
│   ├── 📁 dialogs/
│   │   ├── 📄 __init__.py
│   │   └── 📄 upload_progress.py
│   ├── 📁 forms/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 actions.py
│   │   └── 📄 forms.py
│   ├── 📁 login/
│   │   ├── 📄 __init__.py
│   │   └── 📄 login.py
│   ├── 📁 lixeira/
│   │   ├── 📄 __init__.py
│   │   └── 📄 lixeira.py
│   ├── 📁 subpastas/
│   │   ├── 📄 __init__.py
│   │   └── 📄 dialog.py
│   └── 📁 widgets/
│       ├── 📄 __init__.py
│       └── 📄 busy.py
│
└── 📁 utils/                               ✅ MANTIDO (limpo)
    ├── 📄 __init__.py
    ├── 📄 hash_utils.py
    ├── 📄 net_retry.py
    ├── 📄 pdf_reader.py
    ├── 📄 resource_path.py
    ├── 📄 subpastas_config.py
    ├── 📄 text_utils.py
    ├── 📄 theme_manager.py
    ├── 📄 themes.py
    ├── 📄 validators.py
    ├── 📁 file_utils/
    │   ├── 📄 __init__.py
    │   └── 📄 file_utils.py
    └── 📁 helpers/
        ├── 📄 __init__.py
        ├── 📄 cloud_guardrails.py
        ├── 📄 hidpi.py
        └── 📄 rc_hotfix_no_local_fs.py
```

---

## 📊 Comparação Numérica

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| **Pastas `__pycache__`** | ~30 | 0 | -30 📉 |
| **Build artifacts** | 1 (`build/`) | 0 | -1 📉 |
| **Docs de dev** | 1 (`ajuda/`) | 0 | -1 📉 |
| **Scripts de dev** | 1 (`scripts/`) | 0 | -1 📉 |
| **Módulos vazios** | 2 (`detectors/`, `infrastructure/`) | 0 | -2 📉 |
| **Relatórios MD** | 4 arquivos | 0 | -4 📉 |
| **Total removido** | - | - | **~39 itens** 🎯 |

---

## ✅ Resultado Final

**ANTES:** ~XXX itens (pastas + arquivos)  
**DEPOIS:** ~(XXX - 39) itens  

✨ **Projeto limpo, organizado e funcional!** ✨

---

**Legenda:**
- ✅ KEEP = Mantido (essencial para runtime)
- 🗑️ REMOVE = Movido para quarentena (cache, build, dev)
- 📄 = Arquivo
- 📁 = Pasta
