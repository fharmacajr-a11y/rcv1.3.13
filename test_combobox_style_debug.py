#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de debug para verificar estilo do Combobox."""

import logging
import ttkbootstrap as tb

from src.utils.themes import apply_combobox_style

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Criar janela de teste
root = tb.Window(themename="flatly")
root.title("Teste de Estilo Combobox")
root.geometry("600x400")

# Obter instância de Style E aplicar tema
app_style = tb.Style()
app_style.theme_use("flatly")  # ← IMPORTANTE: aplicar tema primeiro

logger.info("=" * 60)
logger.info("TESTE DE ESTILO COMBOBOX - ANTES")
logger.info("=" * 60)

# Verificar estado ANTES
entry_bg_before = app_style.lookup("TEntry", "fieldbackground", ("!disabled",))
combo_readonly_before = app_style.lookup("TCombobox", "fieldbackground", ("readonly",))
combo_normal_before = app_style.lookup("TCombobox", "fieldbackground", ("!disabled",))
combo_map_before = app_style.map("TCombobox", "fieldbackground")

logger.info("Entry background: %s", entry_bg_before)
logger.info("Combobox readonly: %s", combo_readonly_before)
logger.info("Combobox normal: %s", combo_normal_before)
logger.info("Combobox map: %s", combo_map_before)

# Aplicar correção
logger.info("=" * 60)
logger.info("APLICANDO CORREÇÃO")
logger.info("=" * 60)
apply_combobox_style(app_style)

# Verificar estado DEPOIS
logger.info("=" * 60)
logger.info("VERIFICAÇÃO FINAL")
logger.info("=" * 60)

combo_readonly_after = app_style.lookup("TCombobox", "fieldbackground", ("readonly",))
combo_normal_after = app_style.lookup("TCombobox", "fieldbackground", ("!disabled",))
combo_focus_after = app_style.lookup("TCombobox", "fieldbackground", ("focus",))
combo_active_after = app_style.lookup("TCombobox", "fieldbackground", ("active",))
combo_map_after = app_style.map("TCombobox", "fieldbackground")

logger.info("Combobox readonly DEPOIS: %s", combo_readonly_after)
logger.info("Combobox normal DEPOIS: %s", combo_normal_after)
logger.info("Combobox focus DEPOIS: %s", combo_focus_after)
logger.info("Combobox active DEPOIS: %s", combo_active_after)
logger.info("Combobox map DEPOIS: %s", combo_map_after)

# Criar widgets de teste
frame = tb.Frame(root, padding=20)
frame.pack(fill="both", expand=True)

tb.Label(frame, text="Entry (referência):", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
entry = tb.Entry(frame)
entry.insert(0, "Entry com fundo padrão")
entry.pack(fill="x", pady=(0, 20))

tb.Label(frame, text="Combobox readonly:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
combo_readonly = tb.Combobox(frame, values=["Opção 1", "Opção 2", "Opção 3"], state="readonly")
combo_readonly.set("Opção 1")
combo_readonly.pack(fill="x", pady=(0, 20))

tb.Label(frame, text="Combobox normal:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
combo_normal = tb.Combobox(frame, values=["Item A", "Item B", "Item C"])
combo_normal.set("Item A")
combo_normal.pack(fill="x", pady=(0, 20))

# Resultados - verificar se Combobox agora usa #ffffff
target_bg = "#ffffff"
if combo_readonly_after == target_bg:
    logger.info("✅ SUCESSO: Combobox readonly agora usa fundo branco: %s", combo_readonly_after)
    success = True
else:
    logger.error("❌ FALHA: Combobox readonly não está com fundo branco!")
    logger.error("   Esperado: %s", target_bg)
    logger.error("   Obtido: %s", combo_readonly_after)
    success = False

result_label = tb.Label(
    frame,
    text="✅ Combobox com fundo branco!" if success else "❌ Combobox ainda com problema!",
    font=("Segoe UI", 12, "bold"),
    foreground="green" if success else "red",
)
result_label.pack(pady=20)

root.mainloop()
