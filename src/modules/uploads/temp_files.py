"""Gerenciamento de arquivos temporários para uploads/downloads.

Este módulo centraliza a criação e limpeza de arquivos temporários usados
para visualização de arquivos baixados do Supabase Storage.

Política de ciclo de vida:
- Arquivos temporários são criados em %TEMP%/rc_gestor_uploads/
- Cleanup automático de arquivos antigos (>7 dias) no startup
- Logs detalhados de criação/limpeza para troubleshooting
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Diretório base para arquivos temporários do app
TEMP_DIR_NAME = "rc_gestor_uploads"

# Idade máxima em segundos (7 dias)
MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class TempFileInfo(NamedTuple):
    """Informações sobre um arquivo temporário criado."""

    path: str
    """Caminho completo do arquivo temporário."""

    directory: str
    """Diretório onde o arquivo foi criado."""

    filename: str
    """Nome do arquivo (basename)."""


def get_temp_directory() -> Path:
    """Retorna o diretório temporário do app, criando-o se necessário.

    Returns:
        Path para o diretório temporário (ex: %TEMP%/rc_gestor_uploads/)
    """
    system_temp = Path(tempfile.gettempdir())
    app_temp = system_temp / TEMP_DIR_NAME

    if not app_temp.exists():
        app_temp.mkdir(parents=True, exist_ok=True)
        logger.info("Diretório temporário criado: %s", app_temp)

    return app_temp


def create_temp_file(remote_filename: str) -> TempFileInfo:
    """Cria um arquivo temporário para download.

    Args:
        remote_filename: Nome do arquivo remoto (basename)

    Returns:
        TempFileInfo com path, directory e filename

    Raises:
        OSError: Se houver erro ao criar o diretório temporário
    """
    temp_dir = get_temp_directory()

    # Garantir nome de arquivo seguro
    safe_filename = Path(remote_filename).name
    temp_path = temp_dir / safe_filename

    # Se arquivo já existe, adicionar timestamp
    if temp_path.exists():
        stem = temp_path.stem
        suffix = temp_path.suffix
        timestamp = int(time.time())
        safe_filename = f"{stem}_{timestamp}{suffix}"
        temp_path = temp_dir / safe_filename

    logger.debug("Arquivo temporário preparado: %s", temp_path)

    return TempFileInfo(
        path=str(temp_path),
        directory=str(temp_dir),
        filename=safe_filename,
    )


def cleanup_old_files(max_age_seconds: int = MAX_AGE_SECONDS) -> dict[str, int]:
    """Remove arquivos temporários antigos do diretório do app.

    Args:
        max_age_seconds: Idade máxima em segundos (padrão: 7 dias)

    Returns:
        Dict com estatísticas: {"removed": N, "failed": M, "total_bytes": X}
    """
    stats = {"removed": 0, "failed": 0, "total_bytes": 0}

    temp_dir = get_temp_directory()

    if not temp_dir.exists():
        logger.debug("Diretório temporário não existe, nada a limpar")
        return stats

    now = time.time()
    cutoff_time = now - max_age_seconds

    logger.info("Iniciando limpeza de arquivos temporários (idade > %d dias)", max_age_seconds // 86400)

    for item in temp_dir.iterdir():
        if not item.is_file():
            continue

        try:
            file_mtime = item.stat().st_mtime

            if file_mtime < cutoff_time:
                file_size = item.stat().st_size
                item.unlink()
                stats["removed"] += 1
                stats["total_bytes"] += file_size

                age_days = (now - file_mtime) / 86400
                logger.debug(
                    "Removido arquivo temporário antigo: %s (%.1f dias, %d bytes)",
                    item.name,
                    age_days,
                    file_size,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao remover arquivo temporário %s: %s", item.name, exc)
            stats["failed"] += 1

    if stats["removed"] > 0:
        logger.info(
            "Limpeza concluída: %d arquivo(s) removido(s), %.2f MB liberados",
            stats["removed"],
            stats["total_bytes"] / (1024 * 1024),
        )
    else:
        logger.debug("Nenhum arquivo temporário antigo encontrado")

    return stats


def cleanup_on_startup() -> None:
    """Executa limpeza de arquivos antigos no startup do app.

    Esta função deve ser chamada uma vez no início da aplicação.
    """
    try:
        cleanup_old_files()
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro durante limpeza de temporários no startup: %s", exc, exc_info=True)


__all__ = [
    "TempFileInfo",
    "get_temp_directory",
    "create_temp_file",
    "cleanup_old_files",
    "cleanup_on_startup",
]
