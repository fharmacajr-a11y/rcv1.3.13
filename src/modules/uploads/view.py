"""View principal do módulo Uploads/Arquivos.

Este módulo encapsula a UI legada de gerenciamento de arquivos
(`files_browser`) em utilitários compatíveis com a camada de módulos,
mantendo 100% de compatibilidade com o comportamento atual.

A ideia é que, no futuro, qualquer ajuste visual do módulo de
Uploads seja feito aqui, sem precisar mexer diretamente em
`src/ui/files_browser.py`.
"""

from __future__ import annotations

from typing import Any, Dict


def _get_legacy_open_files_browser():
    """Lazy import para evitar import circular.

    Importa open_files_browser apenas quando necessário,
    quebrando o ciclo: files_browser → uploads → files_browser.
    """
    from src.ui.files_browser.main import open_files_browser

    return open_files_browser


def _normalize_legacy_args(*args: Any, **kwargs: Any) -> tuple[tuple[Any, ...], Dict[str, Any]]:
    """Adapta chamadas feitas para o browser modular (v1.1.68+)
    para a assinatura do browser legado em
    src.ui.files_browser.open_files_browser.

    Ignora parâmetros extras como `bucket`, `base_prefix` e `modal`,
    preservando `start_prefix`, `module`, `supabase` etc.
    """
    cleaned: Dict[str, Any] = dict(kwargs)

    # Parâmetros específicos do browser modular que o legado não conhece.
    cleaned.pop("bucket", None)
    cleaned.pop("base_prefix", None)

    # O browser legado não implementa comportamento modal via flag;
    # o chamador continua responsável por bloquear/aguardar se quiser.
    cleaned.pop("modal", None)

    return args, cleaned


class UploadsFrame:
    """Alias compatível para abertura da janela do Gerenciador de Arquivos."""

    def __new__(cls, *args: Any, **kwargs: Any):
        args, kwargs = _normalize_legacy_args(*args, **kwargs)
        _legacy_open_files_browser = _get_legacy_open_files_browser()
        return _legacy_open_files_browser(*args, **kwargs)


def open_files_browser(*args: Any, **kwargs: Any):
    """Wrapper fino para a função legada `open_files_browser`.

    Aceita a mesma assinatura utilizada pelas versões modularizadas
    (incluindo `bucket`, `base_prefix` e `modal`), mas descarta esses
    parâmetros ao delegar para o browser legado.
    """
    args, kwargs = _normalize_legacy_args(*args, **kwargs)
    _legacy_open_files_browser = _get_legacy_open_files_browser()
    return _legacy_open_files_browser(*args, **kwargs)
