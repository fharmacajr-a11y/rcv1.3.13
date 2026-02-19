# -*- coding: utf-8 -*-
"""
DEPRECATED (UP-05): Service layer legado para fluxo de salvar + upload de documentos.

Este módulo não é mais usado em produção. Novos fluxos devem usar:
- src.modules.uploads.service (upload_items_for_client)
- src.modules.uploads.views.upload_dialog (UploadDialog)

Mantido apenas para compatibilidade com testes legacy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


def salvar_e_upload_docs_service(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    DEPRECATED (UP-05): Use UploadDialog + upload_items_for_client.

    Este service legado não é mais chamado em produção.
    """
    log.warning(
        "DEPRECATED: salvar_e_upload_docs_service foi chamado. Use src.modules.uploads.views.upload_dialog.UploadDialog"
    )

    raise NotImplementedError(
        "salvar_e_upload_docs_service foi removido (UP-05). "
        "Use src.modules.uploads.views.upload_dialog.UploadDialog + "
        "src.modules.uploads.service.upload_items_for_client"
    )
