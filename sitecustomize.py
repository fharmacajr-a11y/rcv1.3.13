"""Project-level sitecustomize to expose src-style packages on sys.path."""

import os
import sys
import warnings

_ROOT = os.path.dirname(os.path.abspath(__file__))
for rel_path in ("src", "infra", "adapters"):
    abs_path = os.path.join(_ROOT, rel_path)
    if os.path.isdir(abs_path) and abs_path not in sys.path:
        sys.path.insert(0, abs_path)

# PyMuPDF (fitz) dispara um DeprecationWarning envolvendo swigvarlink logo ao ser importado.
# Silenciamos no processo inteiro para evitar ruído em run globais e no app.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"builtin type swigvarlink has no __module__ attribute",
)
