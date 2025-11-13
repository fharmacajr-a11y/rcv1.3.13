from typing import Final

# Column widths for table display
COL_ID_WIDTH: Final[int] = 40
COL_RAZAO_WIDTH: Final[int] = 240
COL_CNPJ_WIDTH: Final[int] = 140
COL_NOME_WIDTH: Final[int] = 170
COL_WHATSAPP_WIDTH: Final[int] = 120
COL_OBS_WIDTH: Final[int] = 180  # Observações um pouco menor p/ caber tudo
COL_STATUS_WIDTH: Final[int] = 200
COL_ULTIMA_WIDTH: Final[int] = 165

# Base de delay (segundos) para backoff em _with_retries / operações de rede
RETRY_BASE_DELAY: Final[float] = 0.4
