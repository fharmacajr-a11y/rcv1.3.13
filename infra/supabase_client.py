# infra/supabase_client.py
from __future__ import annotations
from config.paths import CLOUD_ONLY

import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import unquote as url_unquote

from requests import exceptions as req_exc

from supabase import Client, create_client
from shared.config.environment import load_env, env_str

load_env()


# -----------------------------------------------------------------------------#
# .env (compatível com qualquer CWD e PyInstaller)
# -----------------------------------------------------------------------------#
def _project_root() -> Path:
    # este arquivo está em <raiz>/infra/supabase_client.py
    return Path(__file__).resolve().parent.parent


# ordem de carga: empacotado -> raiz do projeto -> CWD (se existir)
SUPABASE_URL: str | None = env_str("SUPABASE_URL")
SUPABASE_ANON_KEY: str | None = env_str("SUPABASE_ANON_KEY")
SUPABASE_BUCKET: str = env_str("SUPABASE_BUCKET") or "rc-docs"

# -----------------------------------------------------------------------------#
# Cliente Supabase (lazy)
# -----------------------------------------------------------------------------#
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Cria/reusa cliente Supabase; valida variáveis só aqui (não no import)."""
    global _supabase_client, SUPABASE_URL, SUPABASE_ANON_KEY
    if _supabase_client is None:
        SUPABASE_URL = SUPABASE_URL or env_str("SUPABASE_URL")
        SUPABASE_ANON_KEY = SUPABASE_ANON_KEY or env_str("SUPABASE_ANON_KEY")
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(
                "Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env/ambiente."
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client


# Proxy preguiçoso: ao acessar qualquer atributo, resolve o client na hora
class _SupabaseLazy:
    def __getattr__(self, name: str):
        return getattr(get_supabase(), name)


supabase = _SupabaseLazy()  # <- não instancia nada na importação

# -----------------------------------------------------------------------------#
# Helpers
# -----------------------------------------------------------------------------#
EDGE_FUNCTION_ZIPPER_URL = f"{SUPABASE_URL}/functions/v1/zipper"


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


# Sessão lazy para reutilizar conexões com retry/timeout
_session = None


def _sess():
    """Retorna sessão reutilizável com retry e timeout configurados."""
    global _session
    if _session is None:
        from infra.net_session import make_session

        _session = make_session()
    return _session


# -----------------------------------------------------------------------------#
# Exports explícitos do módulo
# -----------------------------------------------------------------------------#
__all__ = ["supabase", "get_supabase", "baixar_pasta_zip", "DownloadCancelledError"]


# -----------------------------------------------------------------------------#
# Download (com cancelamento + mensagens amigáveis)
# -----------------------------------------------------------------------------#
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
