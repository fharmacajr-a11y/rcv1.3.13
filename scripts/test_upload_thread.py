"""
Script de teste para verificar a UI responsiva do upload de arquivos.

Testa:
1. Modal de progresso aparece e é responsivo
2. Cancelamento funciona
3. UI não trava durante processamento
"""
import tkinter as tk
from ttkbootstrap import ttk
import threading
import time


class TestUploadWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Teste de Upload Responsivo")
        self.geometry("400x300")
        
        ttk.Label(
            self,
            text="Teste de Upload com Thread",
            font=("-size", 14, "-weight", "bold")
        ).pack(pady=20)
        
        ttk.Button(
            self,
            text="Iniciar Upload (5s)",
            command=self.start_upload
        ).pack(pady=10)
        
        ttk.Button(
            self,
            text="Teste: UI ainda responde?",
            command=lambda: print("✓ UI responsiva!")
        ).pack(pady=10)
        
        self.label_status = ttk.Label(self, text="", foreground="green")
        self.label_status.pack(pady=10)
    
    def start_upload(self):
        """Simula upload com modal de progresso."""
        self._show_busy("Processando", "Simulando upload...")
        threading.Thread(target=self._worker, daemon=True).start()
    
    def _show_busy(self, titulo: str, msg: str):
        """Modal de progresso indeterminado."""
        self._busy = tk.Toplevel(self)
        self._busy.title(titulo)
        self._busy.transient(self)  # type: ignore
        self._busy.grab_set()
        self._busy.resizable(False, False)
        
        # Centralizar
        self._busy.update_idletasks()
        w, h = 360, 160
        x = (self._busy.winfo_screenwidth() // 2) - (w // 2)
        y = (self._busy.winfo_screenheight() // 2) - (h // 2)
        self._busy.geometry(f"{w}x{h}+{x}+{y}")
        
        ttk.Label(self._busy, text=msg).pack(padx=20, pady=(20, 12))
        
        self._pb = ttk.Progressbar(self._busy, mode="indeterminate", length=300)
        self._pb.pack(padx=20, pady=(0, 16), fill="x")
        self._pb.start(12)
        
        self._cancel_flag = False
        
        def cancel():
            self._cancel_flag = True
            btn.configure(state="disabled", text="Cancelando...")
        
        btn = ttk.Button(self._busy, text="Cancelar", command=cancel)
        btn.pack(pady=(0, 20))
    
    def _worker(self):
        """Simula trabalho pesado (5 segundos)."""
        for i in range(50):
            if self._cancel_flag:
                self.after(0, lambda: self._finish("Cancelado pelo usuário"))
                return
            time.sleep(0.1)  # simula processamento
        
        self.after(0, lambda: self._finish("Upload concluído com sucesso!"))
    
    def _finish(self, msg: str):
        """Fecha modal e mostra resultado."""
        try:
            self._pb.stop()
            self._busy.destroy()
        except:
            pass
        
        self.label_status.configure(text=msg)
        print(f"[RESULTADO] {msg}")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE: UI Responsiva com Thread")
    print("=" * 60)
    print("\n1. Clique em 'Iniciar Upload (5s)'")
    print("2. Durante o progresso, clique em 'Teste: UI ainda responde?'")
    print("3. Se aparecer '✓ UI responsiva!' no console, está OK!")
    print("4. Teste também o botão 'Cancelar'\n")
    
    app = TestUploadWindow()
    app.mainloop()
