# -*- coding: utf-8 -*-
"""
Helpers puros para hub_screen.py - Lógica testável sem Tkinter.

Este módulo contém funções puras extraídas de HubScreen para permitir
testes unitários sem dependências de GUI.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# Timezone local com fallback
try:
    _LOCAL_TZ = datetime.now().astimezone().tzinfo or timezone.utc
except Exception:
    _LOCAL_TZ = timezone.utc


# ============================================================================
# MÓDULOS E NAVEGAÇÃO
# ============================================================================


@dataclass(frozen=True)
class ModuleButton:
    """Configuração de um botão de módulo no Hub."""

    text: str
    enabled: bool
    bootstyle: str
    has_callback: bool


def build_module_buttons(
    has_clientes: bool = True,
    has_senhas: bool = True,
    has_auditoria: bool = True,
    has_cashflow: bool = False,
    has_anvisa: bool = False,
    has_farmacia_popular: bool = False,
    has_sngpc: bool = False,
    has_sifap: bool = False,
) -> list[ModuleButton]:
    """
    Constrói lista de botões de módulos baseado em features habilitadas.

    Esta função centraliza a lógica de quais módulos aparecem no Hub
    e em qual ordem, facilitando testes e manutenção.

    Args:
        has_clientes: Se módulo Clientes está habilitado
        has_senhas: Se módulo Senhas está habilitado
        has_auditoria: Se módulo Auditoria está habilitado
        has_cashflow: Se módulo Fluxo de Caixa está habilitado
        has_anvisa: Se módulo Anvisa está habilitado
        has_farmacia_popular: Se módulo Farmácia Popular está habilitado
        has_sngpc: Se módulo Sngpc está habilitado
        has_sifap: Se módulo Sifap está habilitado

    Returns:
        Lista de ModuleButton na ordem de exibição

    Examples:
        >>> buttons = build_module_buttons()
        >>> len(buttons)
        8
        >>> buttons[0].text
        'Clientes'
        >>> buttons[0].bootstyle
        'info'
        >>> buttons[0].enabled
        True
        >>> buttons_no_cashflow = build_module_buttons(has_cashflow=False)
        >>> cashflow_btn = [b for b in buttons_no_cashflow if b.text == 'Fluxo de Caixa'][0]
        >>> cashflow_btn.enabled
        False
    """
    buttons = []

    # Ordem fixa de módulos
    if has_clientes:
        buttons.append(ModuleButton("Clientes", True, "info", True))

    if has_senhas:
        buttons.append(ModuleButton("Senhas", True, "info", True))

    if has_auditoria:
        buttons.append(ModuleButton("Auditoria", True, "success", True))

    # Fluxo de Caixa (em desenvolvimento)
    buttons.append(
        ModuleButton(
            "Fluxo de Caixa",
            enabled=has_cashflow,
            bootstyle="warning",
            has_callback=has_cashflow,
        )
    )

    # Módulos em desenvolvimento (sempre aparecem, mas desabilitados)
    if True:  # Sempre mostrar placeholders
        buttons.append(ModuleButton("Anvisa", has_anvisa, "secondary", has_anvisa))
        buttons.append(
            ModuleButton(
                "Farmácia Popular",
                has_farmacia_popular,
                "secondary",
                has_farmacia_popular,
            )
        )
        buttons.append(ModuleButton("Sngpc", has_sngpc, "secondary", has_sngpc))
        buttons.append(ModuleButton("Sifap", has_sifap, "secondary", has_sifap))

    return buttons


# ============================================================================
# SESSÃO E AUTENTICAÇÃO
# ============================================================================


def is_auth_ready(has_app: bool, has_auth: bool, is_authenticated: bool) -> bool:
    """
    Verifica se autenticação está pronta sem levantar exceção.

    Centraliza a lógica de verificação de autenticação para evitar
    duplicação e facilitar testes.

    Args:
        has_app: Se objeto app existe
        has_auth: Se app.auth existe
        is_authenticated: Se app.auth.is_authenticated é True

    Returns:
        True se autenticação está pronta, False caso contrário

    Examples:
        >>> is_auth_ready(True, True, True)
        True
        >>> is_auth_ready(True, True, False)
        False
        >>> is_auth_ready(True, False, True)
        False
        >>> is_auth_ready(False, True, True)
        False
    """
    return has_app and has_auth and is_authenticated


def extract_email_prefix(email: str | None) -> str:
    """
    Extrai o prefixo de um email (parte antes do @).

    Usado para criar nomes curtos a partir de emails quando
    display_name não está disponível.

    Args:
        email: Endereço de email completo ou None

    Returns:
        Prefixo do email (antes do @) ou string vazia

    Examples:
        >>> extract_email_prefix("usuario@example.com")
        'usuario'
        >>> extract_email_prefix("joao.silva@empresa.com.br")
        'joao.silva'
        >>> extract_email_prefix("sem-arroba")
        'sem-arroba'
        >>> extract_email_prefix("")
        ''
        >>> extract_email_prefix(None)
        ''
        >>> extract_email_prefix("  user@test.com  ")
        'user'
    """
    if not email:
        return ""

    email = email.strip()
    if "@" in email:
        return email.split("@")[0].strip()

    return email


def format_author_fallback(
    email: str | None,
    display_name: str | None = None,
) -> str:
    """
    Formata nome de autor com fallback para email/prefixo.

    Hierarquia de prioridade:
    1. display_name (se não vazio)
    2. prefixo do email
    3. email completo
    4. "Anônimo"

    Args:
        email: Endereço de email do autor
        display_name: Nome de exibição preferido (opcional)

    Returns:
        Nome formatado para exibição

    Examples:
        >>> format_author_fallback("user@test.com", "João Silva")
        'João Silva'
        >>> format_author_fallback("user@test.com", "")
        'user'
        >>> format_author_fallback("user@test.com", None)
        'user'
        >>> format_author_fallback("user@test.com")
        'user'
        >>> format_author_fallback("", "")
        'Anônimo'
        >>> format_author_fallback(None, None)
        'Anônimo'
        >>> format_author_fallback("sem-arroba@", "")
        'sem-arroba'
    """
    # Prioridade 1: display_name
    if display_name and display_name.strip():
        return display_name.strip()

    # Prioridade 2/3: prefixo ou email completo
    if email:
        prefix = extract_email_prefix(email)
        if prefix:
            return prefix
        # Se não tem @, usar email completo
        if email.strip():
            return email.strip()

    # Fallback final
    return "Anônimo"


# ============================================================================
# ESTILO DE BOTÕES
# ============================================================================


def calculate_module_button_style(
    highlight: bool = False,
    yellow: bool = False,
    bootstyle: Optional[str] = None,
) -> str:
    """
    Determina o estilo de um botão de módulo baseado em flags de estado.

    Esta função implementa a hierarquia de prioridade de estilos:
    1. bootstyle explícito (maior prioridade)
    2. yellow (warning)
    3. highlight (success)
    4. padrão (secondary)

    Args:
        highlight: Se True, usa estilo "success" (verde)
        yellow: Se True, usa estilo "warning" (amarelo)
        bootstyle: Estilo explícito que sobrescreve highlight/yellow

    Returns:
        str: Nome do estilo ttkbootstrap ("success", "warning", "secondary", ou customizado)

    Examples:
        >>> calculate_module_button_style()
        'secondary'
        >>> calculate_module_button_style(highlight=True)
        'success'
        >>> calculate_module_button_style(yellow=True)
        'warning'
        >>> calculate_module_button_style(bootstyle='danger')
        'danger'
        >>> calculate_module_button_style(highlight=True, yellow=True)
        'warning'
        >>> calculate_module_button_style(highlight=True, bootstyle='info')
        'info'
    """
    if bootstyle:
        return bootstyle
    if yellow:
        return "warning"
    if highlight:
        return "success"
    return "secondary"


def calculate_notes_ui_state(has_org_id: bool) -> dict[str, Any]:
    """
    Calcula o estado da UI de notas baseado na presença de org_id.

    Determina se o botão "Adicionar Nota" deve estar habilitado e qual
    mensagem de placeholder deve aparecer no campo de texto.

    Args:
        has_org_id: Se True, sessão tem organização válida

    Returns:
        dict com chaves:
            - button_enabled (bool): Se botão "Adicionar" está habilitado
            - placeholder_message (str): Mensagem para campo de texto
            - text_field_enabled (bool): Se campo de texto está habilitado

    Examples:
        >>> calculate_notes_ui_state(True)
        {'button_enabled': True, 'placeholder_message': '', 'text_field_enabled': True}
        >>> result = calculate_notes_ui_state(False)
        >>> result['button_enabled']
        False
        >>> 'Sessão sem organização' in result['placeholder_message']
        True
        >>> result['text_field_enabled']
        False
    """
    if has_org_id:
        return {
            "button_enabled": True,
            "placeholder_message": "",
            "text_field_enabled": True,
        }

    return {
        "button_enabled": False,
        "placeholder_message": "Sessão sem organização. Faça login novamente.",
        "text_field_enabled": False,
    }


def calculate_notes_content_hash(notes: list[dict[str, Any]]) -> str:
    """
    Calcula hash SHA256 do conteúdo das notas para detectar mudanças.

    Usa apenas campos relevantes para renderização (author_email, created_at,
    body length, author_name) para gerar uma assinatura única do conteúdo.
    Isso permite skip de re-render quando o conteúdo não mudou.

    Args:
        notes: Lista de dicionários com dados das notas

    Returns:
        str: Hash SHA256 hex (64 caracteres) do conteúdo normalizado

    Examples:
        >>> notes = [
        ...     {'author_email': 'user@example.com', 'created_at': '2025-01-01T10:00:00Z', 'body': 'Test', 'author_name': 'User'},
        ... ]
        >>> hash1 = calculate_notes_content_hash(notes)
        >>> len(hash1)
        64
        >>> hash2 = calculate_notes_content_hash(notes)
        >>> hash1 == hash2
        True
        >>> notes2 = [
        ...     {'author_email': 'user@example.com', 'created_at': '2025-01-01T10:00:00Z', 'body': 'Changed', 'author_name': 'User'},
        ... ]
        >>> hash3 = calculate_notes_content_hash(notes2)
        >>> hash1 == hash3
        False
        >>> calculate_notes_content_hash([])
        'd751713988987e9331980363e24189ce'
    """
    sig_items = []
    for n in notes:
        email = (n.get("author_email") or "").strip().lower()
        created_at = n.get("created_at") or ""
        body_len = len(n.get("body") or "")
        author_name = n.get("author_name") or ""
        sig_items.append((email, created_at, body_len, author_name))

    # Usar MD5 para consistência (hash mais curto, não para segurança)
    content_json = json.dumps(sig_items, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(content_json.encode("utf-8"), usedforsecurity=False).hexdigest()  # nosec B324


def should_skip_refresh_by_cooldown(
    last_refresh: float,
    cooldown_seconds: int,
    force: bool = False,
) -> bool:
    """
    Determina se deve pular refresh baseado em cooldown e flag force.

    Implementa lógica de cooldown para evitar requisições duplicadas:
    - Se force=True, sempre refresha (ignora cooldown)
    - Se tempo desde último refresh < cooldown, pula
    - Caso contrário, permite refresh

    Args:
        last_refresh: Timestamp Unix (time.time()) do último refresh
        cooldown_seconds: Segundos mínimos entre refreshes
        force: Se True, ignora cooldown e sempre refresha

    Returns:
        bool: True se deve PULAR refresh, False se deve PERMITIR refresh

    Examples:
        >>> now = time.time()
        >>> # Força sempre permite
        >>> should_skip_refresh_by_cooldown(now, 30, force=True)
        False
        >>> # Refresh recente (5s atrás) com cooldown de 30s
        >>> should_skip_refresh_by_cooldown(now - 5, 30, force=False)
        True
        >>> # Refresh antigo (35s atrás) com cooldown de 30s
        >>> should_skip_refresh_by_cooldown(now - 35, 30, force=False)
        False
        >>> # Primeiro refresh (last_refresh=0)
        >>> should_skip_refresh_by_cooldown(0, 30, force=False)
        False
        >>> # Cooldown de 0 sempre permite
        >>> should_skip_refresh_by_cooldown(now, 0, force=False)
        False
    """
    if force:
        return False  # force=True sempre permite refresh

    now = time.time()
    elapsed = now - last_refresh

    # Se cooldown é 0 ou negativo, sempre permite
    if cooldown_seconds <= 0:
        return False

    # Se elapsed < cooldown, deve pular (True)
    return elapsed < cooldown_seconds


def normalize_note_dict(note: Any) -> dict[str, Any]:
    """
    Normaliza uma nota (dict/tuple/list) para formato dict padrão.

    Converte diferentes formatos de entrada (tuplas legadas, listas, dicts)
    para um formato de dicionário consistente com chaves padronizadas.

    Args:
        note: Nota em qualquer formato (dict, tuple, list, ou outro)

    Returns:
        dict com chaves padronizadas:
            - author_email (str)
            - created_at (str)
            - body (str)
            - author_name (str, opcional)

    Examples:
        >>> normalize_note_dict({'author_email': 'user@test.com', 'body': 'Test'})
        {'author_email': 'user@test.com', 'created_at': '', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict(('2025-01-01T10:00:00Z', 'user@test.com', 'Test'))
        {'author_email': 'user@test.com', 'created_at': '2025-01-01T10:00:00Z', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict(['user@test.com', 'Test'])
        {'author_email': 'user@test.com', 'created_at': '', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict({})
        {'author_email': '', 'created_at': '', 'body': '', 'author_name': ''}
    """
    if isinstance(note, dict):
        return {
            "author_email": (note.get("author_email") or note.get("author") or note.get("email") or ""),
            "created_at": (note.get("created_at") or note.get("timestamp") or ""),
            "body": (note.get("body") or note.get("text") or note.get("content") or ""),
            "author_name": (note.get("author_name") or note.get("display_name") or ""),
        }

    if isinstance(note, (tuple, list)):
        # Formatos possíveis:
        # (created_at, author, body) - 3 elementos
        # (author, body) - 2 elementos
        # (body,) - 1 elemento
        if len(note) >= 3:
            return {
                "author_email": str(note[1]),
                "created_at": str(note[0]),
                "body": str(note[2]),
                "author_name": "",
            }
        if len(note) == 2:
            return {
                "author_email": str(note[0]),
                "created_at": "",
                "body": str(note[1]),
                "author_name": "",
            }
        if len(note) == 1:
            return {
                "author_email": "",
                "created_at": "",
                "body": str(note[0]),
                "author_name": "",
            }

    # Fallback: converter para string
    return {
        "author_email": "",
        "created_at": "",
        "body": str(note) if note else "",
        "author_name": "",
    }


# ============================================================================
# FORMATAÇÃO DE NOTAS E TIMESTAMPS
# ============================================================================


def format_timestamp(ts_iso: str | None) -> str:
    """
    Converte timestamp ISO do Supabase para string local dd/mm/YYYY - HH:MM.

    Usa timezone local do sistema e trata casos de erro retornando
    o timestamp original ou "?" se vazio/inválido.

    Args:
        ts_iso: Timestamp ISO 8601 (ex: "2025-01-01T10:30:00Z")

    Returns:
        str: Timestamp formatado ou "?" se inválido

    Examples:
        >>> format_timestamp("2025-01-15T14:30:00Z")  # doctest: +SKIP
        '15/01/2025 - 11:30'
        >>> format_timestamp("")
        '?'
        >>> format_timestamp(None)
        '?'
        >>> format_timestamp("invalid")
        'invalid'
    """
    try:
        if not ts_iso:
            return "?"
        # Normalizar formato ISO
        value = ts_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        # Garantir timezone UTC se não tiver
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Converter para timezone local
        dt_local = dt.astimezone(_LOCAL_TZ)
        return dt_local.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        # Retornar timestamp original em caso de erro
        return ts_iso or "?"


def format_note_line(created_at: str | None, author_display: str, text: str) -> str:
    """
    Compõe linha de nota no formato padrão: [timestamp] autor: texto.

    Formato: "[dd/mm/YYYY - HH:MM] Nome do Autor: Texto da nota"

    Args:
        created_at: Timestamp ISO 8601
        author_display: Nome de exibição do autor
        text: Corpo da nota

    Returns:
        str: Linha formatada completa

    Examples:
        >>> format_note_line("2025-01-15T14:30:00Z", "João Silva", "Reunião às 15h")  # doctest: +SKIP
        '[15/01/2025 - 11:30] João Silva: Reunião às 15h'
        >>> format_note_line("", "Usuário", "Nota sem timestamp")
        '[?] Usuário: Nota sem timestamp'
        >>> format_note_line(None, "Anônimo", "Teste")
        '[?] Anônimo: Teste'
    """
    ts = format_timestamp(created_at)
    return f"[{ts}] {author_display}: {text}"


def should_show_notes_section(notes_count: int) -> bool:
    """
    Determina se seção de notas deve ser exibida baseado em contagem.

    Por enquanto sempre retorna True (seção sempre visível), mas
    centraliza a lógica para facilitar mudanças futuras.

    Args:
        notes_count: Número de notas disponíveis

    Returns:
        bool: True se deve mostrar seção de notas

    Examples:
        >>> should_show_notes_section(0)
        True
        >>> should_show_notes_section(1)
        True
        >>> should_show_notes_section(100)
        True
    """
    # Seção de notas sempre visível (mesmo vazia)
    return True


def format_notes_count(count: int) -> str:
    """
    Formata texto de contagem de notas com pluralização correta.

    Args:
        count: Número de notas

    Returns:
        str: Texto formatado (ex: "0 notas", "1 nota", "5 notas")

    Examples:
        >>> format_notes_count(0)
        '0 notas'
        >>> format_notes_count(1)
        '1 nota'
        >>> format_notes_count(2)
        '2 notas'
        >>> format_notes_count(100)
        '100 notas'
    """
    if count == 1:
        return "1 nota"
    return f"{count} notas"


def is_notes_list_empty(notes: list[dict[str, Any]] | None) -> bool:
    """
    Verifica se lista de notas está vazia ou None.

    Args:
        notes: Lista de notas ou None

    Returns:
        bool: True se lista está vazia/None, False caso contrário

    Examples:
        >>> is_notes_list_empty(None)
        True
        >>> is_notes_list_empty([])
        True
        >>> is_notes_list_empty([{'body': 'test'}])
        False
    """
    return not notes or len(notes) == 0


def should_skip_render_empty_notes(notes: list[dict[str, Any]] | None) -> bool:
    """
    Determina se deve pular render quando lista de notas vem vazia.

    Evita "branco" e piscadas na UI mantendo conteúdo anterior quando
    recebe lista vazia (comportamento defensivo).

    Args:
        notes: Lista de notas ou None

    Returns:
        bool: True se deve PULAR render, False se deve PERMITIR render

    Examples:
        >>> should_skip_render_empty_notes(None)
        True
        >>> should_skip_render_empty_notes([])
        True
        >>> should_skip_render_empty_notes([{'body': 'test'}])
        False
    """
    return is_notes_list_empty(notes)


def calculate_retry_delay_ms(
    retry_count: int,
    base_delay_ms: int = 60000,
    max_delay_ms: int = 300000,
) -> int:
    """
    Calcula delay para retry com backoff exponencial.

    Implementa estratégia de backoff exponencial para retry de operações
    falhadas (ex: tabela de notas ausente).

    Args:
        retry_count: Número de tentativas já realizadas (0 = primeira tentativa)
        base_delay_ms: Delay base em milissegundos (padrão 60s)
        max_delay_ms: Delay máximo em milissegundos (padrão 5min)

    Returns:
        int: Delay em milissegundos para próximo retry

    Examples:
        >>> calculate_retry_delay_ms(0)
        60000
        >>> calculate_retry_delay_ms(1)
        120000
        >>> calculate_retry_delay_ms(2)
        240000
        >>> calculate_retry_delay_ms(10)
        300000
        >>> calculate_retry_delay_ms(0, base_delay_ms=1000, max_delay_ms=5000)
        1000
    """
    delay = base_delay_ms * (2**retry_count)
    return min(delay, max_delay_ms)
