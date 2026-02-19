from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DownloadContext:
    base_name: str
    default_dir: Path
    extension: str


def get_default_download_dir() -> Path:
    """
    Retorna um diretório padrão (Downloads) de forma compatível com o código legado.
    """
    try:
        import ctypes
        import ctypes.wintypes
        import uuid

        folder_id_downloads = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath  # noqa: N806 (Win32 API name)
        SHGetKnownFolderPath.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        p_path = ctypes.c_wchar_p()
        guid_bytes = folder_id_downloads.bytes_le
        guid_int = int.from_bytes(guid_bytes, byteorder="little")
        hr = SHGetKnownFolderPath(
            ctypes.c_void_p(guid_int),
            0,
            None,
            ctypes.byref(p_path),
        )
        if hr == 0 and p_path.value:
            return Path(p_path.value)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter pasta Downloads pelo shell: %s", exc)
    return Path(os.path.expanduser("~")) / "Downloads"


def build_unique_path(ctx: DownloadContext) -> Path:
    """
    Gera um caminho único com sufixo incremental, preservando o padrão legado.
    """
    ext = ctx.extension if ctx.extension.startswith(".") else f".{ctx.extension}"
    directory = ctx.default_dir
    base = ctx.base_name
    candidate = directory / f"{base}{ext}"
    counter = 1
    stem = directory / base
    while candidate.exists():
        candidate = Path(f"{stem} ({counter}){ext}")
        counter += 1
    return candidate


def save_pdf(bytes_data: Optional[bytes], source_path: Optional[str], ctx: DownloadContext) -> Path:
    """
    Salva um PDF vindo de bytes ou copia a partir de um caminho existente.
    """
    target = build_unique_path(ctx)
    if bytes_data:
        target.write_bytes(bytes_data)
        return target
    if source_path:
        src = Path(source_path)
        if src.exists():
            shutil.copyfile(src, target)
            return target
    raise FileNotFoundError("Nenhum PDF carregado.")


def save_image(pil_image: Any, ctx: DownloadContext) -> Path:
    """
    Salva uma imagem PIL respeitando o padrão legado e com fallback para PNG.
    """
    if pil_image is None:
        raise ValueError("Imagem indisponível.")

    target = build_unique_path(ctx)
    try:
        save_img = pil_image
        if getattr(pil_image, "mode", "") in ("P", "LA"):
            save_img = pil_image.convert("RGBA")
        elif getattr(pil_image, "mode", "") in ("1",):
            save_img = pil_image.convert("L")
        save_img.save(target)
        return target
    except Exception:
        fallback_ctx = DownloadContext(
            base_name=ctx.base_name,
            default_dir=ctx.default_dir,
            extension=".png",
        )
        target = build_unique_path(fallback_ctx)
        save_img = pil_image
        mode = getattr(pil_image, "mode", "")
        if mode not in ("RGB", "RGBA"):
            try:
                save_img = pil_image.convert("RGBA")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao converter imagem para RGBA; mantendo modo atual: %s", exc)
        save_img.save(target, format="PNG")
        return target
