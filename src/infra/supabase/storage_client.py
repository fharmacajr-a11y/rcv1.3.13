# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import tempfile
import unicodedata
import logging
from pathlib import Path
from typing import Callable, Final
from urllib.parse import unquote as url_unquote
import threading

from src.config.paths import CLOUD_ONLY
from requests import exceptions as req_exc
from http.client import RemoteDisconnected
from urllib3.exceptions import ReadTimeoutError, ProtocolError

from src.infra.net_session import make_session
from src.infra.supabase.types import SUPABASE_ANON_KEY, SUPABASE_URL

logger = logging.getLogger("infra.supabase.storage_client")

EDGE_FUNCTION_ZIPPER_URL: Final[str] = f"{SUPABASE_URL}/functions/v1/zipper"

_session = None


def _downloads_dir() -> Path:
    d = Path.home() / "Downloads"
    return d if d.exists() else Path(tempfile.gettempdir())


def _pick_name_from_cd(cd: str, fallback: str) -> str:
    """Extrai filename/filename* de Content-Disposition.

    Args:
        cd: Header Content-Disposition
        fallback: Nome padrão se não encontrar filename

    Returns:
        Nome do arquivo extraído ou fallback
    """
    if not cd:
        return fallback
    m: re.Match[str] | None = re.search(r'filename\*?=(?:UTF-8\'\')?("?)([^";]+)\1', cd)
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
    zip_name: str | None = None,
    out_dir: os.PathLike[str] | str | None = None,
    timeout_s: int = 300,
    cancel_event: threading.Event | None = None,
    progress_cb: Callable[[int], None] | None = None,
) -> Path:
    """Baixa uma PASTA do Storage (prefix) em .zip via Edge Function 'zipper' (GET).

    Args:
        bucket: Nome do bucket de storage
        prefix: Prefixo da pasta a baixar
        zip_name: Nome desejado para o arquivo .zip (opcional)
        out_dir: Diretório de destino (padrão: Downloads ou temp)
        timeout_s: Timeout de leitura em segundos
        cancel_event: Event para cancelamento durante download
        progress_cb: Callback para progresso (recebe bytes baixados)

    Returns:
        Path do arquivo .zip baixado

    Raises:
        ValueError: Se bucket ou prefix estiverem vazios
        RuntimeError: Se servidor retornar erro ou resposta inesperada
        TimeoutError: Se conexão/leitura exceder timeout
        DownloadCancelledError: Se usuário cancelar via cancel_event
        IOError: Se download for truncado (tamanho incompatível)
    """
    if not bucket:
        raise ValueError("bucket é obrigatório")
    if not prefix:
        raise ValueError("prefix é obrigatório")

    base_name: str = zip_name or prefix.rstrip("/").split("/")[-1] or "pasta"
    desired_name: str = f"{base_name}.zip"

    destino: Path = Path(out_dir) if out_dir else _downloads_dir()
    if not CLOUD_ONLY:
        destino.mkdir(parents=True, exist_ok=True)

    anon_key = SUPABASE_ANON_KEY or ""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {anon_key}",
        "apikey": anon_key,
        "Accept": "application/zip,application/json",
        "Accept-Encoding": "identity",  # evita gzip no binário
    }
    params = {
        "bucket": bucket,
        "prefix": prefix,
        "name": desired_name,
    }

    sess = _sess()
    timeouts: tuple[int, int] = (15, timeout_s)  # (connect, read)

    try:
        logger.info(
            "ZIP: iniciando preparo via zipper | bucket=%s prefix=%s name=%s",
            bucket,
            prefix,
            desired_name,
        )
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
                raise RuntimeError(f"Erro do servidor (HTTP {resp.status_code}): {detail}")

            ct: str = (resp.headers.get("Content-Type") or "").lower()
            if "application/zip" not in ct:
                try:
                    detail = resp.json()
                except Exception:
                    detail = (resp.text or "")[:600]
                raise RuntimeError(f"Resposta inesperada do servidor (Content-Type={ct}). Detalhe: {detail}")

            cd: str = resp.headers.get("Content-Disposition", "")
            fname: str = _pick_name_from_cd(cd, desired_name)

            out_path: Path = destino / fname
            base: Path = out_path
            i: int = 1
            while out_path.exists():
                out_path = base.with_name(f"{base.stem} ({i}){base.suffix}")
                i += 1

            expected: int
            try:
                expected = int(resp.headers.get("Content-Length") or "0")
            except Exception:
                expected = 0

            tmp_path: Path = out_path.with_suffix(out_path.suffix + ".part")
            written: int = 0
            resp.raw.decode_content = True

            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if cancel_event is not None and cancel_event.is_set():
                        try:
                            resp.close()
                        finally:
                            try:
                                f.close()
                            except Exception as exc:
                                logger.debug("Erro ao fechar arquivo temporário", exc_info=exc)
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except Exception as exc:
                                logger.debug("Erro ao remover arquivo temporário cancelado", exc_info=exc)
                        raise DownloadCancelledError("Operação cancelada pelo usuário.")

                    if not chunk:
                        continue

                    f.write(chunk)
                    written += len(chunk)

                    if progress_cb is not None:
                        try:
                            progress_cb(len(chunk))
                        except Exception as exc:
                            logger.debug("Callback de progresso falhou", exc_info=exc)

            if cancel_event is not None and cancel_event.is_set():
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception as exc:
                    logger.debug("Erro ao remover arquivo após cancelamento", exc_info=exc)
                raise DownloadCancelledError("Operação cancelada no final do download.")

            if expected and written != expected:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception as exc:
                    logger.debug("Erro ao limpar arquivo truncado", exc_info=exc)
                raise IOError(f"Download truncado: {written}B != {expected}B")

            os.replace(tmp_path, out_path)
            return out_path

    except (req_exc.ConnectTimeout, req_exc.ReadTimeout, req_exc.Timeout, ReadTimeoutError) as e:
        logger.warning(
            "ZIP: timeout (connect/read) | bucket=%s prefix=%s name=%s erro=%s",
            bucket,
            prefix,
            desired_name,
            e,
        )
        raise TimeoutError(
            "Tempo esgotado ao baixar (conexão ou leitura). Verifique sua internet e tente novamente."
        ) from e
    except DownloadCancelledError:
        raise
    except (RemoteDisconnected, ProtocolError, req_exc.ConnectionError, req_exc.RequestException) as e:
        # Conexão encerrada pelo servidor antes de responder ou erro de protocolo/conn.
        friendly = (
            "Não foi possível preparar o ZIP no Supabase. "
            "O servidor encerrou a conexão antes de responder. Tente novamente em alguns instantes."
        )
        logger.warning(
            "ZIP: conexão encerrada/erro de protocolo | bucket=%s prefix=%s name=%s erro=%s",
            bucket,
            prefix,
            desired_name,
            e,
        )
        # Mantém compat com testes legados que verificam 'Falha de rede':
        raise RuntimeError(f"Falha de rede durante o download: {friendly}") from e


# -----------------------------------------------------------------------------
# Funções de criação de prefixo para clientes no Storage
# -----------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Converte texto em slug: normaliza unicode, remove acentos, substitui espaços/especiais por hífen.

    Args:
        text: Texto a ser convertido em slug

    Returns:
        Texto em formato slug (lowercase, sem acentos, hífens no lugar de especiais)
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
    """Constrói o prefixo de armazenamento para um cliente no formato: {org_id}/{client_id}

    Args:
        org_id: ID da organização
        cnpj: CNPJ do cliente (atualmente não usado no prefixo)
        razao_social: Razão social do cliente (atualmente não usado no prefixo)
        client_id: ID do cliente (obrigatório)

    Returns:
        Prefixo no formato "{org_id}/{client_id}"

    Raises:
        ValueError: Se client_id for None
    """
    if not client_id:
        raise ValueError("client_id obrigatório para montar o prefixo compatível.")
    return f"{org_id}/{client_id}"


def ensure_client_storage_prefix(
    bucket: str,
    org_id: str,
    cnpj: str,
    razao_social: str = "",
    client_id: int | None = None,
) -> str:
    """Garante que o prefixo exista no Storage criando um placeholder '.keep'.

    Args:
        bucket: Nome do bucket de storage
        org_id: ID da organização
        cnpj: CNPJ do cliente
        razao_social: Razão social do cliente
        client_id: ID do cliente (obrigatório)

    Returns:
        Prefixo criado no formato "{org_id}/{client_id}"

    Raises:
        ValueError: Se client_id for None (via build_client_prefix)
        Exception: Se falhar ao criar placeholder no Storage

    Note:
        - Usa arquivo temporário (caminho em disco) porque storage3 abre via open()
        - Define 'upsert' como STRING "true" (não bool), evitando erro do httpx .encode()
        - Alinha o caminho com os uploads: <ORG>/<CLIENT_ID>/.keep
    """
    from src.infra.supabase_client import supabase

    # Prefixo alinhado
    prefix: str = build_client_prefix(org_id, cnpj, razao_social, client_id)
    key: str = f"{prefix}/.keep"

    logger.info("ensure_client_storage_prefix: criando placeholder bucket=%s key=%s", bucket, key)

    tmp_path: str | None = None
    # Compat entre storage3.from_ e .from_
    bucket_ref = getattr(supabase.storage, "from_", supabase.storage.from_)(bucket)

    try:
        fd: int
        fd, tmp_path = tempfile.mkstemp(prefix="rc_keep_", suffix=".txt")
        os.write(fd, b"1")
        os.close(fd)

        # >>> Fix principal: upsert como STRING <<<
        res = bucket_ref.upload(
            key,
            tmp_path,
            {"contentType": "text/plain", "upsert": "true"},
        )

        logger.info("Storage placeholder OK | bucket=%s key=%s resp=%s", bucket, key, getattr(res, "data", res))
        return prefix.rstrip("/")
    except Exception as exc:
        logger.exception("Erro ao criar placeholder no Storage: bucket=%s key=%s erro=%s", bucket, key, exc)
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.warning("Não conseguiu apagar tmp: %s", tmp_path)
