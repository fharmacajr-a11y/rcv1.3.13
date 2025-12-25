# -*- coding: utf-8 -*-
"""Constantes compartilhadas do HubScreen.

ORG-004: Extraído de hub_screen.py para reduzir complexidade.
Contém apenas constantes de configuração sem dependências de UI.

NOTA: AUTH_RETRY_MS está definida em hub_screen_builder.py e hub_lifecycle.py.
Este módulo serve como ponto central futuro para consolidação de constantes
quando todas as duplicações forem resolvidas.
"""

from __future__ import annotations

# Constantes para retry de autenticação
# NOTA: Atualmente duplicada em hub_screen_builder.py (linha 44)
# Valor mantido aqui para referência e futura consolidação
AUTH_RETRY_MS = 2000  # 2 segundos (milissegundos)
