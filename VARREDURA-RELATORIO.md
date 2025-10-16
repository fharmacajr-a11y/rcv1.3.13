# Relatório de Verificação — v1.0.14 (Fases 1–4)

## Fase 1 — resource_path & sha256_file
- utils/resource_path.py: ✅ | __all__: ✅ | corpo: ✅
- utils/hash_utils.py: ✅ | __all__: ✅ | corpo: ✅
- **Consumidores (imports/fallbacks):**
  - app_gui.py: resource_path ✅ / sha256 ✅ -> ✅
  - core/services/upload_service.py: resource_path ❌ / sha256 ✅ -> ✅
  - core/services/supabase_uploader.py: resource_path ❌ / sha256 ✅ -> ✅
  - ui/login/login.py: resource_path ✅ / sha256 ❌ -> ✅
  - ui/forms/actions.py: resource_path ✅ / sha256 ✅ -> ✅

## Fase 2 — validators & OkCancelMixin
- utils/validators.py: ✅
- `only_digits` duplicado(s) fora de utils: 0
- OkCancelMixin em ui/utils.py: ✅

## Fase 3 — center_on_parent
- Definido em ui/utils.py: ✅
- Uso/imports:
  - ui/login/login.py: ✅
  - ui/forms/actions.py: ✅
  - ui/dialogs.py: ❌
  - app_gui.py: ✅

## Fase 4 — imports absolutos & __all__
- __all__ em ui/utils.py (expondo center_on_parent): ✅
- ui/__init__.py presente (reexport possível): ✅

## Import smoke (sem executar GUI)
- import utils.resource_path: ✅
- import utils.hash_utils: ✅
- import utils.validators: ✅
- import ui.utils: ✅