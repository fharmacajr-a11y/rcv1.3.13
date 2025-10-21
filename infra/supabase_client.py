# infra/supabase_client.py
from __future__ import annotations
from config.paths import CLOUD_ONLY

import os
import re
import tempfile
import threading
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote as url_unquote

import httpx
from httpx import Timeout
from requests import exceptions as req_exc

from supabase import Client, ClientOptions, create_client
from shared.config.environment import load_env, env_str

from infra.http.retry import retry_call

load_env()

log = logging.getLogger(__name__)

_HTTPX_TIMEOUT = Timeout(connect=10.0, read=60.0, write=60.0, pool=None)
_HTTPX_CLIENT = httpx.Client(
    http2=False,  # força HTTP/1.1 para evitar glitches no Windows
    timeout=_HTTPX_TIMEOUT,
)


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
# Cliente Supabase SINGLETON (thread-safe) + Health Check
# -----------------------------------------------------------------------------#
_SUPABASE_SINGLETON: Optional[Client] = None
_SINGLETON_REUSE_LOGGED: bool = False
_SINGLETON_LOCK = threading.Lock()

# -----------------------------------------------------------------------------#
# Sistema de 3 Estados de Conectividade: Online / Instável / Offline
# -----------------------------------------------------------------------------#
# Configurações do health-check (podem ser sobrescritas via variáveis de ambiente)
HEALTHCHECK_INTERVAL_SECONDS = float(os.getenv("RC_HEALTHCHECK_INTERVAL", "30"))   # padrão 30s
HEALTHCHECK_UNSTABLE_THRESHOLD = float(os.getenv("RC_HEALTHCHECK_UNSTABLE", "60")) # padrão 60s
HEALTHCHECK_USE_RPC = True
HEALTHCHECK_RPC_NAME = "ping"    # public.ping()
HEALTHCHECK_FALLBACK_TABLE = "profiles"  # caso RPC falhe, usar select em tabela leve

# Flag para desligar o checker, se necessário
HEALTHCHECK_DISABLED = os.getenv("RC_HEALTHCHECK_DISABLE", "0") == "1"

# Estado de conectividade (atualizado por thread em background)
_IS_ONLINE: bool = False  # True se última verificação teve sucesso
_LAST_SUCCESS_TIMESTAMP: float = 0.0  # Timestamp da última verificação bem-sucedida
_HEALTH_CHECKER_STARTED: bool = False
_STATE_LOCK = threading.Lock()  # Lock para acesso thread-safe ao estado


def _health_check_once(client: Client) -> bool:
    """
    Executa uma única verificação de saúde do Supabase.
    
    Retorna True (online) ou False (offline).
    
    Estratégia:
    1) Tenta RPC public.ping() -> 'ok'
    2) Se RPC falhar por rede, tenta fallback em tabela leve (profiles) com limit(1).
    
    Args:
        client: Cliente Supabase configurado
        
    Returns:
        bool: True se conectado, False se offline
    """
    # Tentativa 1: RPC ping
    if HEALTHCHECK_USE_RPC:
        try:
            res = exec_postgrest(client.rpc(HEALTHCHECK_RPC_NAME))
            data = getattr(res, "data", None)
            if data == "ok" or (isinstance(data, str) and data == "ok"):
                return True
        except Exception as e:
            # Não derrube o app; siga para fallback
            log.debug("Health RPC error: %s", e)

    # Tentativa 2: Fallback leve via tabela
    try:
        r = exec_postgrest(
            client.table(HEALTHCHECK_FALLBACK_TABLE)
            .select("id", count="exact")
            .limit(1)
        )
        # Se não deu erro de PGRST e retornou normally, consideramos online
        return True
    except Exception as e:
        # Só marque offline se for erro de conexão/timeouts
        log.warning("Health fallback error: %s", str(e)[:150])
        return False


def _start_health_checker() -> None:
    """
    Inicia thread daemon que verifica periodicamente a conectividade com Supabase.
    
    Sistema de 3 Estados:
    - ONLINE: Última verificação bem-sucedida E dentro do threshold (< 60s)
    - INSTÁVEL: Última verificação bem-sucedida MAS fora do threshold (> 60s)
    - OFFLINE: Verificações falhando consistentemente
    
    O health check usa RPC public.ping() para verificação leve e estável,
    com fallback para query em tabela 'profiles' caso RPC falhe.
    
    Atualiza as variáveis globais:
    - _IS_ONLINE: True se última tentativa teve sucesso
    - _LAST_SUCCESS_TIMESTAMP: Timestamp Unix da última verificação bem-sucedida
    """
    global _HEALTH_CHECKER_STARTED, _IS_ONLINE, _LAST_SUCCESS_TIMESTAMP
    
    if _HEALTH_CHECKER_STARTED:
        return
    
    _HEALTH_CHECKER_STARTED = True
    
    def _checker():
        global _IS_ONLINE, _LAST_SUCCESS_TIMESTAMP
        import time
        
        if HEALTHCHECK_DISABLED:
            log.info("Health checker desativado por RC_HEALTHCHECK_DISABLE=1")
            return
        
        log.info(
            "Health checker iniciado (intervalo: %.1fs, threshold instabilidade: %.1fs, via RPC '%s')",
            HEALTHCHECK_INTERVAL_SECONDS,
            HEALTHCHECK_UNSTABLE_THRESHOLD,
            HEALTHCHECK_RPC_NAME
        )
        
        last_bad = None
        
        while True:
            try:
                client = get_supabase()
                ok = _health_check_once(client)
                
                if ok:
                    # Sucesso: atualiza estado e timestamp
                    with _STATE_LOCK:
                        _IS_ONLINE = True
                        _LAST_SUCCESS_TIMESTAMP = time.time()
                    
                    # Reset janela de instabilidade
                    last_bad = None
                    log.debug("Health check: Supabase ONLINE")
                else:
                    # Falha: marca offline
                    with _STATE_LOCK:
                        _IS_ONLINE = False
                    
                    if last_bad is None:
                        last_bad = time.time()
                        log.warning("Health check: Supabase OFFLINE")
                    elif (time.time() - last_bad) >= HEALTHCHECK_UNSTABLE_THRESHOLD:
                        log.warning("Supabase instável há >= %.0fs", HEALTHCHECK_UNSTABLE_THRESHOLD)
                        
            except Exception as e:
                # Erro na verificação: marca offline
                with _STATE_LOCK:
                    _IS_ONLINE = False
                
                if last_bad is None:
                    last_bad = time.time()
                
                log.warning("Health check error: %s", str(e)[:150])
            
            # Aguarda próximo ciclo
            time.sleep(HEALTHCHECK_INTERVAL_SECONDS)
    
    thread = threading.Thread(target=_checker, daemon=True, name="SupabaseHealthChecker")
    thread.start()


def is_supabase_online() -> bool:
    """
    Retorna True se o Supabase está acessível, False caso contrário.
    
    DEPRECATED: Use get_supabase_state() para obter estado detalhado (Online/Instável/Offline).
    Esta função mantida para compatibilidade retroativa.
    
    Esta função consulta o estado mantido pela thread de health check em background.
    O estado é atualizado a cada ~30 segundos através de uma query minimalista.
    
    **Uso recomendado:**
    - Antes de operações críticas que dependem do Supabase (upload, queries)
    - Para habilitar/desabilitar botões de UI baseado na conectividade
    - Para mostrar indicadores visuais de status (online/offline)
    
    **Importante:**
    - A primeira verificação ocorre após alguns segundos do início da aplicação
    - Inicialmente retorna False até a primeira verificação completar
    - O health checker é iniciado automaticamente na primeira chamada desta função
    
    **Exemplo:**
    ```python
    if is_supabase_online():
        # Prosseguir com upload
        upload_para_supabase(dados)
    else:
        # Mostrar mensagem e salvar localmente
        messagebox.showwarning("Offline", "Salvando localmente...")
    ```
    
    Returns:
        bool: True se online e acessível, False se offline ou ainda não verificado
    """
    global _IS_ONLINE
    
    # Garante que o health checker foi iniciado
    if not _HEALTH_CHECKER_STARTED:
        _start_health_checker()
    
    return _IS_ONLINE


def is_really_online() -> bool:
    """
    Verifica se o Supabase está REALMENTE online e estável.
    
    Esta função implementa verificação rigorosa com threshold de instabilidade.
    
    Retorna True SOMENTE SE:
    1. Última verificação teve sucesso (_IS_ONLINE == True)
    2. E o tempo desde última verificação bem-sucedida <= INSTABILITY_THRESHOLD (60s)
    
    Se passou do threshold, considera como INSTÁVEL mesmo que _IS_ONLINE seja True.
    
    Esta é a função recomendada para usar antes de operações críticas de envio de dados.
    
    Returns:
        bool: True se online E estável, False se offline OU instável
    """
    import time
    
    # Garante que o health checker foi iniciado
    if not _HEALTH_CHECKER_STARTED:
        _start_health_checker()
    
    with _STATE_LOCK:
        is_online = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP
    
    # Se nunca teve sucesso, está offline
    if last_success == 0.0:
        return False
    
    # Se última verificação falhou, está offline
    if not is_online:
        return False
    
    # Verifica se passou do threshold de instabilidade
    time_since_success = time.time() - last_success
    
    if time_since_success > HEALTHCHECK_UNSTABLE_THRESHOLD:
        # Passou do threshold: considera instável
        log.debug(
            "Conexão INSTÁVEL: última verificação bem-sucedida há %.1fs (threshold: %.1fs)",
            time_since_success,
            HEALTHCHECK_UNSTABLE_THRESHOLD
        )
        return False
    
    # Tudo OK: online e dentro do threshold
    return True


def get_supabase_state() -> tuple[str, str]:
    """
    Retorna o estado detalhado da conexão com Supabase.
    
    Sistema de 3 Estados:
    
    1. **ONLINE** (🟢): 
       - Última verificação bem-sucedida
       - Dentro do threshold de instabilidade (< 60s)
       - Seguro para enviar dados
    
    2. **INSTÁVEL** (🟡):
       - Última verificação bem-sucedida há mais de 60s
       - OU verificações intermitentes falhando
       - NÃO recomendado enviar dados
    
    3. **OFFLINE** (🔴):
       - Verificações falhando consistentemente
       - Ou nunca teve verificação bem-sucedida
       - Envio de dados BLOQUEADO
    
    Returns:
        tuple[str, str]: (estado, descrição)
        - estado: "online", "unstable", "offline"
        - descrição: Texto descritivo para exibir na UI
    
    Exemplo:
        ```python
        state, description = get_supabase_state()
        if state == "online":
            btn_enviar.config(state="normal", text="Enviar")
        elif state == "unstable":
            btn_enviar.config(state="disabled", text="Envio suspenso - Conexão instável")
        else:  # offline
            btn_enviar.config(state="disabled", text="Envio suspenso - Offline")
        ```
    """
    import time
    
    # Garante que o health checker foi iniciado
    if not _HEALTH_CHECKER_STARTED:
        _start_health_checker()
    
    with _STATE_LOCK:
        is_online = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP
    
    # Nunca teve sucesso: OFFLINE
    if last_success == 0.0:
        return ("offline", "Aguardando primeira verificação")
    
    time_since_success = time.time() - last_success
    
    # Última verificação falhou: OFFLINE
    if not is_online:
        if time_since_success < HEALTHCHECK_UNSTABLE_THRESHOLD:
            return ("offline", f"Sem conexão (offline há {int(time_since_success)}s)")
        else:
            return ("offline", f"Sem conexão (offline há {int(time_since_success/60)}min)")
    
    # Última verificação teve sucesso: verificar threshold
    if time_since_success <= HEALTHCHECK_UNSTABLE_THRESHOLD:
        # ONLINE: dentro do threshold
        return ("online", "Conectado")
    else:
        # INSTÁVEL: passou do threshold
        mins = int(time_since_success / 60)
        return ("unstable", f"Conexão instável (último sucesso há {mins}min)")


def get_cloud_status_for_ui() -> tuple[str, str, str]:
    """
    Retorna informações formatadas para exibição na UI.
    
    Função de conveniência que retorna:
    1. Texto para exibir ("Online", "Instável", "Offline")
    2. Cor/estilo do indicador ("success", "warning", "danger")
    3. Tooltip/descrição detalhada
    
    Returns:
        tuple[str, str, str]: (texto, estilo, tooltip)
    
    Exemplo:
        ```python
        text, style, tooltip = get_cloud_status_for_ui()
        label.config(text=f"Nuvem: {text}", bootstyle=style)
        # Pode adicionar tooltip se desejar
        ```
    """
    state, description = get_supabase_state()
    
    if state == "online":
        return ("Online", "success", f"Nuvem conectada e estável. {description}")
    elif state == "unstable":
        return ("Instável", "warning", f"Conexão intermitente. {description}")
    else:  # offline
        return ("Offline", "danger", f"Sem conexão com a nuvem. {description}")


def get_supabase() -> Client:
    """
    Retorna instância SINGLETON do cliente Supabase.
    Loga 'criado' na primeira vez, 'reutilizado' no primeiro reuso.
    Nunca recria o cliente. Thread-safe.
    """
    global _SUPABASE_SINGLETON, _SINGLETON_REUSE_LOGGED
    
    # Fast path: cliente já existe (sem lock para performance)
    if _SUPABASE_SINGLETON is not None:
        # Logar apenas uma vez no primeiro reuso
        if not _SINGLETON_REUSE_LOGGED:
            with _SINGLETON_LOCK:
                if not _SINGLETON_REUSE_LOGGED:  # double-check
                    log.info("Cliente Supabase reutilizado.")
                    _SINGLETON_REUSE_LOGGED = True
        return _SUPABASE_SINGLETON
    
    # Criar cliente pela primeira vez (com lock para evitar race condition)
    with _SINGLETON_LOCK:
        # Double-check: outro thread pode ter criado enquanto esperávamos o lock
        if _SUPABASE_SINGLETON is not None:
            return _SUPABASE_SINGLETON
        
        url = os.getenv("SUPABASE_URL") or SUPABASE_URL
        key = os.getenv("SUPABASE_ANON_KEY") or SUPABASE_ANON_KEY
        
        if not url or not key:
            raise RuntimeError("Faltam SUPABASE_URL/SUPABASE_ANON_KEY no .env")
        
        options = ClientOptions(
            httpx_client=_HTTPX_CLIENT,
            postgrest_client_timeout=_HTTPX_TIMEOUT,
        )
        _SUPABASE_SINGLETON = create_client(url, key, options=options)
        log.info("Cliente Supabase SINGLETON criado.")
        
        # Inicia o health checker em background
        _start_health_checker()
        
        return _SUPABASE_SINGLETON


def bind_postgrest_auth_if_any(client: Client) -> None:
    """
    Aplica o access_token atual no PostgREST do mesmo client.
    Se não houver token, retorna silenciosamente (leituras podem degradar).
    Se falhar ao aplicar, loga WARNING mas não estoura exceção.
    """
    from data.auth_bootstrap import _get_access_token
    
    token = _get_access_token(client)
    if not token:
        log.debug("bind_postgrest_auth_if_any: sem token para aplicar")
        return
    
    try:
        client.postgrest.auth(token)
        log.info("PostgREST: token aplicado (sessão presente).")
    except Exception as e:
        log.warning("PostgREST auth falhou: %s", e)
        # Não estoura exceção - leituras podem degradar graciosamente


# Proxy preguiçoso: ao acessar qualquer atributo, resolve o client na hora
class _SupabaseLazy:
    def __getattr__(self, name: str):
        return getattr(get_supabase(), name)


supabase = _SupabaseLazy()  # <- não instancia nada na importação


def exec_postgrest(request_builder):
    """Executa request_builder.execute() com tentativas e backoff."""
    return retry_call(request_builder.execute, tries=3, backoff=0.7, jitter=0.3)

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
__all__ = [
    "supabase",
    "get_supabase",
    "baixar_pasta_zip",
    "DownloadCancelledError",
    "is_supabase_online",  # deprecated, use get_supabase_state()
    "is_really_online",
    "get_supabase_state",
    "get_cloud_status_for_ui",
]


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
