# -*- coding: utf-8 -*-
"""
Exemplo de integração do gerenciamento de obrigações no módulo de clientes.

Este arquivo demonstra como adicionar um botão "Obrigações" na toolbar do módulo
de clientes para abrir a janela de gerenciamento de obrigações regulatórias.
"""

from __future__ import annotations

# EXEMPLO 1: Adicionar botão na toolbar do módulo de clientes
# ============================================================
#
# No arquivo: src/modules/clientes/views/toolbar.py
#
# 1. Importar a função:
#
#    from src.modules.clientes.views.client_obligations_window import (
#        show_client_obligations_window,
#    )
#
# 2. Adicionar um botão na toolbar (após o botão "Senhas", por exemplo):
#
#    obligations_btn = tb.Button(
#        self,
#        text="📋 Obrigações",
#        command=self._on_obligations_clicked,
#        bootstyle="info-outline",
#        width=15,
#    )
#    obligations_btn.pack(side=LEFT, padx=(5, 0))
#
# 3. Implementar o callback:
#
#    def _on_obligations_clicked(self):
#        """Handle obligations button click."""
#        # Verificar se há cliente selecionado
#        selection = self.get_selected_client_id()  # método existente
#        if not selection:
#            Messagebox.show_warning(
#                "Selecione um cliente para gerenciar obrigações",
#                "Atenção",
#                parent=self,
#            )
#            return
#
#        client_id = selection
#        client_name = self.get_selected_client_name()  # método existente
#        org_id = get_supabase_state()["org_id"]
#        user_id = get_supabase_state()["user_id"]
#
#        # Abrir janela de obrigações
#        show_client_obligations_window(
#            parent=self.winfo_toplevel(),
#            org_id=org_id,
#            created_by=user_id,
#            client_id=client_id,
#            client_name=client_name,
#            on_refresh_hub=self._refresh_hub_callback,  # opcional
#        )


# EXEMPLO 2: Usar diretamente em qualquer parte do código
# =========================================================
#
# Em qualquer lugar onde você tenha acesso a:
# - parent window (tk root ou toplevel)
# - org_id
# - user_id
# - client_id
#
# Basta importar e chamar:
#
#    from src.modules.clientes.views.client_obligations_window import (
#        show_client_obligations_window,
#    )
#
#    show_client_obligations_window(
#        parent=root,
#        org_id="org-123",
#        created_by="user-456",
#        client_id=5,
#        client_name="Farmácia Central",
#    )


# EXEMPLO 3: Criar aba em um Notebook (se o módulo usar abas)
# ============================================================
#
# Se o módulo de clientes usar um ttk.Notebook para organizar abas,
# você pode adicionar uma aba "Obrigações":
#
#    from src.modules.clientes.views.client_obligations_frame import (
#        ClientObligationsFrame,
#    )
#
#    # Criar aba
#    obligations_tab = ClientObligationsFrame(
#        notebook,
#        org_id=org_id,
#        created_by=user_id,
#        client_id=client_id,
#    )
#    notebook.add(obligations_tab, text="Obrigações")


# EXEMPLO 4: Atualizar Hub após criar/editar obrigação
# =====================================================
#
# Para que o Hub seja atualizado automaticamente após criar/editar
# uma obrigação, passe um callback on_refresh_hub:
#
#    def refresh_hub():
#        # Código para atualizar o dashboard do Hub
#        hub_frame.reload_dashboard()  # ou método equivalente
#
#    show_client_obligations_window(
#        parent=root,
#        org_id=org_id,
#        created_by=user_id,
#        client_id=client_id,
#        on_refresh_hub=refresh_hub,
#    )


# TESTES MANUAIS
# ==============
#
# Para testar manualmente a funcionalidade:
#
# 1. Abra o app (python -m src.app_gui)
# 2. Vá para o módulo de Clientes
# 3. Selecione um cliente
# 4. Clique no botão "Obrigações" (após adicionar na toolbar)
# 5. Teste as operações:
#    - Criar nova obrigação
#    - Editar obrigação existente
#    - Excluir obrigação
#    - Verificar se aparecem no Hub (Radar de riscos, Clientes do dia)
