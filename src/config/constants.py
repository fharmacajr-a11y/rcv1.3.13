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

# Altura da linha (rowheight) - aumentada para evitar texto cortado
# 36px garante espaço vertical para centralização do texto
TREEVIEW_ROW_HEIGHT: Final[int] = 36

# Fonte moderna para a Treeview (reduzida para 9pt para caber bem em 36px)
TREEVIEW_FONT_FAMILY: Final[str] = "Segoe UI"  # Fallback: Roboto, Arial
TREEVIEW_FONT_SIZE: Final[int] = 9
TREEVIEW_HEADER_FONT_SIZE: Final[int] = 10

# ============================================================================
# CORES DE STATUS - Tons PASTEL suaves com texto escuro para legibilidade
# ============================================================================
# As cores de fundo são muito claras (pastel) para não conflitar com zebra
# O texto é sempre escuro (preto/cinza) para garantir contraste

# Status: Novo Cliente - Verde pastel suave
STATUS_NOVO_CLIENTE_BG: Final[str] = "#e8f5e9"  # Verde muito claro (pastel)
STATUS_NOVO_CLIENTE_FG: Final[str] = "#1b5e20"  # Verde escuro para texto

# Status: Sem resposta - Amarelo/Laranja pastel suave
STATUS_SEM_RESPOSTA_BG: Final[str] = "#fff8e1"  # Amarelo muito claro (pastel)
STATUS_SEM_RESPOSTA_FG: Final[str] = "#e65100"  # Laranja escuro para texto

# Status: Análise - Azul pastel suave
STATUS_ANALISE_BG: Final[str] = "#e3f2fd"  # Azul muito claro (pastel)
STATUS_ANALISE_FG: Final[str] = "#0d47a1"  # Azul escuro para texto

# Status: Aguardando documento/pagamento - Cinza pastel
STATUS_AGUARDANDO_BG: Final[str] = "#f5f5f5"  # Cinza muito claro
STATUS_AGUARDANDO_FG: Final[str] = "#424242"  # Cinza escuro para texto

# Status: Finalizado - Verde pastel (mais saturado que Novo Cliente)
STATUS_FINALIZADO_BG: Final[str] = "#c8e6c9"  # Verde claro
STATUS_FINALIZADO_FG: Final[str] = "#2e7d32"  # Verde escuro

# Status: Follow-up - Roxo/Lilás pastel suave
STATUS_FOLLOWUP_BG: Final[str] = "#f3e5f5"  # Lilás muito claro (pastel)
STATUS_FOLLOWUP_FG: Final[str] = "#6a1b9a"  # Roxo escuro para texto

# Cores de zebra striping (linhas alternadas)
ZEBRA_EVEN_BG: Final[str] = "#ffffff"  # Branco
ZEBRA_ODD_BG: Final[str] = "#f8f9fa"  # Cinza muito claro

# Base de delay (segundos) para backoff em _with_retries / operações de rede
RETRY_BASE_DELAY: Final[float] = 0.4
