from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Protocol

log = logging.getLogger(__name__)


def configure_environment() -> None:
    """Aplicar defaults de ambiente e carregar eventuais arquivos .env."""
    os.environ.setdefault("RC_NO_LOCAL_FS", "1")

    try:
        from dotenv import load_dotenv
        from src.utils.resource_path import resource_path

        # PyInstaller bundle first, external file overrides second
        load_dotenv(resource_path(".env"), override=False)
        load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
    except Exception as exc:
        log.debug("Falha ao carregar .env (opcional)", exc_info=exc)


def configure_logging(*, preload: bool = False) -> Optional[logging.Logger]:
    """Inicializa o sistema de logging e, se não estiver em preload, devolve o logger de startup."""
    try:
        from src.core.logs.configure import configure_logging as _configure_logging

        _configure_logging()
    except Exception as exc:
        log.debug("configure_logging: fallback para logging básico", exc_info=exc)

    if preload:
        return None

    # Obter nível de log da variável de ambiente RC_LOG_LEVEL
    import os

    _level_name = os.getenv("RC_LOG_LEVEL", "INFO").upper()
    _level_val = getattr(logging, _level_name, logging.INFO)

    # Configurar logging apenas se ainda não foi configurado
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=_level_val,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    else:
        # Já foi configurado (por src.core.logger), apenas garantir que o nível está correto
        logging.getLogger().setLevel(_level_val)

    logger = logging.getLogger("startup")

    root = Path(__file__).resolve().parents[1]
    logger.info("APP PATH = %s", root)
    logger.info("Logging level ativo: %s", logging.getLevelName(logging.getLogger().level))

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    try:
        from datetime import datetime

        import tzlocal  # type: ignore[import-not-found]

        tz = tzlocal.get_localzone()
        logger.info(
            "Timezone local detectado: %s (agora: %s)",
            tz,
            datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception:
        logger.info("Timezone local não detectado; usando hora do sistema.")

    return logger


def configure_hidpi() -> None:
    """Configura suporte HiDPI antes de qualquer root Tk existir."""
    try:
        from src.utils.helpers import configure_hidpi_support

        configure_hidpi_support()
    except Exception as exc:
        log.debug("configure_hidpi: ignorando erro ao aplicar HiDPI", exc_info=exc)


def run_initial_healthcheck(logger: Optional[logging.Logger] = None) -> bool:
    """Executa o health-check de conectividade legado e retorna True/False.

    Deprecated: use schedule_healthcheck_after_gui para uma experiência não bloqueante.
    """
    try:
        from src.utils.network import require_internet_or_alert

        ok = require_internet_or_alert()
        if not ok and logger is not None:
            logger.error("Internet check failed in cloud-only mode. Exiting.")
        return ok
    except Exception as exc:
        if logger is not None:
            logger.warning("Failed to check internet connectivity: %s", exc)
        return True


class AfterCapableApp(Protocol):
    """Interface mínima esperada para agendar callbacks após o bootstrap."""

    def after(self, ms: int, func: Any = None, *args: Any) -> Any:
        """Agenda callback após delay (compatível com tkinter.Tk.after)."""
        ...


def schedule_healthcheck_after_gui(
    app: AfterCapableApp,
    logger: Optional[logging.Logger] = None,
    delay_ms: int = 500,
) -> None:
    """Agenda o health-check em background após a GUI existir.

    CORREÇÃO: Executa check em threading.Thread para não bloquear a UI.
    Atualiza UI via app.after(0, ...) de forma thread-safe.
    """
    import threading

    def _run_check_in_background():
        """Executado em thread daemon para não bloquear UI."""
        try:
            from src.utils.network import check_internet_connectivity
            import os

            # Only check in cloud-only mode
            is_cloud_only = os.getenv("RC_NO_LOCAL_FS") == "1"
            if not is_cloud_only:
                if logger:
                    logger.debug("Not in cloud-only mode, skipping health check")
                return

            # Run check with aggressive timeout (now truly non-blocking)
            has_internet = check_internet_connectivity(timeout=1.0)

            if logger:
                if has_internet:
                    logger.info("Background health check: Internet OK")
                else:
                    logger.warning("Background health check: No internet detected")

            # Update app footer or status if available (thread-safe via after)
            def _update_ui():
                try:
                    if hasattr(app, "footer"):
                        status = "online" if has_internet else "offline"
                        footer = app.footer
                        # Try multiple API patterns for compatibility
                        if hasattr(footer, "set_cloud"):
                            footer.set_cloud(status)
                        elif hasattr(footer, "set_cloud_status"):
                            footer.set_cloud_status(has_internet)
                        elif hasattr(footer, "cloud_status") and isinstance(footer.cloud_status, list):
                            footer.cloud_status.append(status)
                except Exception as exc:
                    if logger:
                        logger.debug("Falha ao atualizar footer com status da nuvem", exc_info=exc)

            # Schedule UI update on main thread
            try:
                app.after(0, _update_ui)
            except Exception as exc:
                if logger:
                    logger.debug("Falha ao agendar atualização de UI: %s", exc)

        except Exception as exc:
            if logger:
                logger.warning("Background health check failed: %s", exc)

    def _start_worker():
        """Inicia worker thread (daemon) para não bloquear shutdown."""
        worker = threading.Thread(target=_run_check_in_background, daemon=True, name="HealthCheckWorker")
        worker.start()

    # Schedule worker start after GUI is ready (não bloqueia)
    app.after(delay_ms, _start_worker)


__all__ = [
    "configure_environment",
    "configure_logging",
    "configure_hidpi",
    "run_initial_healthcheck",
    "schedule_healthcheck_after_gui",
]
