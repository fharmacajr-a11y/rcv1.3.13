# -*- coding: utf-8 -*-
"""
Constantes da Main Window.

Centraliza valores constantes usados pela janela principal.
"""

# Versão exibida no título da janela
APP_TITLE = "Regularize Consultoria"
APP_VERSION = "v1.2.0"

# Ícone da aplicação
APP_ICON_PATH = "rc.ico"

# Timings (em milissegundos)
INITIAL_STATUS_DELAY = 300  # Delay antes da primeira atualização de status
STATUS_REFRESH_INTERVAL = 300  # Intervalo para re-tentar atualização de status
HEALTH_POLL_INTERVAL = 5000  # Intervalo de polling do health check (5s)

# Cores de status (dot indicator)
STATUS_COLOR_ONLINE = "green"
STATUS_COLOR_OFFLINE = "red"
STATUS_COLOR_UNKNOWN = "gray"

# Texto padrão para ambiente
DEFAULT_ENV_TEXT = "LOCAL"
