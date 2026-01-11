from typing import Final

# ============================================================================
# LARGURA DAS COLUNAS - Prioridade: CNPJ, Nome, WhatsApp (sem cortes)
# ============================================================================
COL_ID_WIDTH: Final[int] = 45  # ID numérico pequeno
COL_RAZAO_WIDTH: Final[int] = 220  # Razão Social (estica)
COL_CNPJ_WIDTH: Final[int] = 150  # CNPJ completo sem corte (XX.XXX.XXX/XXXX-XX)
COL_NOME_WIDTH: Final[int] = 180  # Nome do responsável
COL_WHATSAPP_WIDTH: Final[int] = 130  # WhatsApp com DDD (+55 11 99999-9999)
COL_OBS_WIDTH: Final[int] = 90  # Observações REDUZIDA pela metade
COL_STATUS_WIDTH: Final[int] = 180  # Status (um pouco menor)
COL_ULTIMA_WIDTH: Final[int] = 150  # Última Alteração

# ============================================================================
# TREEVIEW - Layout Limpo e Padronizado
# ============================================================================

# Altura FIXA de 28px para todas as linhas (nenhuma tag pode alterar)
TREEVIEW_ROW_HEIGHT: Final[int] = 28

# Fonte ÚNICA para toda a Treeview: Segoe UI 9pt (sem negrito)
TREEVIEW_FONT_FAMILY: Final[str] = "Segoe UI"
TREEVIEW_FONT_SIZE: Final[int] = 9
TREEVIEW_HEADER_FONT_SIZE: Final[int] = 9  # Cabeçalho mesmo tamanho

# ============================================================================
# ZEBRA STRIPING - Apenas branco e cinza claríssimo (sem cores de status)
# ============================================================================
ZEBRA_EVEN_BG: Final[str] = "#ffffff"  # Branco puro
ZEBRA_ODD_BG: Final[str] = "#f9f9f9"  # Cinza claríssimo padrão

# ============================================================================
# CORES DE STATUS - DESABILITADAS (mantidas para compatibilidade futura)
# ============================================================================
# Por enquanto, todas as linhas usam apenas zebra striping.
# As constantes abaixo são mantidas mas não são aplicadas.
STATUS_NOVO_CLIENTE_BG: Final[str] = "#ffffff"
STATUS_NOVO_CLIENTE_FG: Final[str] = "#000000"
STATUS_SEM_RESPOSTA_BG: Final[str] = "#ffffff"
STATUS_SEM_RESPOSTA_FG: Final[str] = "#000000"
STATUS_ANALISE_BG: Final[str] = "#ffffff"
STATUS_ANALISE_FG: Final[str] = "#000000"
STATUS_AGUARDANDO_BG: Final[str] = "#ffffff"
STATUS_AGUARDANDO_FG: Final[str] = "#000000"
STATUS_FINALIZADO_BG: Final[str] = "#ffffff"
STATUS_FINALIZADO_FG: Final[str] = "#000000"
STATUS_FOLLOWUP_BG: Final[str] = "#ffffff"
STATUS_FOLLOWUP_FG: Final[str] = "#000000"

# Base de delay (segundos) para backoff em _with_retries / operações de rede
RETRY_BASE_DELAY: Final[float] = 0.4
