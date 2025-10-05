# main.py
import logging, sys
from core import db_manager
from app_gui import App
from ui.login import LoginDialog

# ---- LOG no console ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("startup")

if __name__ == "__main__":
    log.info("Iniciando aplicação...")

    db_manager.init_db()
    log.info("Banco inicializado.")

    # root único (App) já nasce com o tema salvo; esconde para login
    app = App(start_hidden=True)
    log.info("App criado (root único). Abrindo login...")

    dlg = LoginDialog(app)
    app.wait_window(dlg)
    log.info("Login fechado. Resultado: %s", dlg.result)

    if dlg.result:
        log.info("Login OK. Mostrando App...")
        app.deiconify()
        try:
            app._update_user_status()
        except Exception:
            pass
        app.mainloop()
    else:
        log.info("Login cancelado ou inválido.")
        app.destroy()
