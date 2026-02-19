"""Project-level sitecustomize to expose src-style packages on sys.path."""

import os
import sys
import warnings

# =============================================================================
# FASE 5 (2026-01-03): Simplificado para src-layout
# -----------------------------------------------------------------------------
# Após migração completa para src/, não precisamos mais adicionar subpastas
# individuais (infra/, adapters/). Apenas garantimos que a RAIZ do projeto
# esteja no sys.path para permitir "import src.*" de forma determinística.
# =============================================================================
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# PyMuPDF (fitz) dispara um DeprecationWarning envolvendo swigvarlink logo ao ser importado.
# Silenciamos no processo inteiro para evitar ruído em run globais e no app.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"builtin type swigvarlink has no __module__ attribute",
)

# NOTA: Warning "Storage endpoint URL should have a trailing slash." do storage3
# -----------------------------------------------------------------------------
# Este warning cosmético é emitido pela lib storage3 durante inicialização.
# A causa raiz foi CORRIGIDA em src/infra/supabase/db_client.py (patch _base_url).
# O warning persiste porque é print() direto no módulo storage3, não configurável.
# Funcionalidade: ✅ OK | Warning: cosmético, sem impacto operacional.
