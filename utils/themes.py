# utils/themes.py
from __future__ import annotations
import os
import json
import logging

try:
    import ttkbootstrap as tb
except Exception:
    tb = None  # fallback se ttkbootstrap não estiver disponível

# ---------- Caminho estável para o arquivo de tema ----------
try:
    # Usa BASE_DIR se existir no projeto
    from config.paths import BASE_DIR as _BASE_DIR
except Exception:
    # Fallback: pasta acima de utils/
    from pathlib import Path
    _BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_FILE = os.path.join(str(_BASE_DIR), "config_theme.json")

# ---------- Constantes ----------
DEFAULT_THEME = "flatly"   # claro
ALT_THEME = "darkly"       # escuro

# ---------- Cache em memória ----------
_CACHED_THEME: str | None = None
_CACHED_MTIME: float | None = None


def _load_theme_from_disk() -> str:
    """Lê o tema do JSON (sem cache)."""
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme") or DEFAULT_THEME
    except Exception:
        logging.exception("themes: falha ao carregar tema do disco")
    return DEFAULT_THEME


def load_theme(force_reload: bool = False) -> str:
    """
    Retorna o tema ativo usando cache em memória.
    Se o arquivo mudar (mtime diferente) ou force_reload=True, recarrega do disco.
    """
    global _CACHED_THEME, _CACHED_MTIME
    try:
        if not force_reload and _CACHED_THEME is not None:
            mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else None
            if _CACHED_MTIME == mtime:
                return _CACHED_THEME

        theme = _load_theme_from_disk()
        _CACHED_THEME = theme
        _CACHED_MTIME = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else None
        return theme
    except Exception:
        logging.exception("themes: load_theme falhou; usando default")
        return _CACHED_THEME or DEFAULT_THEME


def save_theme(theme: str) -> None:
    """Salva o tema no JSON e atualiza o cache."""
    global _CACHED_THEME, _CACHED_MTIME
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": theme}, f, ensure_ascii=False, indent=2)
        _CACHED_THEME = theme
        _CACHED_MTIME = os.path.getmtime(CONFIG_FILE)
    except Exception:
        logging.exception("themes: falha ao salvar tema")


def toggle_theme(app=None) -> str:
    """
    Alterna entre DEFAULT_THEME e ALT_THEME e aplica imediatamente.
    Mantém compatibilidade com chamadas existentes.
    """
    atual = load_theme()
    novo = ALT_THEME if atual == DEFAULT_THEME else DEFAULT_THEME

    # Aplica no ttkbootstrap se disponível
    if tb is not None:
        try:
            tb.Style().theme_use(novo)
        except Exception:
            logging.exception("themes: falha ao aplicar tema com ttkbootstrap")

    save_theme(novo)

    # Atualiza referência no app e estilos de botões sem reler JSON
    if app is not None:
        try:
            setattr(app, "tema_atual", novo)
            apply_button_styles(app, theme=novo)
        except Exception:
            # estilização é best-effort; não deve quebrar
            logging.debug("themes: toggle_theme -> apply_button_styles silencioso")

    return novo


def apply_button_styles(app, *, theme: str | None = None) -> None:
    """
    Ajusta estilos de botões conforme o tema ativo.
    Aceita `theme=` para evitar I/O adicional (cache-friendly).
    Mantém o mapeamento existente do projeto.
    """
    atual = theme or load_theme()
    try:
        has_limpar = hasattr(app, "btn_limpar")
        has_abrir = hasattr(app, "btn_abrir")
        has_subp = hasattr(app, "btn_subpastas")

        if atual == DEFAULT_THEME:
            has_limpar and app.btn_limpar.configure(bootstyle="danger")
            has_abrir and app.btn_abrir.configure(bootstyle="primary")
            has_subp and app.btn_subpastas.configure(bootstyle="secondary")
        else:
            has_limpar and app.btn_limpar.configure(bootstyle="secondary")
            has_abrir and app.btn_abrir.configure(bootstyle="secondary")
            has_subp and app.btn_subpastas.configure(bootstyle="secondary")
    except Exception:
        # Não falhar se algum botão ainda não existir
        logging.debug("themes: apply_button_styles silencioso (componentes podem não existir ainda)")


def apply_theme(win, *, theme: str | None = None) -> None:
    """
    Aplica o tema carregado à janela principal ou toplevel.
    Aceita `theme=` para evitar re-leitura do arquivo.
    """
    if tb is None:
        return
    try:
        tb.Style().theme_use(theme or load_theme())
    except Exception:
        logging.exception("themes: apply_theme falhou")
