# ui/lixeira/lixeira.py
import logging
import time
import threading
import ttkbootstrap as tb
from tkinter import messagebox as tkmsg  # avisos nativos (claros)

from core import db_manager
from utils.file_utils import format_datetime
from core.logs.audit import last_client_activity_many
from ui.components import draw_whatsapp_overlays
from ui.utils import center_window
from config.constants import ICON_SIZE_WHATS
from core.services import lixeira_service  # chamadas diretas (evita modal duplicado)

logger = logging.getLogger(__name__)

_AUDIT_BY_ID_CACHE = {}

def _set_audit_cache(mapping: dict[int, tuple]):
    global _AUDIT_BY_ID_CACHE
    _AUDIT_BY_ID_CACHE = mapping or {}
log = logger

# ---------------- helpers de linha (Row/dict) ----------------
def _row_get(row, key, default=None):
    """Compatível com sqlite3.Row e dict."""
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        # sqlite3.Row suporta mapeamento por chave; checa presença:
        if hasattr(row, "keys") and key in row.keys():
            val = row[key]
            return default if val is None else val
        # tentativa direta (pode levantar KeyError)
        val = row[key]  # type: ignore[index]
        return default if val is None else val
    except Exception:
        return default

# ---------------- modais (nativos, claros) ----------------
def _modal_info(parent, title, message):
    try:
        tkmsg.showinfo(title, message, parent=parent)
    except Exception:
        tkmsg.showinfo(title, message)

def _modal_okcancel(parent, title, message):
    try:
        return tkmsg.askokcancel(title, message, parent=parent, default="ok")
    except Exception:
        return tkmsg.askokcancel(title, message)

# ---------------- formatação da coluna ----------------
def _ultima_txt(ts, cid):
    try:
        txt = format_datetime(ts) if ts else ''
    except Exception:
        txt = ''
    try:
        last = _AUDIT_BY_ID_CACHE.get(cid)
        if last:
            lts, user = (last[0], last[1] or '')
            if not txt and lts:
                txt = format_datetime(lts)
            if user:
                txt = (txt + f' ({user})').strip()
    except Exception:
        pass
    return txt or '-'

# ---------------- helpers UI ----------------
def _set_busy(win, buttons, busy: bool):
    try:
        win.configure(cursor="watch" if busy else "")
        for b in buttons:
            try:
                b.configure(state=("disabled" if busy else "normal"))
            except Exception:
                pass
        win.update_idletasks()
    except Exception:
        pass

def _run_bg(win, buttons, work_fn, on_done):
    """Roda work_fn em thread e chama on_done no mainloop."""
    _set_busy(win, buttons, True)
    started = time.perf_counter()

    def _target():
        err = None
        result = None
        try:
            result = work_fn()
        except Exception as e:
            err = e
            logger.exception("Falha na operação da Lixeira: %s", e)
        finally:
            elapsed = time.perf_counter() - started
            def _finish():
                _set_busy(win, buttons, False)
                try:
                    on_done(err, result, elapsed)
                except Exception:
                    logger.exception("Falha no on_done da Lixeira")
            win.after(0, _finish)

    threading.Thread(target=_target, daemon=True).start()

# ---------------- janela da lixeira ----------------
def abrir_lixeira(app):
    # já aberta? foca e recarrega uma vez
    if hasattr(app, "lixeira_win") and app.lixeira_win and tb.Toplevel.winfo_exists(app.lixeira_win):
        logger.info("Lixeira UI: janela já aberta; focando e recarregando")
        app.lixeira_win.focus()
        if hasattr(app.lixeira_win, "carregar_func"):
            app.lixeira_win.carregar_func()
        return

    # cria sem "piscada" (withdraw -> centraliza -> deiconify)
    win = tb.Toplevel(app)
    win.withdraw()
    app.lixeira_win = win
    win.title("Lixeira de Clientes")
    win.geometry("1200x500")
    center_window(win, 1200, 500)
    win.deiconify()
    logger.info("Lixeira UI: janela criada")

    # pedir refresh na tela principal (quando fechar ou após operações)
    def _refresh_main_safely():
        try:
            logger.info("Lixeira UI: pedindo refresh da tela principal")
            app.carregar()
        except Exception:
            logger.exception("Lixeira UI: falha ao atualizar a lista principal")

    def _on_close_lixeira():
        _refresh_main_safely()
        try:
            if hasattr(app, 'lixeira_win'):
                app.lixeira_win = None
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close_lixeira)

    tb.Label(win, text="Clientes na Lixeira", font=("Segoe UI", 12, "bold")).pack(pady=10)

    # ------- Tabela -------
    cols = ("ID", "Razão Social", "CNPJ", "Nome", "WhatsApp", "Observações", "Última Alteração")
    tree = tb.Treeview(win, columns=cols, show="headings", selectmode="extended")

    # Debounce para overlays do WhatsApp (evita flood em <Configure>/<MouseWheel>)
    _whats_after = {'id': None}
    def _schedule_whats_overlays():
        try:
            if _whats_after['id'] is not None:
                win.after_cancel(_whats_after['id'])
        except Exception:
            pass
        try:
            _whats_after['id'] = win.after(60, lambda: (
                draw_whatsapp_overlays(tree, 'WhatsApp', ICON_SIZE_WHATS),
                _whats_after.__setitem__('id', None)
            ))
        except Exception:
            # fallback direto (não quebra a UI)
            try:
                draw_whatsapp_overlays(tree, 'WhatsApp', ICON_SIZE_WHATS)
            except Exception:
                pass

    # ícones do WhatsApp
    tree.bind('<Configure>',   lambda e: _schedule_whats_overlays())
    tree.bind('<MouseWheel>',  lambda e: _schedule_whats_overlays())

    for col, width, anchor in [
        ("ID", 40, "center"),
        ("Razão Social", 200, "w"),
        ("CNPJ", 140, "center"),
        ("Nome", 150, "w"),
        ("WhatsApp", 140, "center"),
        ("Observações", 220, "w"),
        ("Última Alteração", 200, "center"),
    ]:
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor=anchor)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def carregar():
        started = time.perf_counter()
        # limpa a árvore
        for rowid in tree.get_children():
            tree.delete(rowid)
        total = 0
        rows = []
        try:
            # Reutiliza o serviço central de listagem de deletados
            rows = db_manager.list_clientes_deletados(order_by="ID")
        except Exception:
            logger.exception('Lixeira UI: falha ao listar clientes deletados (service)')
            rows = []

        for row in rows or []:
            try:
                cid = _row_get(row, 'ID', None)
                ultima = _ultima_txt(_row_get(row, 'ULTIMA_ALTERACAO', None), cid)
                tree.insert(
                    "", "end",
                    values=(
                        _row_get(row, 'ID', ''),
                        _row_get(row, 'RAZAO_SOCIAL', ''),
                        _row_get(row, 'CNPJ', ''),
                        _row_get(row, 'NOME', ''),
                        _row_get(row, 'NUMERO', '') or '',
                        _row_get(row, 'OBS', '') or '',
                        ultima,
                    )
                )
                total += 1
            except Exception:
                logger.exception('Lixeira UI: falha ao inserir linha na grade (ID=%s)', _row_get(row, 'ID', '?'))

        logger.info('Lixeira UI: carregadas %s linhas em %.3fs', total, time.perf_counter() - started)
        # redesenha overlays após popular a grade
        _schedule_whats_overlays()

    def _get_selected_ids():
        ids = []
        for iid in tree.selection():
            vals = tree.item(iid, "values")
            if vals:
                try:
                    ids.append(int(str(vals[0]).strip()))
                except Exception:
                    pass
        return ids

    def restaurar():
        ids = _get_selected_ids()
        if not ids:
            _modal_info(win, 'Aviso', 'Selecione um ou mais clientes para restaurar.')
            return
        logger.info("Lixeira UI: solicitar RESTORE de %d id(s): %s", len(ids), ids)
        # Confirmação simples antes de restaurar
        if not _modal_okcancel(
            win,
            'Restaurar',
            f'Restaurar {len(ids)} cliente(s) da Lixeira e reativar no sistema?'
        ):
            return

        def _work():
            return lixeira_service.restore_ids(ids)  # -> (ok_db, processadas, falhas)

        def _done(err, result, elapsed):
            if err:
                _modal_info(win, 'Erro', 'Falha ao restaurar. Veja o log.')
                return
            ok_db, processadas, falhas = result
            logger.info(
                'Lixeira UI: RESTORE finalizado em %.3fs -> ok_db=%s, processadas=%s, falhas=%s',
                elapsed, ok_db, processadas, falhas
            )
            # Evita popup duplicado: não mostra diálogo de sucesso aqui.
            # Se houve falhas, mostra um único aviso resumido.
            if falhas and falhas > 0:
                _modal_info(win, 'Parcial', f'Restauradas {processadas - falhas} pasta(s). {falhas} falha(s). Verifique o log.')
            carregar()              # atualiza a lista da Lixeira
            _refresh_main_safely()  # atualiza a tela principal

        _run_bg(win, [btn_restaurar, btn_apagar, btn_refresh, btn_fechar], _work, _done)

    def apagar_definitivo():
        ids = _get_selected_ids()
        if not ids:
            _modal_info(win, 'Aviso', 'Selecione um ou mais clientes para apagar definitivamente.')
            return
        if not _modal_okcancel(
            win,
            "Apagar definitivamente",
            f"Remover {len(ids)} cliente(s) de forma irreversível?\n"
            "Esta ação não pode ser desfeita."
        ):
            return
        logger.info("Lixeira UI: solicitar PURGE de %d id(s): %s", len(ids), ids)

    # --- PURGE mantido como estava no seu arquivo anterior ---
        def _work():
            return lixeira_service.purge_ids(ids)  # -> (ok_db, removidas)

        def _done(err, result, elapsed):
            if err:
                _modal_info(win, "Erro", "Falha ao apagar definitivamente. Veja o log.")
                return
            ok_db, removidas = result
            logger.info(
                "Lixeira UI: PURGE finalizado em %.3fs -> removidos_bd=%s, pastas_apagadas=%s",
                elapsed, ok_db, removidas
            )
            _modal_info(win, "Lixeira", f"Removidos do banco: {ok_db}\nPastas apagadas: {removidas}")
            carregar()              # atualiza a lista da Lixeira
            _refresh_main_safely()  # atualiza a tela principal

        _run_bg(win, [btn_restaurar, btn_apagar, btn_refresh, btn_fechar], _work, _done)

    def _on_key(event):
        if event.keysym == "Delete":
            apagar_definitivo(); return "break"
        if event.keysym.lower() == "r" and (event.state & 0x4):
            restaurar(); return "break"
        if event.keysym == "F5":
            carregar(); return "break"
    tree.bind("<Key>", _on_key)

    # ------- Rodapé -------
    btn_frame = tb.Frame(win)
    btn_frame.pack(fill="x", pady=10)

    btn_restaurar = tb.Button(btn_frame, text="Restaurar Selecionados", bootstyle="success",
                              command=restaurar)
    btn_restaurar.pack(side="left", padx=5)

    btn_apagar = tb.Button(btn_frame, text="Apagar Selecionados", bootstyle="danger",
                           command=apagar_definitivo)
    btn_apagar.pack(side="left", padx=5)

    btn_fechar = tb.Button(btn_frame, text="Fechar", bootstyle="secondary",
                           command=_on_close_lixeira)
    btn_fechar.pack(side="right", padx=5)

    btn_refresh = tb.Button(
        btn_frame, text="↻", width=3, bootstyle="secondary",
        command=lambda: (logger.info("Refresh manual (↻) - Lixeira"), carregar())
    )
    btn_refresh.pack(side="right", padx=5)

    # expõe função de recarregar para outras telas
    win.carregar_func = carregar
    # carga inicial
    carregar()
