from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional, Tuple

from supabase import Client, ClientOptions, create_client

from infra.http.retry import retry_call
from infra.supabase import types as supa_types
from infra.supabase.http_client import HTTPX_CLIENT, HTTPX_TIMEOUT

log = logging.getLogger(__name__)

_SUPABASE_SINGLETON: Optional[Client] = None
_SINGLETON_REUSE_LOGGED: bool = False
_SINGLETON_LOCK = threading.Lock()

_IS_ONLINE: bool = False
_LAST_SUCCESS_TIMESTAMP: float = 0.0
_HEALTH_CHECKER_STARTED: bool = False
_STATE_LOCK = threading.Lock()


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
    if supa_types.HEALTHCHECK_USE_RPC:
        try:
            res = exec_postgrest(client.rpc(supa_types.HEALTHCHECK_RPC_NAME))
            data = getattr(res, "data", None)
            if data == "ok" or (isinstance(data, str) and data == "ok"):
                return True
        except Exception as e:
            # Fallback: se RPC não existir (404), tentar /auth/v1/health
            error_str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                log.debug("RPC 'ping' indisponível (404). Usando /auth/v1/health como fallback.")
                try:
                    # Tentar endpoint de health do GoTrue (Auth)
                    import httpx
                    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
                    health_url = f"{supabase_url}/auth/v1/health"
                    resp = httpx.get(health_url, timeout=10.0)
                    if resp.status_code == 200:
                        health_data = resp.json()
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
        exec_postgrest(
            client.table(supa_types.HEALTHCHECK_FALLBACK_TABLE)
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
        
        if supa_types.HEALTHCHECK_DISABLED:
            log.info("Health checker desativado por RC_HEALTHCHECK_DISABLE=1")
            return
        
        log.info(
            "Health checker iniciado (intervalo: %.1fs, threshold instabilidade: %.1fs, via RPC '%s')",
            supa_types.HEALTHCHECK_INTERVAL_SECONDS,
            supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD,
            supa_types.HEALTHCHECK_RPC_NAME
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
                    elif (time.time() - last_bad) >= supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD:
                        log.warning("Supabase instável há >= %.0fs", supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD)
                        
            except Exception as e:
                # Erro na verificação: marca offline
                with _STATE_LOCK:
                    _IS_ONLINE = False
                
                if last_bad is None:
                    last_bad = time.time()
                
                log.warning("Health check error: %s", str(e)[:150])
            
            # Aguarda próximo ciclo
            time.sleep(supa_types.HEALTHCHECK_INTERVAL_SECONDS)
    
    thread = threading.Thread(target=_checker, daemon=True, name="SupabaseHealthChecker")
    thread.start()


def is_supabase_online() -> bool:
    """
    Retorna True se o Supabase está acessível, False caso contrário.
    
    DEPRECATED: Use get_supabase_state() para obter estado detalhado (Online/Instável/Offline).
    Esta função mantida para compatibilidade retroativa.
    
    Esta função consulta o estado mantido pela thread de health check em background.
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
    """
    Verifica se estamos realmente ONLINE considerando limiar de instabilidade.
    Retorna True se último sucesso foi há menos de HEALTHCHECK_UNSTABLE_THRESHOLD segundos.
    """
    with _STATE_LOCK:
        current_state = _IS_ONLINE
        last_success = _LAST_SUCCESS_TIMESTAMP
    
    if not current_state:
        return False
    
    time_since_success = time.time() - last_success
    return time_since_success < supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD


def get_supabase_state() -> Tuple[str, str]:
    """
    Retorna estado detalhado da conectividade com o Supabase.
    
    Returns:
        tuple[str, str]: (estado, descrição amigável)
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


def get_cloud_status_for_ui() -> Tuple[str, str, str]:
    """
    Retorna (texto, estilo, tooltip) para exibir no UI.
    
    Exemplo de uso:
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
        
        url = os.getenv("SUPABASE_URL") or supa_types.SUPABASE_URL
        key = os.getenv("SUPABASE_ANON_KEY") or supa_types.SUPABASE_ANON_KEY
        
        if not url or not key:
            raise RuntimeError("Faltam SUPABASE_URL/SUPABASE_ANON_KEY no .env")
        
        options = ClientOptions(
            httpx_client=HTTPX_CLIENT,
            postgrest_client_timeout=HTTPX_TIMEOUT,
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


def exec_postgrest(request_builder):
    """Executa request_builder.execute() com tentativas e backoff."""
    return retry_call(request_builder.execute, tries=3, backoff=0.7, jitter=0.3)
