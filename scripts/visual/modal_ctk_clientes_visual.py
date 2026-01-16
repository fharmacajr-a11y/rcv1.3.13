#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script visual para testar ClientesModalCTK (requer CustomTkinter).

Execute manualmente:
    python scripts/visual/modal_ctk_clientes_visual.py

Microfase: 6 (Subdialogs CustomTkinter)
"""

import sys
from pathlib import Path

# Adicionar src/ ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

try:
    from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
    from src.modules.clientes.ui import ClientesModalCTK
    from src.modules.clientes.appearance import ClientesThemeManager

    if not HAS_CUSTOMTKINTER:
        raise ImportError("CustomTkinter não disponível")
except ImportError as e:
    print(f"❌ Erro ao importar CustomTkinter: {e}")
    print("\nInstale com: pip install customtkinter")
    sys.exit(1)


class ModalTestApp:
    """App de teste para ClientesModalCTK."""

    def __init__(self):
        """Inicializa o app."""
        self.theme_manager = ClientesThemeManager()

        # Configurar tema
        mode = self.theme_manager.load_mode()
        ctk.set_appearance_mode(mode)

        # Janela principal
        self.root = ctk.CTk()
        self.root.title("Teste Visual - ClientesModalCTK")
        self.root.geometry("600x500")

        # Frame principal
        frame = ctk.CTkFrame(self.root)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        title = ctk.CTkLabel(
            frame,
            text="🎨 Teste Visual - ClientesModalCTK",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(pady=(0, 20))

        # Descrição
        desc = ctk.CTkLabel(
            frame,
            text="Clique nos botões abaixo para testar os modals CustomTkinter.\nOs modais devem seguir o tema Light/Dark automaticamente.",
            justify="center",
            wraplength=500,
        )
        desc.pack(pady=(0, 20))

        # Botões de teste
        btn_confirm = ctk.CTkButton(
            frame,
            text="❓ Testar Confirm (Sim/Não)",
            command=self.test_confirm,
            width=400,
            height=40,
        )
        btn_confirm.pack(pady=5)

        btn_alert = ctk.CTkButton(
            frame,
            text="⚠️ Testar Alert (Aviso)",
            command=self.test_alert,
            width=400,
            height=40,
        )
        btn_alert.pack(pady=5)

        btn_error = ctk.CTkButton(
            frame,
            text="❌ Testar Error (Erro)",
            command=self.test_error,
            width=400,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
        )
        btn_error.pack(pady=5)

        btn_info = ctk.CTkButton(
            frame,
            text="ℹ️ Testar Info (Informação)",
            command=self.test_info,
            width=400,
            height=40,
        )
        btn_info.pack(pady=5)

        # Separador
        separator = ctk.CTkFrame(frame, height=2, fg_color="gray")
        separator.pack(fill="x", pady=20)

        # Toggle de tema
        btn_toggle = ctk.CTkButton(
            frame,
            text="🌓 Alternar Light/Dark",
            command=self.toggle_theme,
            width=400,
            height=40,
        )
        btn_toggle.pack(pady=5)

        # Label de resultado
        self.result_label = ctk.CTkLabel(
            frame,
            text="",
            font=("Segoe UI", 11),
        )
        self.result_label.pack(pady=10)

    def test_confirm(self):
        """Testa modal de confirmação."""
        result = ClientesModalCTK.confirm(
            parent=self.root,
            title="Confirmação",
            message="Você deseja continuar com esta operação?",
            theme_manager=self.theme_manager,
        )
        self.result_label.configure(text=f"✓ Confirm retornou: {result} ({'Sim' if result else 'Não'})")

    def test_alert(self):
        """Testa modal de alerta."""
        ClientesModalCTK.alert(
            parent=self.root,
            title="Aviso",
            message="Esta é uma mensagem de aviso.\n\nVerifique as informações antes de prosseguir.",
            theme_manager=self.theme_manager,
        )
        self.result_label.configure(text="✓ Alert exibido")

    def test_error(self):
        """Testa modal de erro."""
        ClientesModalCTK.error(
            parent=self.root,
            title="Erro",
            message="Ocorreu um erro ao processar a operação.\n\nDetalhes: Arquivo não encontrado.",
            theme_manager=self.theme_manager,
        )
        self.result_label.configure(text="✓ Error exibido")

    def test_info(self):
        """Testa modal de informação."""
        ClientesModalCTK.info(
            parent=self.root,
            title="Informação",
            message="Operação concluída com sucesso!\n\nTodos os dados foram salvos.",
            theme_manager=self.theme_manager,
        )
        self.result_label.configure(text="✓ Info exibido")

    def toggle_theme(self):
        """Alterna entre Light e Dark."""
        current = self.theme_manager.load_mode()
        new_mode = "dark" if current == "light" else "light"
        self.theme_manager.save_mode(new_mode)
        ctk.set_appearance_mode(new_mode)
        self.result_label.configure(text=f"✓ Tema alterado para: {new_mode.upper()}")

    def run(self):
        """Executa o app."""
        print("✓ App iniciado - teste os modais clicando nos botões")
        print("✓ Use 'Alternar Light/Dark' para testar temas")
        print("✓ Feche a janela para sair")
        self.root.mainloop()


if __name__ == "__main__":
    app = ModalTestApp()
    app.run()
