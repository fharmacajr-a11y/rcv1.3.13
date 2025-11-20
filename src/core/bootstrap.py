from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional


def configure_environment() -> None:
    """Apply environment defaults and load .env files."""
    os.environ.setdefault("RC_NO_LOCAL_FS", "1")

    try:
        from dotenv import load_dotenv
        from src.utils.resource_path import resource_path

        # PyInstaller bundle first, external file overrides second
        load_dotenv(resource_path(".env"), override=False)
        load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
    except Exception:
        pass


def configure_logging(*, preload: bool = False) -> Optional[logging.Logger]:
    """Bootstrap logging infrastructure and optionally return the startup logger."""
    try:
        from src.core.logs.configure import configure_logging as _configure_logging

        _configure_logging()
    except Exception:
        pass

    if preload:
        return None

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("startup")

    root = Path(__file__).resolve().parents[1]
    logger.info("APP PATH = %s", root)

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
    """Configure HiDPI awareness before any Tk root exists."""
    try:
        from src.utils.helpers import configure_hidpi_support

        configure_hidpi_support()
    except Exception:
        pass


def run_initial_healthcheck(logger: Optional[logging.Logger] = None) -> bool:
    """Run the existing connectivity check and return its status.

    DEPRECATED: Use schedule_healthcheck_after_gui() for non-blocking startup.
    Kept for compatibility with legacy code paths.
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


def schedule_healthcheck_after_gui(
    app,
    logger: Optional[logging.Logger] = None,
    delay_ms: int = 500,
) -> None:
    """Schedule health check to run after GUI is created (non-blocking startup).

    Args:
        app: Tkinter app instance with .after() method
        logger: Optional logger for diagnostics
        delay_ms: Delay in milliseconds before running check (default: 500ms)
    """

    def _run_check():
        try:
            from src.utils.network import check_internet_connectivity
            import os

            # Only check in cloud-only mode
            is_cloud_only = os.getenv("RC_NO_LOCAL_FS") == "1"
            if not is_cloud_only:
                if logger:
                    logger.debug("Not in cloud-only mode, skipping health check")
                return

            # Run check with aggressive timeout (non-blocking)
            has_internet = check_internet_connectivity(timeout=1.0)

            if logger:
                if has_internet:
                    logger.info("Background health check: Internet OK")
                else:
                    logger.warning("Background health check: No internet detected")

            # Update app footer or status if available
            try:
                if hasattr(app, "footer"):
                    status = "online" if has_internet else "offline"
                    app.footer.set_cloud(status)
            except Exception:
                pass

        except Exception as exc:
            if logger:
                logger.warning("Background health check failed: %s", exc)

    # Schedule to run after GUI is ready
    app.after(delay_ms, _run_check)


__all__ = [
    "configure_environment",
    "configure_logging",
    "configure_hidpi",
    "run_initial_healthcheck",
    "schedule_healthcheck_after_gui",
]
