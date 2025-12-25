from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Final, TypeVar

from supabase import Client, ClientOptions, create_client  # type: ignore[import-untyped]

from infra.http.retry import retry_call
from infra.supabase import types as supa_types
from infra.supabase.http_client import HTTPX_CLIENT, HTTPX_TIMEOUT_LIGHT

# Type variable for PostgREST responses
T = TypeVar("T")

# Type aliases
HealthState = tuple[str, str]  # (estado, descrição)
UiStatusTuple = tuple[str, str, str]  # (texto, estilo, tooltip)

log = logging.getLogger(__name__)

# Singleton state
_SUPABASE_SINGLETON: Client | None = None
_SINGLETON_REUSE_LOGGED: bool = False
_SINGLETON_LOCK: Final[threading.Lock] = threading.Lock()

# Health check state
_IS_ONLINE: bool = False
_LAST_SUCCESS_TIMESTAMP: float = 0.0
_HEALTH_CHECKER_STARTED: bool = False
_STATE_LOCK: Final[threading.Lock] = threading.Lock()


def _health_check_once(client: Client) -> bool:
    """Executa uma única verificação de saúde do Supabase.

    Estratégia:
    1) Tenta RPC public.ping() -> 'ok'
    2) Se RPC falhar (404), tenta fallback em /auth/v1/health
    3) Como último recurso, tenta query em tabela de fallback

    Args:
        client: Cliente Supabase configurado

    Returns:
        True se conectado e responsivo, False se offline ou inacessível
    """
    # Tentativa 1: RPC ping
    if supa_types.HEALTHCHECK_USE_RPC:
        try:
            res = exec_postgrest(client.rpc(supa_types.HEALTHCHECK_RPC_NAME))
            data: Any = getattr(res, "data", None)
            if data == "ok" or (isinstance(data, str) and data == "ok"):
                return True
        except Exception as e:
            # Fallback: se RPC não existir (404), tentar /auth/v1/health
            error_str: str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                log.debug("RPC 'ping' indisponível (404). Usando /auth/v1/health como fallback.")
                try:
                    # Tentar endpoint de health do GoTrue (Auth)
                    import httpx

                    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
                    health_url: str = f"{supabase_url}/auth/v1/health"
                    resp: httpx.Response = httpx.get(health_url, timeout=10.0)
                    if resp.status_code == 200:
                        health_data: dict[str, Any] = resp.json()
                        # GoTrue retorna {"version": "...", "name": "GoTrue", ...}
                        if health_data.get("version") or health_data.get("name") == "GoTrue":
                            log.debug("Health check OK via /auth/v1/health")
                            return True
                except Exception as health_error:
                    log.debug("Health fallback /auth/v1/health error: %s", health_error)
            else:
                # Outro tipo de erro RPC, apenas logar
                log.debug("Health RPC error: %s", e)

    # Tentativa 2: Fallback leve via tabela
    try:
        exec_postgrest(client.table(supa_types.HEALTHCHECK_FALLBACK_TABLE).select("id", count="exact").limit(1))
        # Se não deu erro de PGRST e retornou normally, consideramos online
        return True
    except Exception as e:
        # Só marque offline se for erro de conexão/timeouts
        # Silencia em testes para evitar spam
        if os.getenv("PYTEST_CURRENT_TEST") is None:
            log.warning("Health fallback error: %s", str(e)[:150])
        return False


def _start_health_checker() -> None:
    """Inicia thread daemon que verifica periodicamente a conectividade com Supabase.

    Sistema de 3 Estados:
    - ONLINE: Última verificação bem-sucedida E dentro do threshold (< 60s)
    - INSTÁVEL: Última verificação bem-sucedida MAS fora do threshold (> 60s)
    - OFFLINE: Verificações falhando consistentemente

    Estratégia de Verificação:
    1. RPC public.ping() - verificação leve preferencial
    2. /auth/v1/health - fallback se RPC retornar 404
    3. Query em tabela de fallback - último recurso

    Note:
        Thread é daemon (não bloqueia shutdown do app)
        Atualiza variáveis globais _IS_ONLINE e _LAST_SUCCESS_TIMESTAMP
        Configurável via variáveis de ambiente (HEALTHCHECK_INTERVAL_SECONDS, etc.)

    OFFLINE-SUPABASE-UX-002: Em cloud-only sem internet, não inicia o checker
        para evitar spam de warnings no console.
    """
    global _HEALTH_CHECKER_STARTED

    if _HEALTH_CHECKER_STARTED:
        return

    # OFFLINE-SUPABASE-UX-002: Não iniciar health checker se cloud-only E offline
    # (para evitar spam de warnings quando sem internet)
    is_cloud_only = os.getenv("RC_NO_LOCAL_FS") == "1"
    is_testing = os.getenv("RC_TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST") is not None

    if is_cloud_only and not is_testing:
        try:
            from src.utils.network import check_internet_connectivity

            if not check_internet_connectivity(timeout=1.0):
                log.info("Cloud-only offline: health checker não iniciado para evitar ruído no console.")
                return
        except Exception as exc:
            log.debug("Erro ao verificar internet para health checker: %s", exc)

    _HEALTH_CHECKER_STARTED = True

    def _checker():
        global _IS_ONLINE, _LAST_SUCCESS_TIMESTAMP

        if supa_types.HEALTHCHECK_DISABLED:
            log.info("Health checker desativado por RC_HEALTHCHECK_DISABLE=1")
            return

        log.info(
            "Health checker iniciado (intervalo: %.1fs, threshold instabilidade: %.1fs, via RPC '%s')",
            supa_types.HEALTHCHECK_INTERVAL_SECONDS,
            supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD,
            supa_types.HEALTHCHECK_RPC_NAME,
        )

        last_bad: float | None = None
        unstable_warned: bool = False

        while True:
            try:
                client: Client = get_supabase()
                ok: bool = _health_check_once(client)

                if ok:
                    # Sucesso: atualiza estado e timestamp
                    with _STATE_LOCK:
                        _IS_ONLINE = True
                        _LAST_SUCCESS_TIMESTAMP = time.time()

                    # Reset janela de instabilidade
                    last_bad = None
                    unstable_warned = False
                    log.debug("Health check: Supabase ONLINE")
                else:
                    # Falha: marca offline
                    with _STATE_LOCK:
                        _IS_ONLINE = False

                    if last_bad is None:
                        last_bad = time.time()
                        # Silencia em testes para evitar spam
                        if os.getenv("PYTEST_CURRENT_TEST") is None:
                            log.warning("Health check: Supabase OFFLINE")
                    elif not unstable_warned and (time.time() - last_bad) >= supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD:
                        # Emitir warning de instabilidade apenas 1 vez por sequência offline
                        unstable_warned = True
                        # Silencia em testes para evitar spam
                        if os.getenv("PYTEST_CURRENT_TEST") is None:
                            log.warning("Supabase instável há >= %.0fs", supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD)

            except StopIteration:
                # Para testes que usam generator em time.sleep, sair da thread de forma limpa
                log.debug("SupabaseHealthChecker: StopIteration recebida, encerrando thread")
                break
            except Exception as e:
                # Erro na verificação: marca offline
                with _STATE_LOCK:
                    _IS_ONLINE = False

                if last_bad is None:
                    last_bad = time.time()

                log.warning("Health check error: %s", str(e)[:150])

            # Aguarda próximo ciclo
            try:
                time.sleep(supa_types.HEALTHCHECK_INTERVAL_SECONDS)
            except StopIteration:
                # Para testes que patcham time.sleep com generator
                log.debug("SupabaseHealthChecker: StopIteration em sleep, encerrando thread")
                break

    thread = threading.Thread(target=_checker, daemon=True, name="SupabaseHealthChecker")
    thread.start()


def is_supabase_online() -> bool:
    """Retorna True se o Supabase está acessível, False caso contrário.

    Returns:
        True se conectado e dentro do threshold de estabilidade, False caso contrário

    Warning:
        DEPRECATED: Use get_supabase_state() para obter estado detalhado (Online/Instável/Offline).
        Mantida apenas para compatibilidade retroativa.

    Note:
        Consulta estado mantido pela thread de health check em background.
        Considera UNSTABLE (threshold excedido) como offline.
    """
    with _STATE_LOCK:
        current_state = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP

    if not current_state:
        return False

    time_since_success = time.time() - last_success
    if time_since_success > supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD:
        return False

    return True


def is_really_online() -> bool:
    """Verifica se estamos realmente ONLINE considerando limiar de instabilidade.

    Returns:
        True se último sucesso foi há menos de HEALTHCHECK_UNSTABLE_THRESHOLD segundos

    Note:
        Diferente de is_supabase_online(), esta função usa exatamente o threshold
        configurado sem arredondamentos ou ajustes.
    """
    with _STATE_LOCK:
        current_state = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP

    if not current_state:
        return False

    time_since_success = time.time() - last_success
    return time_since_success < supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD


def get_supabase_state() -> HealthState:
    """Retorna estado detalhado da conectividade com o Supabase.

    Returns:
        Tupla (estado, descrição) onde estado pode ser:
        - "online": Conectado e estável
        - "unstable": Última resposta excedeu threshold
        - "offline": Sem resposta recente

    Example:
        >>> state, desc = get_supabase_state()
        >>> if state == "online":
        ...     print("Tudo OK")
    """
    with _STATE_LOCK:
        current_state = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP

    if not current_state:
        return (
            "offline",
            "Sem resposta recente do Supabase. Verifique sua conexão.",
        )

    time_since_success = time.time() - last_success
    if time_since_success > supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD:
        return (
            "unstable",
            "Última resposta bem-sucedida excedeu o limiar configurado.",
        )

    return (
        "online",
        "Conectado ao Supabase e dentro do limiar de estabilidade.",
    )


def get_cloud_status_for_ui() -> UiStatusTuple:
    """Retorna (texto, estilo, tooltip) para exibir no UI.

    Returns:
        Tupla (texto, estilo, tooltip) onde:
        - texto: "Online", "Instável" ou "Offline"
        - estilo: "success", "warning" ou "danger" (Bootstrap styles)
        - tooltip: Descrição detalhada do estado

    Example:
        >>> text, style, tooltip = get_cloud_status_for_ui()
        >>> label.config(text=f"Nuvem: {text}", bootstyle=style)
    """
    state: str
    description: str
    state, description = get_supabase_state()

    if state == "online":
        return ("Online", "success", f"Nuvem conectada e estável. {description}")
    elif state == "unstable":
        return ("Instável", "warning", f"Conexão intermitente. {description}")
    else:  # offline
        return ("Offline", "danger", f"Sem conexão com a nuvem. {description}")


def get_supabase() -> Client:
    """Retorna instância SINGLETON do cliente Supabase.

    Returns:
        Cliente Supabase configurado e pronto para uso

    Raises:
        RuntimeError: Se SUPABASE_URL ou SUPABASE_ANON_KEY não estiverem configurados

    Note:
        - Thread-safe (usa double-checked locking pattern)
        - Loga 'criado' na primeira vez, 'reutilizado' no primeiro reuso
        - Nunca recria o cliente (singleton permanente)
        - Inicia health checker em background na primeira criação
        - Usa HTTPX_CLIENT customizado com retry e timeout configurados
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

        url_from_env = os.getenv("SUPABASE_URL")
        url: str = url_from_env or supa_types.SUPABASE_URL or ""

        # CORREÇÃO: Suportar SUPABASE_KEY como alias de SUPABASE_ANON_KEY
        key_from_env = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        key: str = key_from_env or supa_types.SUPABASE_ANON_KEY or ""

        if not url or not key:
            raise RuntimeError("Faltam SUPABASE_URL e SUPABASE_ANON_KEY (ou SUPABASE_KEY) no .env")

        options: ClientOptions = ClientOptions(
            httpx_client=HTTPX_CLIENT,
            postgrest_client_timeout=HTTPX_TIMEOUT_LIGHT,
        )
        _SUPABASE_SINGLETON = create_client(url, key, options=options)
        log.info("Cliente Supabase SINGLETON criado.")

        # Inicia o health checker em background
        _start_health_checker()

        return _SUPABASE_SINGLETON


class _SupabaseLazy:
    def __getattr__(self, name: str):
        return getattr(get_supabase(), name)


supabase = _SupabaseLazy()  # <- não instancia nada na importação


def exec_postgrest(request_builder: Any) -> Any:
    """Executa request_builder.execute() com tentativas e backoff.

    Args:
        request_builder: PostgREST request builder (from .table(), .rpc(), etc.)

    Returns:
        APIResponse object with .data, .error, .count attributes

    Raises:
        Exception: Se todas as 3 tentativas falharem (propagado do retry_call)

    Note:
        - Usa retry_call com 3 tentativas
        - Backoff exponencial de 0.7s entre tentativas
        - Jitter de 0.3s para evitar thundering herd
        - Type hint Any devido à API dinâmica do PostgREST
    """
    return retry_call(request_builder.execute, tries=3, backoff=0.7, jitter=0.3)
