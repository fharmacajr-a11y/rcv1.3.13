from typing import Final

# Column widths for table display
# ============================================================================
# COLUNAS FIXAS (stretch=False) - tamanho previsível, não crescem
# ============================================================================
COL_ID_WIDTH: Final[int] = 55
COL_CNPJ_WIDTH: Final[int] = 130  # CNPJ fixo e compacto
COL_WHATSAPP_WIDTH: Final[int] = 160  # WhatsApp - aumentado (+20px) para mover pra esquerda
COL_ULTIMA_WIDTH: Final[int] = 190  # Última Alteração - garantir visibilidade
COL_OBS_WIDTH: Final[int] = 180  # Observações - reduzida para compactar (-80px)
COL_STATUS_WIDTH: Final[int] = 250  # Status - reduzido para ficar perto da Última Alteração (-50px)

# ============================================================================
# COLUNAS FLEX (stretch=True) - crescem proporcionalmente com a janela
# Pesos: Razão=7 (maior), Nome=3
# ============================================================================
COL_RAZAO_WIDTH: Final[int] = 520  # Razão Social - peso 7 (ajustado -20px)
COL_NOME_WIDTH: Final[int] = 220  # Nome - peso 3 - aumentado ligeiramente (+20px)

# Minwidths para evitar encolhimento excessivo (apenas colunas flex)
COL_RAZAO_MINWIDTH: Final[int] = 260
COL_NOME_MINWIDTH: Final[int] = 160

# Base de delay (segundos) para backoff em _with_retries / operações de rede
RETRY_BASE_DELAY: Final[float] = 0.4
