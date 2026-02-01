# -*- coding: utf-8 -*-
"""
State Helpers para Main Window.

Funções puras para cálculos de estado, tema/modo, título e navegação
sem dependências de Tkinter.

MICROFASE 24+: Migrando de "temas ttkbootstrap" para "modos CTk".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


# ============================================================================
# TEMA / MODO (MICROFASE 24+: CTk modes)
# ============================================================================

ThemeMode = Literal["light", "dark"]


@dataclass(frozen=True)
class ThemeConfig:
    """Configuração de tema/modo para aplicação."""

    name: str  # modo: "light"/"dark" ou tema legado
    should_persist: bool
    is_change: bool


def migrate_legacy_theme_to_mode(theme_name: str) -> ThemeMode:
    """Migra nome de tema legado (ttkbootstrap) para modo CTk.

    Args:
        theme_name: Nome do tema ttkbootstrap (ex: "darkly", "flatly")

    Returns:
        Modo CTk equivalente ("light" ou "dark")

    Examples:
        >>> migrate_legacy_theme_to_mode("darkly")
        'dark'

        >>> migrate_legacy_theme_to_mode("flatly")
        'light'

        >>> migrate_legacy_theme_to_mode("superhero")
        'dark'
    """
    normalized = theme_name.lower().strip()

    # Temas escuros -> dark
    dark_themes = {"darkly", "cyborg", "superhero", "vapor", "solar"}
    if normalized in dark_themes:
        return "dark"

    # Qualquer outro tema -> light (padrão seguro)
    return "light"


def compute_theme_config(
    requested_theme: str | None,
    current_theme: str | None,
    *,
    allow_persistence: bool = True,
) -> ThemeConfig | None:
    """Calcula configuração de tema/modo com base no solicitado e atual.

    Args:
        requested_theme: Tema/modo solicitado pelo usuário ou config
        current_theme: Tema/modo atualmente ativo
        allow_persistence: Se deve persistir em disco (False em NO_FS mode)

    Returns:
        ThemeConfig ou None se não houver mudança necessária

    Examples:
        >>> compute_theme_config("dark", None)
        ThemeConfig(name='dark', should_persist=True, is_change=True)

        >>> compute_theme_config("light", "light")
        None

        >>> compute_theme_config("dark", "light", allow_persistence=False)
        ThemeConfig(name='dark', should_persist=False, is_change=True)
    """
    # Normalizar inputs
    req = (requested_theme or "").strip()
    cur = (current_theme or "").strip()

    # Se não há solicitado ou é igual ao atual, não fazer nada
    if not req or req == cur:
        return None

    return ThemeConfig(
        name=req,
        should_persist=allow_persistence,
        is_change=(cur != ""),  # True se já havia um tema/modo (mudança)
    )


def validate_theme_mode(
    mode: str,
    *,
    fallback: ThemeMode = "light",
) -> ThemeMode:
    """Valida e normaliza modo de tema.

    Args:
        mode: Modo a validar (pode ser modo CTk ou tema legado)
        fallback: Modo padrão se o solicitado não for válido

    Returns:
        Modo válido: "light" ou "dark"

    Examples:
        >>> validate_theme_mode("dark")
        'dark'

        >>> validate_theme_mode("darkly")  # tema legado
        'dark'

        >>> validate_theme_mode("invalid")
        'light'

        >>> validate_theme_mode("", fallback="dark")
        'dark'
    """
    normalized = (mode or "").strip().lower()

    if not normalized:
        return fallback

    # Modos CTk válidos
    if normalized in ("light", "dark"):
        return normalized  # type: ignore[return-value]

    # Fallback para "system" legado
    if normalized == "system":
        return "light"

    # Migrar tema legado
    return migrate_legacy_theme_to_mode(normalized)


def validate_theme_name(
    theme_name: str,
    available_themes: list[str],
    *,
    fallback: str = "flatly",
) -> str:
    """Valida e normaliza nome de tema contra lista de disponíveis.

    DEPRECATED: Use validate_theme_mode() para CTk.
    Mantido apenas para compatibilidade com código legado ttkbootstrap.

    Args:
        theme_name: Nome do tema a validar
        available_themes: Lista de temas disponíveis
        fallback: Tema padrão se o solicitado não existir

    Returns:
        Nome de tema válido

    Examples:
        >>> validate_theme_name("darkly", ["flatly", "darkly", "superhero"])
        'darkly'

        >>> validate_theme_name("invalid", ["flatly", "darkly"])
        'flatly'

        >>> validate_theme_name("", ["flatly"], fallback="superhero")
        'superhero'
    """
    normalized = (theme_name or "").strip().lower()

    if not normalized:
        return fallback

    # Case-insensitive match
    available_lower = {t.lower(): t for t in available_themes}

    return available_lower.get(normalized, fallback)


# ============================================================================
# TÍTULO DA JANELA
# ============================================================================


def build_app_title(
    base_title: str,
    version: str,
    *,
    profile_name: str | None = None,
    separator: str = " - ",
) -> str:
    """Constrói título da janela principal com versão e perfil opcional.

    Args:
        base_title: Título base da aplicação (ex: "Regularize Consultoria")
        version: Versão da aplicação (ex: "v1.3.28")
        profile_name: Nome do perfil/usuário logado (opcional)
        separator: Separador entre partes do título

    Returns:
        Título formatado

    Examples:
        >>> build_app_title("RC Gestor", "v1.3.28")
        'RC Gestor - v1.3.28'

        >>> build_app_title("RC Gestor", "v1.3.28", profile_name="Admin")
        'RC Gestor - v1.3.28 (Admin)'

        >>> build_app_title("RC Gestor", "v1.3.28", separator=" | ")
        'RC Gestor | v1.3.28'
    """
    base = f"{base_title}{separator}{version}"

    if profile_name and profile_name.strip():
        return f"{base} ({profile_name.strip()})"

    return base


def format_version_string(version: str, *, prefix: str = "v") -> str:
    """Formata string de versão com prefixo opcional.

    Args:
        version: Versão sem prefixo (ex: "1.3.28")
        prefix: Prefixo a adicionar (default: "v")

    Returns:
        Versão formatada

    Examples:
        >>> format_version_string("1.3.28")
        'v1.3.28'

        >>> format_version_string("v1.3.28")
        'v1.3.28'

        >>> format_version_string("1.3.28", prefix="version ")
        'version 1.3.28'
    """
    v = version.strip()

    if not v:
        return prefix.strip()

    # Remove prefixo existente se houver
    if v.lower().startswith(prefix.lower()):
        return v

    return f"{prefix}{v}"


# ============================================================================
# NAVEGAÇÃO / SEÇÕES
# ============================================================================


class MainWindowSection(str, Enum):
    """Seções da janela principal."""

    HUB = "hub"
    CLIENTES = "clientes"
    CASHFLOW = "cashflow"
    LIXEIRA = "lixeira"


def resolve_initial_section(
    *,
    has_session: bool,
    default_section: MainWindowSection = MainWindowSection.HUB,
) -> MainWindowSection:
    """Resolve qual seção abrir inicialmente com base no estado da sessão.

    Args:
        has_session: Se há sessão/usuário autenticado
        default_section: Seção padrão para usuários logados

    Returns:
        Seção a abrir

    Examples:
        >>> resolve_initial_section(has_session=True)
        <MainWindowSection.HUB: 'hub'>

        >>> resolve_initial_section(has_session=False)
        <MainWindowSection.HUB: 'hub'>

        >>> resolve_initial_section(has_session=True, default_section=MainWindowSection.CLIENTES)
        <MainWindowSection.CLIENTES: 'clientes'>
    """
    # Atualmente sempre retorna o default, mas permite expansão futura
    # para lógica como "se sem sessão, redirecionar para login"
    if not has_session:
        # Futura implementação: pode redirecionar para tela de login
        return default_section

    return default_section


def build_section_navigation_map(
    sections: list[MainWindowSection],
) -> dict[str, MainWindowSection]:
    """Constrói mapa de navegação entre seções.

    Args:
        sections: Lista de seções disponíveis

    Returns:
        Dicionário nome → seção

    Examples:
        >>> sections = [MainWindowSection.HUB, MainWindowSection.CLIENTES]
        >>> nav_map = build_section_navigation_map(sections)
        >>> nav_map["hub"]
        <MainWindowSection.HUB: 'hub'>
    """
    return {section.value: section for section in sections}


# ============================================================================
# ESTADO DE CONECTIVIDADE
# ============================================================================


@dataclass
class ConnectivityState:
    """Estado de conectividade da aplicação."""

    is_online: bool
    offline_alerted: bool


def compute_connectivity_state(
    current_online: bool,
    new_online: bool,
    already_alerted: bool,
) -> ConnectivityState:
    """Calcula novo estado de conectividade com base em mudança.

    Args:
        current_online: Estado atual (online/offline)
        new_online: Novo estado detectado
        already_alerted: Se já foi emitido alerta de offline

    Returns:
        Novo estado de conectividade

    Examples:
        >>> compute_connectivity_state(True, False, False)
        ConnectivityState(is_online=False, offline_alerted=False)

        >>> compute_connectivity_state(False, True, True)
        ConnectivityState(is_online=True, offline_alerted=False)

        >>> compute_connectivity_state(True, True, False)
        ConnectivityState(is_online=True, offline_alerted=False)
    """
    # Se voltou online, resetar flag de alerta
    if new_online and not current_online:
        return ConnectivityState(is_online=True, offline_alerted=False)

    # Se continua online ou mudou para offline
    return ConnectivityState(is_online=new_online, offline_alerted=already_alerted)


def should_show_offline_alert(
    current_online: bool,
    new_online: bool,
    already_alerted: bool,
) -> bool:
    """Determina se deve mostrar alerta de offline.

    Args:
        current_online: Estado atual
        new_online: Novo estado
        already_alerted: Se já foi alertado

    Returns:
        True se deve mostrar alerta

    Examples:
        >>> should_show_offline_alert(True, False, False)
        True

        >>> should_show_offline_alert(True, False, True)
        False

        >>> should_show_offline_alert(False, False, False)
        False

        >>> should_show_offline_alert(False, True, True)
        False
    """
    # Mostrar alerta apenas na transição online → offline
    # e somente se ainda não foi alertado
    return current_online and not new_online and not already_alerted


# ============================================================================
# STATUS DISPLAY
# ============================================================================


def format_status_text(
    base_text: str,
    is_online: bool,
    *,
    online_suffix: str = "",
    offline_suffix: str = " (offline)",
) -> str:
    """Formata texto de status com sufixo de conectividade.

    Args:
        base_text: Texto base do status
        is_online: Se está online
        online_suffix: Sufixo quando online
        offline_suffix: Sufixo quando offline

    Returns:
        Texto formatado

    Examples:
        >>> format_status_text("Supabase", True)
        'Supabase'

        >>> format_status_text("Supabase", False)
        'Supabase (offline)'

        >>> format_status_text("DB", False, offline_suffix=" [sem conexão]")
        'DB [sem conexão]'
    """
    suffix = online_suffix if is_online else offline_suffix
    return f"{base_text}{suffix}"


def parse_clients_count_display(count_text: str) -> int:
    """Extrai número de clientes de texto formatado.

    Args:
        count_text: Texto como "150 clientes" ou "1 cliente"

    Returns:
        Número de clientes ou 0 se parsing falhar

    Examples:
        >>> parse_clients_count_display("150 clientes")
        150

        >>> parse_clients_count_display("1 cliente")
        1

        >>> parse_clients_count_display("0 clientes")
        0

        >>> parse_clients_count_display("invalid")
        0
    """
    try:
        parts = count_text.strip().split()
        if parts:
            return int(parts[0])
    except (ValueError, IndexError):
        pass

    return 0


def format_clients_count_display(count: int) -> str:
    """Formata número de clientes para exibição.

    Args:
        count: Número de clientes

    Returns:
        Texto formatado

    Examples:
        >>> format_clients_count_display(150)
        '150 clientes'

        >>> format_clients_count_display(1)
        '1 cliente'

        >>> format_clients_count_display(0)
        '0 clientes'
    """
    if count == 1:
        return "1 cliente"

    return f"{count} clientes"


# ============================================================================
# ROUND 6 - USER STATUS E DISPLAY
# ============================================================================


def build_user_status_suffix(email: str, role: str = "user") -> str:
    """Constrói sufixo de status com informações do usuário.

    Retorna string no formato " | Usuário: email (role)" se email fornecido,
    ou string vazia se não houver email.

    Args:
        email: Email do usuário (pode ser vazio)
        role: Role do usuário (padrão "user")

    Returns:
        Sufixo formatado ou string vazia

    Examples:
        >>> build_user_status_suffix("user@example.com", "admin")
        ' | Usuário: user@example.com (admin)'

        >>> build_user_status_suffix("test@test.com")
        ' | Usuário: test@test.com (user)'

        >>> build_user_status_suffix("")
        ''

        >>> build_user_status_suffix("", "admin")
        ''
    """
    if not email:
        return ""
    return f" | Usuário: {email} ({role})"


def combine_status_display(base_text: str, suffix: str) -> str:
    """Combina texto base e sufixo para exibição de status.

    Se base_text estiver vazio e suffix começar com " | ",
    remove o prefixo " | " do suffix.

    Args:
        base_text: Texto base do status
        suffix: Sufixo com informações adicionais

    Returns:
        Texto de status combinado

    Examples:
        >>> combine_status_display("LOCAL", " | Usuário: user@test.com (admin)")
        'LOCAL | Usuário: user@test.com (admin)'

        >>> combine_status_display("", " | Usuário: user@test.com (admin)")
        'Usuário: user@test.com (admin)'

        >>> combine_status_display("PROD", "")
        'PROD'

        >>> combine_status_display("", "")
        ''
    """
    if not base_text and suffix.startswith(" | "):
        return suffix[3:]  # Remove " | " prefix
    return f"{base_text}{suffix}"


@dataclass(frozen=True)
class StatusDotStyle:
    """Estilo do dot de status (cor/bootstyle)."""

    symbol: str
    bootstyle: str


def compute_status_dot_style(is_online: bool | None) -> StatusDotStyle:
    """Calcula estilo do status dot baseado em estado de conectividade.

    Args:
        is_online: True (online), False (offline), None (unknown)

    Returns:
        StatusDotStyle com symbol e bootstyle

    Examples:
        >>> compute_status_dot_style(True)
        StatusDotStyle(symbol='•', bootstyle='success')

        >>> compute_status_dot_style(False)
        StatusDotStyle(symbol='•', bootstyle='danger')

        >>> compute_status_dot_style(None)
        StatusDotStyle(symbol='•', bootstyle='warning')
    """
    if is_online is True:
        bootstyle = "success"
    elif is_online is False:
        bootstyle = "danger"
    else:
        bootstyle = "warning"

    return StatusDotStyle(symbol="•", bootstyle=bootstyle)
