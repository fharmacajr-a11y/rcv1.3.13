# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import re
import tempfile
import unicodedata
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote as url_unquote
import threading

from src.config.paths import CLOUD_ONLY
from requests import exceptions as req_exc

from infra.net_session import make_session
from infra.supabase.types import SUPABASE_ANON_KEY, SUPABASE_URL

logger = logging.getLogger("infra.supabase.storage_client")

EDGE_FUNCTION_ZIPPER_URL = f"{SUPABASE_URL}/functions/v1/zipper"

_session = None


def _downloads_dir() -> Path:
    d = Path.home() / "Downloads"
    return d if d.exists() else Path(tempfile.gettempdir())


def _pick_name_from_cd(cd: str, fallback: str) -> str:
    """Extrai filename/filename* de Content-Disposition."""
    if not cd:
        return fallback
    m = re.search(r'filename\*?=(?:UTF-8\'\')?("?)([^";]+)\1', cd)
    if not m:
        return fallback
    return url_unquote(m.group(2))


def _sess():
    """Retorna sessão reutilizável com retry e timeout configurados."""
    global _session
    if _session is None:
        _session = make_session()
    return _session


class DownloadCancelledError(Exception):
    """Sinaliza cancelamento voluntário do usuário durante o download."""

    pass


def baixar_pasta_zip(
    bucket: str,
    prefix: str,
    zip_name: Optional[str] = None,
    out_dir: Optional[os.PathLike[str] | str] = None,
    timeout_s: int = 300,
    cancel_event: Optional[threading.Event] = None,
) -> Path:
    """
    Baixa uma PASTA do Storage (prefix) em .zip via Edge Function 'zipper' (GET).
    """
    if not bucket:
        raise ValueError("bucket é obrigatório")
    if not prefix:
        raise ValueError("prefix é obrigatório")

    base_name = zip_name or prefix.rstrip("/").split("/")[-1] or "pasta"
    desired_name = f"{base_name}.zip"

    destino = Path(out_dir) if out_dir else _downloads_dir()
    if not CLOUD_ONLY:
        destino.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "apikey": SUPABASE_ANON_KEY,
        "Accept": "application/zip,application/json",
        "Accept-Encoding": "identity",  # evita gzip no binário
    }
    params = {"bucket": bucket, "prefix": prefix, "name": desired_name}

    sess = _sess()
    timeouts = (15, timeout_s)  # (connect, read)

    try:
        with sess.get(
            EDGE_FUNCTION_ZIPPER_URL,
            headers=headers,
            params=params,
            stream=True,
            timeout=timeouts,
        ) as resp:
            if resp.status_code != 200:
                try:
                    detail = resp.json()
                except Exception:
                    detail = (resp.text or "")[:600]
                raise RuntimeError(
                    f"Erro do servidor (HTTP {resp.status_code}): {detail}"
                )

            ct = (resp.headers.get("Content-Type") or "").lower()
            if "application/zip" not in ct:
                try:
                    detail = resp.json()
                except Exception:
                    detail = (resp.text or "")[:600]
                raise RuntimeError(
                    f"Resposta inesperada do servidor (Content-Type={ct}). Detalhe: {detail}"
                )

            cd = resp.headers.get("Content-Disposition", "")
            fname = _pick_name_from_cd(cd, desired_name)

            out_path = destino / fname
            base = out_path
            i = 1
            while out_path.exists():
                out_path = base.with_name(f"{base.stem} ({i}){base.suffix}")
                i += 1

            try:
                expected = int(resp.headers.get("Content-Length") or "0")
            except Exception:
                expected = 0

            tmp_path = out_path.with_suffix(out_path.suffix + ".part")
            written = 0
            resp.raw.decode_content = True

            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if cancel_event is not None and cancel_event.is_set():
                        try:
                            resp.close()
                        finally:
                            try:
                                f.close()
                            except Exception:
                                pass
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                        raise DownloadCancelledError("Download cancelado pelo usuário.")

                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)

            if expected and written != expected:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise IOError(f"Download truncado: {written}B != {expected}B")

            tmp_path.replace(out_path)
            return out_path

    except (req_exc.ConnectTimeout, req_exc.ReadTimeout, req_exc.Timeout) as e:
        raise TimeoutError(
            "Tempo esgotado ao baixar (conexão ou leitura). "
            "Verifique sua internet e tente novamente."
        ) from e
    except DownloadCancelledError:
        raise
    except req_exc.RequestException as e:
        raise RuntimeError(f"Falha de rede durante o download: {e}") from e


# -----------------------------------------------------------------------------
# Funções de criação de prefixo para clientes no Storage
# -----------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """
    Converte texto em slug: normaliza unicode, remove acentos, substitui espaços/especiais por hífen.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return text.lower()


def build_client_prefix(
    org_id: str,
    cnpj: str,
    razao_social: str = "",
    client_id: int | None = None,
) -> str:
    """
    Constrói o prefixo de armazenamento para um cliente no formato:
    {org_id}/{cnpj_digits}-{slug}[-{client_id:06d}]
    
    Args:
        org_id: ID da organização
        cnpj: CNPJ do cliente (será normalizado para apenas dígitos)
        razao_social: Razão social do cliente (será slugificada)
        client_id: ID do cliente (opcional, será formatado com 6 dígitos)
    
    Returns:
        String do prefixo (sem barra final)
    """
    # Normaliza CNPJ para apenas dígitos
    cnpj_digits = re.sub(r"\D", "", cnpj or "")
    
    # Slugifica razão social ou usa "cliente" como fallback
    slug = _slugify(razao_social) or "cliente"
    
    # Monta prefixo base
    base = f"{org_id}/{cnpj_digits}-{slug}"
    
    # Adiciona client_id se fornecido
    if client_id:
        base = f"{base}-{client_id:06d}"
    
    return base  # sem barra final


def ensure_client_storage_prefix(
    bucket: str,
    org_id: str,
    cnpj: str,
    razao_social: str = "",
    client_id: int | None = None,
) -> str:
    """
    Garante que o prefixo exista no Storage criando um placeholder '.keep'.
    
    Esta função cria um arquivo vazio .keep no prefixo do cliente para garantir
    que a "pasta" exista no Supabase Storage (que funciona baseado em objetos).
    
    Args:
        bucket: Nome do bucket do Supabase Storage
        org_id: ID da organização
        cnpj: CNPJ do cliente
        razao_social: Razão social do cliente
        client_id: ID do cliente
    
    Returns:
        String do prefixo criado
        
    Raises:
        Exception: Se houver erro ao criar o placeholder no Storage
    """
    from infra.supabase_client import supabase
    
    prefix = build_client_prefix(org_id, cnpj, razao_social, client_id)
    key = f"{prefix}/.keep"
    
    logger.info(
        "ensure_client_storage_prefix: criando placeholder bucket=%s key=%s",
        bucket,
        key,
    )
    
    try:
        # Upload de 1 byte; 'upsert' True para idempotência
        data = io.BytesIO(b"1")
        
        # Compatibilidade: alguns clients usam .from_ e outros .from_
        bucket_ref = getattr(supabase.storage, "from_", supabase.storage.from_)(bucket)
        
        res = bucket_ref.upload(
            path=key,
            file=data,
            file_options={"contentType": "text/plain", "upsert": True},
        )
        
        # Logar retorno para debug
        logger.info(
            "ensure_client_storage_prefix: placeholder criado com sucesso - bucket=%s key=%s resp=%s",
            bucket,
            key,
            getattr(res, "data", res),
        )
        
        return prefix
        
    except Exception as exc:
        logger.exception(
            "Erro ao criar placeholder no Storage: bucket=%s key=%s erro=%s",
            bucket,
            key,
            exc,
        )
        raise
