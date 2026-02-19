"""Constantes de mensagens de UI do Hub.

ORG-011: Módulo central que consolida strings de mensagens, títulos e banners
usados em diferentes partes do Hub, eliminando duplicação e centralizando manutenção.

Este módulo contém APENAS mensagens de interface de usuário. Logs de debug
permanecem nos módulos específicos (ex: hub_notes_facade_constants.py).

Organização:
- Títulos de diálogos
- Mensagens de autenticação
- Mensagens de estado (loading, empty, error)
- Mensagens de erro (templates com placeholders)
- Mensagens informativas
- Banners e notificações
"""

# ════════════════════════════════════════════════════════════════════════
# Títulos de Diálogos
# ════════════════════════════════════════════════════════════════════════

TITLE_AUTH_REQUIRED = "Autenticação Necessária"
"""Título para diálogos que requerem autenticação."""

TITLE_ERROR = "Erro"
"""Título padrão para diálogos de erro."""

TITLE_IN_DEVELOPMENT = "Em Desenvolvimento"
"""Título para funcionalidades em desenvolvimento."""

# ════════════════════════════════════════════════════════════════════════
# Mensagens de Autenticação
# ════════════════════════════════════════════════════════════════════════

MSG_LOGIN_REQUIRED_TASKS = "Por favor, faça login para criar tarefas."
"""Mensagem quando usuário tenta criar tarefa sem estar autenticado."""

MSG_LOGIN_REQUIRED_OBLIGATIONS = "Por favor, faça login para criar obrigações."
"""Mensagem quando usuário tenta criar obrigação sem estar autenticado."""

# ════════════════════════════════════════════════════════════════════════
# Mensagens de Estado do Painel de Notas
# ════════════════════════════════════════════════════════════════════════

MSG_LOADING = "Carregando notas..."
"""Mensagem exibida durante carregamento de notas."""

MSG_EMPTY_DEFAULT = "Nenhuma nota compartilhada ainda."
"""Mensagem padrão quando não há notas para exibir."""

MSG_ERROR_PREFIX = "❌ "
"""Prefixo emoji para mensagens de erro em notas."""

# ════════════════════════════════════════════════════════════════════════
# Mensagens de Erro (Templates com Placeholders)
# ════════════════════════════════════════════════════════════════════════

MSG_APP_NOT_FOUND = "Aplicação principal não encontrada."
"""Erro quando referência ao app principal não está disponível."""

MSG_ERROR_OPEN_DIALOG = "Erro ao abrir diálogo: {error}"
"""Template para erro ao abrir diálogo. Use .format(error=e)."""

MSG_ERROR_START_FLOW = "Erro ao iniciar fluxo: {error}"
"""Template para erro ao iniciar fluxo. Use .format(error=e)."""

MSG_ERROR_OPEN_VIEW = "Erro ao abrir visualização: {error}"
"""Template para erro ao abrir visualização. Use .format(error=e)."""

MSG_ERROR_PROCESS_SELECTION = "Erro ao processar seleção: {error}"
"""Template para erro ao processar seleção. Use .format(error=e)."""

MSG_ERROR_PROCESS_ACTION = "Erro ao processar ação: {error}"
"""Template para erro ao processar ação. Use .format(error=e)."""

# ════════════════════════════════════════════════════════════════════════
# Mensagens Informativas
# ════════════════════════════════════════════════════════════════════════

MSG_ACTIVITY_VIEW_COMING_SOON = (
    "A visualização completa da atividade estará disponível em breve.\n\n"
    "No momento, você pode ver as últimas atividades diretamente no Hub."
)
"""Mensagem informando que visualização de atividades está em desenvolvimento."""

# ════════════════════════════════════════════════════════════════════════
# Banners e Notificações
# ════════════════════════════════════════════════════════════════════════

BANNER_CLIENT_PICK_OBLIGATIONS = "🔍 Modo seleção: escolha um cliente para gerenciar obrigações"
"""Banner exibido durante modo de seleção de cliente para obrigações."""

# ════════════════════════════════════════════════════════════════════════
# Exportações
# ════════════════════════════════════════════════════════════════════════

__all__ = [
    # Títulos
    "TITLE_AUTH_REQUIRED",
    "TITLE_ERROR",
    "TITLE_IN_DEVELOPMENT",
    # Autenticação
    "MSG_LOGIN_REQUIRED_TASKS",
    "MSG_LOGIN_REQUIRED_OBLIGATIONS",
    # Estado de notas
    "MSG_LOADING",
    "MSG_EMPTY_DEFAULT",
    "MSG_ERROR_PREFIX",
    # Erros (templates)
    "MSG_APP_NOT_FOUND",
    "MSG_ERROR_OPEN_DIALOG",
    "MSG_ERROR_START_FLOW",
    "MSG_ERROR_OPEN_VIEW",
    "MSG_ERROR_PROCESS_SELECTION",
    "MSG_ERROR_PROCESS_ACTION",
    # Informativas
    "MSG_ACTIVITY_VIEW_COMING_SOON",
    # Banners
    "BANNER_CLIENT_PICK_OBLIGATIONS",
]
