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

# ============================================================================
# TREEVIEW MODERNIZATION - Visual Design Improvements
# ============================================================================

# Altura da linha (rowheight) - aumentada para melhor legibilidade
# Recomendado: 30-35px para evitar linhas "grudadas"
TREEVIEW_ROW_HEIGHT: Final[int] = 32

# Fonte moderna para a Treeview
TREEVIEW_FONT_FAMILY: Final[str] = "Segoe UI"  # Fallback: Roboto, Arial
TREEVIEW_FONT_SIZE: Final[int] = 10
TREEVIEW_HEADER_FONT_SIZE: Final[int] = 11

# Cores de status dinâmico (badges visuais)
# Status: Novo Cliente - Verde (destaque positivo)
STATUS_NOVO_CLIENTE_BG: Final[str] = "#d4edda"  # Verde claro
STATUS_NOVO_CLIENTE_FG: Final[str] = "#155724"  # Verde escuro

# Status: Sem resposta - Laranja/Cinza (atenção)
STATUS_SEM_RESPOSTA_BG: Final[str] = "#fff3cd"  # Amarelo claro
STATUS_SEM_RESPOSTA_FG: Final[str] = "#856404"  # Laranja escuro

# Status: Análise - Azul (em processamento)
STATUS_ANALISE_BG: Final[str] = "#cce5ff"  # Azul claro
STATUS_ANALISE_FG: Final[str] = "#004085"  # Azul escuro

# Status: Aguardando documento/pagamento - Cinza neutro
STATUS_AGUARDANDO_BG: Final[str] = "#e2e3e5"  # Cinza claro
STATUS_AGUARDANDO_FG: Final[str] = "#383d41"  # Cinza escuro

# Status: Finalizado - Verde sucesso
STATUS_FINALIZADO_BG: Final[str] = "#c3e6cb"  # Verde médio
STATUS_FINALIZADO_FG: Final[str] = "#1e7e34"  # Verde

# Status: Follow-up - Roxo/Magenta (urgência)
STATUS_FOLLOWUP_BG: Final[str] = "#e2d5f1"  # Lilás claro
STATUS_FOLLOWUP_FG: Final[str] = "#6f42c1"  # Roxo

# Cores de zebra striping (linhas alternadas)
ZEBRA_EVEN_BG: Final[str] = "#ffffff"  # Branco
ZEBRA_ODD_BG: Final[str] = "#f8f9fa"  # Cinza muito claro

# Base de delay (segundos) para backoff em _with_retries / operações de rede
RETRY_BASE_DELAY: Final[float] = 0.4
