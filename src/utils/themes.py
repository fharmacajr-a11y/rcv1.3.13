# -*- coding: utf-8 -*-
# utils/themes.py
"""DEPRECATED: Sistema legado de temas (ttkbootstrap com 14 temas).

⚠️ MIGRAÇÃO COMPLETA: ttkbootstrap foi REMOVIDO do projeto (18/01/2026).
Este módulo é mantido apenas para compatibilidade de assinatura com código legado.
Todas as funcionalidades retornam None ou valores default sem executar código ttkbootstrap.

NOVO CÓDIGO: Use src/ui/theme_manager.py (CustomTkinter com light/dark).

IMPORTANTE:
- ❌ Não adicionar novas funcionalidades aqui
- ❌ Não usar em novos componentes
- ✅ Migrar todas as chamadas para src.ui.theme_manager
- ✅ Este arquivo será removido em versão futura
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

# ttkbootstrap foi REMOVIDO - código legado mantido apenas para compatibilidade
tb = None
TtkBootstrapStyle = None

# ---------- Modo cloud-only (nao tocar no disco) ----------
NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"
ENV_DEFAULT_THEME = (os.getenv("RC_DEFAULT_THEME") or "").strip()  # opcional

# ---------- Caminho estavel para o arquivo de tema (usado so se NO_FS for False) ----------
if not NO_FS:
    try:
        # Usa BASE_DIR se existir no projeto
        from src.config.paths import BASE_DIR as _BASE_DIR  # type: ignore
    except Exception:
        # Fallback: pasta acima de utils/
        from pathlib import Path

        _BASE_DIR = Path(__file__).resolve().parents[1]
    CONFIG_FILE = os.path.join(str(_BASE_DIR), "config_theme.json")
else:
    CONFIG_FILE = None  # nao usamos arquivo no modo cloud-only

# ---------- Constantes ----------
DEFAULT_THEME = ENV_DEFAULT_THEME or "flatly"  # claro
ALT_THEME = "darkly"  # escuro

# ---------- Cache em memoria ----------
_CACHED_THEME: str | None = None
_CACHED_MTIME: float | None = None


def get_tb_style_safe(widget: Any = None, theme: str | None = None) -> Any:
    """Retorna ttkbootstrap.Style SEM criar root implícita.

    CODEC: Helper seguro CORRETO conforme especificação final.

    IMPORTANTE: tb.Style(widget) NÃO é API válida! Style.__init__ recebe "theme" string.

    Regras corretas:
    1) Se widget tiver atributo .style (ttkbootstrap.Window): usar widget.style
    2) Senão: usar Style.get_instance() (singleton)
    3) Só criar Style() se tk._default_root já existir (nunca criar Tk fantasma)
    4) Se theme fornecido: aplicar style.theme_use(theme)

    Args:
        widget: Widget/janela (ttkbootstrap.Window) que pode ter .style
        theme: Tema opcional para aplicar

    Returns:
        Instância de Style ou None se não puder criar com segurança
    """
    if tb is None or TtkBootstrapStyle is None:
        return None

    # Regra 1: Se widget tem .style (ttkbootstrap.Window), reutilizar
    if widget is not None and hasattr(widget, "style"):
        style = widget.style
        if theme and style:
            try:
                style.theme_use(theme)
            except Exception:
                logging.exception("Falha ao aplicar theme via widget.style")
        return style

    # Regra 2: Tentar singleton Style.get_instance()
    try:
        if hasattr(TtkBootstrapStyle, "get_instance"):
            style = TtkBootstrapStyle.get_instance()
            if style is not None:
                if theme:
                    try:
                        style.theme_use(theme)
                    except Exception:
                        logging.exception("Falha ao aplicar theme via get_instance")
                return style
    except Exception:
        pass

    # Regra 3: Só criar Style() se root já existir
    try:
        import tkinter as tk

        if tk._default_root is None:  # type: ignore[attr-defined]
            return None  # NÃO criar Tk fantasma

        # Root existe: seguro criar Style
        # CORRETO: Style(theme=theme) pois __init__ recebe theme como string
        if theme:
            style = TtkBootstrapStyle(theme=theme)
        else:
            style = TtkBootstrapStyle()
        return style
    except Exception:
        logging.exception("Falha ao criar Style com root existente")
        return None


def _load_theme_from_disk() -> str:
    """Le o tema do JSON (sem cache). Usado apenas quando NO_FS=False."""
    if NO_FS:
        # Seguranca adicional: nunca deve ser chamado nesse modo
        return DEFAULT_THEME
    try:
        if CONFIG_FILE and os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme") or DEFAULT_THEME
    except Exception:
        logging.exception("themes: falha ao carregar tema do disco")
    return DEFAULT_THEME


def load_theme(force_reload: bool = False) -> str:
    """Retorna o tema ativo usando cache, variaveis de ambiente e config em disco conforme NO_FS e safe-mode."""
    global _CACHED_THEME, _CACHED_MTIME

    # Check for safe-mode (returns default theme)
    try:
        from src.cli import get_args

        if get_args().safe_mode:
            return "default"  # Standard theme
    except Exception:
        logging.debug("themes: CLI indisponivel para verificar safe_mode", exc_info=True)

    # Modo cloud-only: nunca toca no disco
    if NO_FS:
        if _CACHED_THEME is not None and not force_reload:
            return _CACHED_THEME
        # Prioriza RC_DEFAULT_THEME se fornecido, senao mantem ultimo conhecido ou DEFAULT_THEME
        _CACHED_THEME = _CACHED_THEME or DEFAULT_THEME
        _CACHED_MTIME = None
        return _CACHED_THEME

    # Modo normal: com arquivo
    try:
        if not force_reload and _CACHED_THEME is not None:
            mtime = os.path.getmtime(CONFIG_FILE) if (CONFIG_FILE and os.path.exists(CONFIG_FILE)) else None
            if _CACHED_MTIME == mtime:
                return _CACHED_THEME

        theme = _load_theme_from_disk()
        _CACHED_THEME = theme
        _CACHED_MTIME = os.path.getmtime(CONFIG_FILE) if (CONFIG_FILE and os.path.exists(CONFIG_FILE)) else None
        return theme
    except Exception:
        logging.exception("themes: load_theme falhou; usando default")
        return _CACHED_THEME or DEFAULT_THEME


def save_theme(theme: str) -> None:
    """Atualiza o tema ativo; persiste em arquivo se NO_FS=False, caso contrario apenas cache."""
    global _CACHED_THEME, _CACHED_MTIME

    # Sempre atualiza o cache
    _CACHED_THEME = theme or DEFAULT_THEME

    if NO_FS:
        # Nao persiste no disco
        _CACHED_MTIME = None
        return

    try:
        if CONFIG_FILE:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"theme": _CACHED_THEME}, f, ensure_ascii=False, indent=2)
            _CACHED_MTIME = os.path.getmtime(CONFIG_FILE)
    except Exception:
        logging.exception("themes: falha ao salvar tema")


def toggle_theme(app: Any | None = None) -> str:
    """Alterna entre DEFAULT_THEME e ALT_THEME, aplica no ttkbootstrap e atualiza cache/arquivo."""
    atual = load_theme()
    novo = ALT_THEME if atual == DEFAULT_THEME else DEFAULT_THEME

    # Aplica no ttkbootstrap se disponivel (usando helper seguro)
    get_tb_style_safe(widget=app, theme=novo)
    # Se style foi obtido, o theme já foi aplicado pelo helper
    # Senão, continua sem problema (modo headless ou CTk-only)

    save_theme(novo)

    # Atualiza referencia no app e estilos de botoes sem reler JSON
    if app is not None:
        try:
            setattr(app, "tema_atual", novo)
            apply_button_styles(app, theme=novo)
        except Exception:
            # estilizacao e best-effort; nao deve quebrar
            logging.debug("themes: toggle_theme -> apply_button_styles silencioso")

    return novo


def apply_button_styles(app: Any, *, theme: str | None = None) -> None:
    """Configura estilos de botoes do app com base no tema atual ou fornecido."""
    atual = theme or load_theme()
    try:
        # Esses atributos podem nao existir dependendo da tela/versao:
        has_limpar = hasattr(app, "btn_limpar")
        has_abrir = hasattr(app, "btn_abrir")
        has_subp = hasattr(app, "btn_subpastas")

        if atual == DEFAULT_THEME:
            _ = has_limpar and app.btn_limpar.configure(bootstyle="danger")
            _ = has_abrir and app.btn_abrir.configure(bootstyle="primary")
            _ = has_subp and app.btn_subpastas.configure(bootstyle="secondary")
        else:
            _ = has_limpar and app.btn_limpar.configure(bootstyle="secondary")
            _ = has_abrir and app.btn_abrir.configure(bootstyle="secondary")
            _ = has_subp and app.btn_subpastas.configure(bootstyle="secondary")
    except Exception:
        # Nao falhar se algum botao ainda nao existir
        logging.debug("themes: apply_button_styles silencioso (componentes podem nao existir ainda)")


def apply_combobox_style(style: Any) -> None:
    """
    Padroniza o fundo dos Combobox para acompanhar o fundo dos Entry.

    ttkbootstrap/flatly usa fieldbackground cinza para readonly por padrão; aqui
    normalizamos para o mesmo fundo dos Entry, mantendo consistência visual.

    Args:
        style: Instância de estilo já configurada (legado - não usado).
               IMPORTANTE: Deve ser a MESMA instância usada pelo app.
    """
    if tb is None or style is None:
        return

    logger = logging.getLogger(__name__)

    try:
        # Obter cor de fundo do Entry (nossa referência)
        entry_bg = (
            style.lookup("TEntry", "fieldbackground", ("!disabled",))
            or style.lookup("TEntry", "fieldbackground")
            or style.lookup("TEntry", "background", ("!disabled",))
            or style.lookup("TEntry", "background")
        )

        # Se ainda estiver vazio, usar branco como fallback seguro
        if not entry_bg or entry_bg == "":
            entry_bg = "#ffffff"
            logger.debug("[COMBOBOX STYLE] Entry bg veio vazio, usando fallback: %s", entry_bg)

        if entry_bg:
            # Configurar padrão
            style.configure("TCombobox", fieldbackground=entry_bg)

            # Map COMPLETO de estados para sobrescrever qualquer cinza do tema
            style.map(
                "TCombobox",
                fieldbackground=[
                    ("readonly", entry_bg),  # Estado readonly (principal problema)
                    ("!disabled", entry_bg),  # Estado normal habilitado
                    ("disabled", "#e9ecef"),  # Cinza apenas se disabled
                    ("focus", entry_bg),  # Quando focado
                    ("active", entry_bg),  # Quando ativo
                ],
            )
            logger.debug("[COMBOBOX STYLE] Aplicado com sucesso: TCombobox -> %s", entry_bg)
        else:
            logger.warning("[COMBOBOX STYLE] Não foi possível detectar cor de fundo do Entry")
    except Exception as exc:
        logger.warning("[COMBOBOX STYLE] Falha ao aplicar estilo: %s", exc, exc_info=True)


def apply_theme(win: Any, *, theme: str | None = None) -> None:
    """Aplica o tema carregado a uma janela/toplevel usando ttkbootstrap, se disponivel."""
    if tb is None:
        return

    # CODEC: Usar helper seguro (theme já é aplicado internamente)
    get_tb_style_safe(widget=win, theme=theme or load_theme())
