# -*- coding: utf-8 -*-

# ui/forms/forms.py

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional, Tuple

try:
    import ttkbootstrap as tb
except Exception:
    tb = ttk  # type: ignore

from src.app_gui import apply_rc_icon
from src.modules.clientes.components.helpers import STATUS_CHOICES, STATUS_PREFIX_RE
from src.modules.passwords.helpers import open_senhas_for_cliente
from src.ui.window_utils import show_centered
from ._collect import coletar_valores as _collect_values
from ._dupes import (
    ask_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)
from . import client_form_actions
from . import client_form_upload_actions

logger = logging.getLogger(__name__)
log = logger


ClientRow = Tuple[Any, ...]
FormPreset = dict[str, str]
EntryMap = dict[str, tk.Widget]
UploadButtonRef = dict[str, tk.Widget | None]


# -----------------------------------------------------------------------------
# Adaptadores para client_form_actions
# -----------------------------------------------------------------------------


class TkMessageAdapter:
    """Adaptador para messagebox do Tkinter."""

    def __init__(self, parent: tk.Misc | None = None) -> None:
        self.parent = parent

    def warn(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.parent)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return messagebox.askokcancel(title, message, parent=self.parent)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.parent)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self.parent)


class FormDataAdapter:
    """Adaptador para coletar dados do formulário Tkinter."""

    def __init__(self, ents: EntryMap, status_var: tk.StringVar) -> None:
        self.ents = ents
        self.status_var = status_var

    def collect(self) -> dict[str, str]:
        return _collect_values(self.ents)

    def get_status(self) -> str:
        return self.status_var.get().strip()


# -----------------------------------------------------------------------------
# Wrappers de Compatibilidade (Round 14 + FIX-TESTS-001)
# -----------------------------------------------------------------------------


def center_on_parent(win: tk.Misc) -> bool:
    """Wrapper de compatibilidade para centralização de janela.

    Mantido para compatibilidade com testes que importam center_on_parent
    de client_form.py. A implementação real vive em src.ui.window_utils.

    Args:
        win: Janela a ser centralizada.

    Returns:
        True se centralização foi bem-sucedida, False caso contrário.
    """
    from src.ui.window_utils import center_on_parent as _impl

    return _impl(win)


def apply_status_prefix(observacoes: str, status: str) -> str:
    """
    Wrapper de compatibilidade para aplicar prefixo de status nas observações.

    Mantido para compatibilidade com testes antigos que importam
    apply_status_prefix de client_form.py. A implementação real vive em
    src.modules.clientes.components.status.
    """
    from src.modules.clientes.components.status import apply_status_prefix as _impl

    return _impl(observacoes, status)


def salvar_cliente_a_partir_do_form(*args: Any, **kwargs: Any) -> Any:
    """
    Wrapper de compatibilidade para salvar cliente a partir do form.

    Delegado para src.modules.clientes.service.salvar_cliente_a_partir_do_form.
    """
    from src.modules.clientes.service import salvar_cliente_a_partir_do_form as _impl

    return _impl(*args, **kwargs)


def checar_duplicatas_para_form(*args: Any, **kwargs: Any) -> Any:
    """
    Wrapper de compatibilidade para checar duplicatas antes de salvar.

    Delegado para src.modules.clientes.service.checar_duplicatas_para_form.
    """
    from src.modules.clientes.service import checar_duplicatas_para_form as _impl

    return _impl(*args, **kwargs)


def preencher_via_pasta(*args: Any, **kwargs: Any) -> Any:
    """
    Wrapper de compatibilidade para preencher formulário via pasta (Cartão CNPJ).

    Delegado para src.ui.forms.actions.preencher_via_pasta.
    """
    from src.ui.forms.actions import preencher_via_pasta as _impl

    return _impl(*args, **kwargs)


def form_cliente(self: tk.Misc, row: ClientRow | None = None, preset: FormPreset | None = None) -> None:
    try:
        parent_window: tk.Misc = self.winfo_toplevel()  # type: ignore[assignment]
    except Exception:
        parent_window = self

    win = tk.Toplevel(parent_window)
    apply_rc_icon(win)
    win.withdraw()
    try:
        win.transient(parent_window)
    except Exception:
        win.transient(self)
    win.resizable(False, False)
    win.minsize(940, 520)

    main_frame = ttk.Frame(win, padding=(8, 8, 8, 2))
    main_frame.grid(row=0, column=0, sticky="nsew")
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)

    left_frame = ttk.Frame(main_frame)
    sep = ttk.Separator(main_frame, orient="vertical")
    right_frame = ttk.Frame(main_frame)
    main_frame.columnconfigure(0, weight=3)
    main_frame.columnconfigure(1, weight=0)
    main_frame.columnconfigure(2, weight=4)
    main_frame.rowconfigure(0, weight=1)

    left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
    sep.grid(row=0, column=1, sticky="ns", padx=(0, 0), pady=10)
    right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
    left_frame.columnconfigure(0, weight=1)
    right_frame.columnconfigure(0, weight=1)

    ents: EntryMap = {}
    row_idx = 0

    def _apply_light_selection(widget: tk.Widget) -> None:
        """
        Tenta aplicar uma cor de selecao mais clara nos widgets que suportam.
        Em ttk/ttkbootstrap, muitas vezes selectbackground nao existe; nesse caso,
        simplesmente ignora silenciosamente para nao poluir o log.
        """
        try:
            widget.configure(
                selectbackground="#5bc0de",  # azul claro
                selectforeground="#000000",  # texto preto
            )
        except tk.TclError:
            # Widget (por ex. ttk.Entry) nao suporta essas opcoes; mantem selecao padrao.
            # Nao loga nada para evitar spam no console.
            pass

    # Razão Social
    ttk.Label(left_frame, text="Razão Social:").grid(row=row_idx, column=0, sticky="w", padx=6, pady=(5, 0))
    row_idx += 1
    ent_razao = ttk.Entry(left_frame)
    ent_razao.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=(0, 5))
    row_idx += 1
    ents["Razão Social"] = ent_razao

    # CNPJ
    ttk.Label(left_frame, text="CNPJ:").grid(row=row_idx, column=0, sticky="w", padx=6, pady=(0, 0))
    row_idx += 1
    ent_cnpj = ttk.Entry(left_frame)
    ent_cnpj.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=(0, 5))
    row_idx += 1
    ents["CNPJ"] = ent_cnpj

    # Nome
    ttk.Label(left_frame, text="Nome:").grid(row=row_idx, column=0, sticky="w", padx=6, pady=(0, 0))
    row_idx += 1
    ent_nome = ttk.Entry(left_frame)
    ent_nome.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=(0, 5))
    row_idx += 1
    ents["Nome"] = ent_nome

    # WhatsApp
    ttk.Label(left_frame, text="WhatsApp:").grid(row=row_idx, column=0, sticky="w", padx=6, pady=(0, 0))
    row_idx += 1
    ent_whats = ttk.Entry(left_frame)
    ent_whats.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=(0, 5))
    row_idx += 1
    ents["WhatsApp"] = ent_whats

    # Observações
    ttk.Label(left_frame, text="Observações:").grid(row=row_idx, column=0, sticky="w", padx=6, pady=(0, 0))
    row_idx += 1
    ent_obs = tk.Text(left_frame, width=52, height=7)
    ent_obs.grid(row=row_idx, column=0, padx=6, pady=(0, 5), sticky="nsew")
    obs_row_for_weight = row_idx
    row_idx += 1
    ents["Observações"] = ent_obs

    left_frame.rowconfigure(obs_row_for_weight, weight=1)
    left_frame.columnconfigure(0, weight=1)
    try:
        current_client_id: int | None = int(row[0]) if row else None
    except Exception:
        current_client_id = None
    initializing: list[bool] = [True]
    _upload_button_ref: UploadButtonRef = {"btn": None}

    def _set_button_enabled(button: ttk.Button | None, enabled: bool) -> None:
        if button is None:
            return
        try:
            if enabled:
                button.state(["!disabled"])
            else:
                button.state(["disabled"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao alterar estado do botao de upload: %s", exc)
            try:
                button.configure(state="normal" if enabled else "disabled")
            except Exception as inner_exc:  # noqa: BLE001
                logger.debug("Falha ao configurar estado fallback do botao de upload: %s", inner_exc)

    def _refresh_send_button() -> None:
        _set_button_enabled(_upload_button_ref["btn"], True)

    class _EditFormState:
        def __init__(self, client_id: Optional[int]) -> None:
            self.client_id: Optional[int] = client_id
            self.is_dirty: bool = False

        def mark_dirty(self, *_args, **_kwargs) -> None:
            if initializing[0]:
                return
            if not self.is_dirty:
                self.is_dirty = True

        def mark_clean(self) -> None:
            if self.is_dirty:
                self.is_dirty = False

        def save_silent(self) -> bool:
            return _perform_save(show_success=False, close_window=False, refresh_list=True, update_row=True)

    state = _EditFormState(current_client_id)
    _refresh_send_button()

    def _bind_dirty(widget: tk.Widget) -> None:
        try:
            widget.bind("<KeyRelease>", state.mark_dirty, add="+")
            widget.bind("<<Paste>>", state.mark_dirty, add="+")
            widget.bind("<<Cut>>", state.mark_dirty, add="+")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao registrar eventos de dirty em form_cliente: %s", exc)

    if hasattr(self, "register_edit_form"):
        try:
            self.register_edit_form(win, state)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao registrar form_cliente no host: %s", exc)
    # --- Seção: Status do Cliente ---
    # TODO: campos de endereço interno (4) ainda não são persistidos no banco; mantidos apenas em memória.
    addr_endereco_var = tk.StringVar(value="")
    addr_bairro_var = tk.StringVar(value="")
    addr_cidade_var = tk.StringVar(value="")
    addr_cep_var = tk.StringVar(value="")
    cliente_like: Any | None = None
    if row and not isinstance(row, tuple):
        cliente_like = row
    if cliente_like is None:
        for cand in ("_cliente_atual", "cliente_atual", "cliente"):
            src_cand = getattr(self, cand, None)
            if src_cand is not None:
                cliente_like = src_cand
                break

    def _addr_val(src: Any | None, *keys: str) -> str:
        if src is None:
            return ""
        for key in keys:
            if isinstance(src, dict) and key in src:
                val = src.get(key)
                if val:
                    return str(val)
            try:
                converted = str(getattr(src, key))
            except Exception:
                logger.debug("Falha ao converter atributo %r em string em _addr_val", key, exc_info=True)
            else:
                if converted:
                    return converted
        return ""

    endereco_val = _addr_val(cliente_like, "endereco", "endereço", "address", "logradouro")
    bairro_val = _addr_val(cliente_like, "bairro", "district")
    cidade_val = _addr_val(cliente_like, "cidade", "city", "municipio")
    cep_val = _addr_val(cliente_like, "cep", "zip", "postal_code")
    addr_endereco_var.set(endereco_val)
    addr_bairro_var.set(bairro_val)
    addr_cidade_var.set(cidade_val)
    addr_cep_var.set(cep_val)
    internal_vars = {
        "endereco": addr_endereco_var,
        "bairro": addr_bairro_var,
        "cidade": addr_cidade_var,
        "cep": addr_cep_var,
    }
    internal_entries: dict[str, ttk.Entry] = {}
    right_row = 0

    ttk.Label(right_frame, text="Endereço (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(5, 0))
    right_row += 1
    ent_endereco = ttk.Entry(right_frame, textvariable=addr_endereco_var)
    ent_endereco.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
    ents["Endereço (interno):"] = ent_endereco
    internal_entries["Endereço (interno):"] = ent_endereco
    right_row += 1

    ttk.Label(right_frame, text="Bairro (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
    right_row += 1
    ent_bairro = ttk.Entry(right_frame, textvariable=addr_bairro_var)
    ent_bairro.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
    ents["Bairro (interno):"] = ent_bairro
    internal_entries["Bairro (interno):"] = ent_bairro
    right_row += 1

    ttk.Label(right_frame, text="Cidade (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
    right_row += 1
    ent_cidade = ttk.Entry(right_frame, textvariable=addr_cidade_var)
    ent_cidade.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
    ents["Cidade (interno):"] = ent_cidade
    internal_entries["Cidade (interno):"] = ent_cidade
    right_row += 1

    ttk.Label(right_frame, text="CEP (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
    right_row += 1
    ent_cep = ttk.Entry(right_frame, textvariable=addr_cep_var)
    ent_cep.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
    ents["CEP (interno):"] = ent_cep
    internal_entries["CEP (interno):"] = ent_cep
    right_row += 1
    right_frame._rc_internal_notes_vars = internal_vars  # type: ignore[attr-defined]
    right_frame._rc_internal_notes_entries = internal_entries  # type: ignore[attr-defined]
    win._rc_internal_notes_vars = internal_vars  # type: ignore[attr-defined]
    win._rc_internal_notes_entries = internal_entries  # type: ignore[attr-defined]
    right_frame.rowconfigure(right_row, weight=1)

    def _safe_text(widget: tk.Widget | None) -> str:
        if widget is None:
            return ""
        try:
            return widget.get().strip()  # type: ignore[attr-defined]
        except Exception:
            return ""

    def _update_title() -> None:
        parts: list[str] = ["Editar Cliente"]
        cid = state.client_id or current_client_id
        if cid:
            parts.append(str(cid))
        razao_txt = _safe_text(ents.get("Razão Social"))
        if razao_txt:
            parts.append(razao_txt)
        cnpj_txt = _safe_text(ents.get("CNPJ"))
        if cnpj_txt:
            parts.append(cnpj_txt)
        win.title(" – ".join(parts))

    selection_targets = [
        ent_razao,
        ent_cnpj,
        ent_nome,
        ent_whats,
        ent_obs,
        ent_endereco,
        ent_bairro,
        ent_cidade,
        ent_cep,
    ]
    for widget in selection_targets:
        _apply_light_selection(widget)

    status_frame = ttk.LabelFrame(left_frame, text="Status do Cliente:")
    status_frame.grid(row=row_idx, column=0, columnspan=1, sticky="ew", padx=6, pady=(6, 6))
    status_frame.columnconfigure(0, weight=1)
    status_frame.columnconfigure(1, weight=0)
    status_var = tk.StringVar(value="")
    cb_status = ttk.Combobox(status_frame, textvariable=status_var, values=STATUS_CHOICES, state="readonly")
    cb_status.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
    ents["Status do Cliente"] = cb_status

    def _on_senhas_clicked() -> None:
        cid = state.client_id or current_client_id
        if not cid:
            messagebox.showinfo("Senhas do Cliente", "Salve o cliente antes de abrir as senhas.", parent=win)
            return
        try:
            razao_val = ents.get("Razão Social")
            razao_text = razao_val.get().strip() if razao_val else ""
        except Exception:
            razao_text = ""
        try:
            open_senhas_for_cliente(win, str(cid), razao_social=razao_text)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao abrir senhas do cliente: %s", exc)
            messagebox.showerror("Erro", f"Falha ao abrir senhas: {exc}", parent=win)

    btn_senhas = tb.Button(
        status_frame,
        text="Senhas",
        command=_on_senhas_clicked,
        bootstyle="secondary",
    )
    btn_senhas.grid(row=0, column=1, sticky="w", padx=6, pady=6)
    # preencher valores iniciais
    if row:
        pk, razao, cnpj, nome, numero, obs, ult = row
        ents["Razão Social"].insert(0, razao or "")
        ents["CNPJ"].insert(0, cnpj or "")
        ents["Nome"].insert(0, nome or "")
        ents["WhatsApp"].insert(0, numero or "")
        ents["Observações"].insert("1.0", obs or "")
        # Pré-preenche status ao editar
        try:
            obs_raw = ents["Observações"].get("1.0", "end").strip()
            m = STATUS_PREFIX_RE.match(obs_raw)
            if m:
                status_var.set(m.group("st"))
                ents["Observações"].delete("1.0", "end")
                ents["Observações"].insert("1.0", STATUS_PREFIX_RE.sub("", obs_raw, count=1).strip())
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao extrair prefixo de status no form_cliente: %s", exc)
    elif preset:
        if preset.get("razao"):
            ents["Razão Social"].insert(0, preset["razao"])
        if preset.get("cnpj"):
            ents["CNPJ"].insert(0, preset["cnpj"])
    for widget in ents.values():
        _bind_dirty(widget)
    cb_status.bind("<<ComboboxSelected>>", state.mark_dirty, add="+")
    status_var.trace_add("write", lambda *_: state.mark_dirty())

    def _confirmar_duplicatas(
        val: dict[str, str],
        row: ClientRow | None = None,
        win: tk.Misc | None = None,
        *,
        exclude_id: Optional[int] = None,
    ) -> bool:
        info = checar_duplicatas_para_form(val, row=row, exclude_id=exclude_id)
        if has_cnpj_conflict(info):
            show_cnpj_warning_and_abort(win, info)
            return False
        if has_razao_conflict(info):
            if not ask_razao_confirm(win, info):
                return False
        return True

    def _perform_save(
        *,
        show_success: bool,
        close_window: bool,
        refresh_list: bool = True,
        update_row: bool = True,
    ) -> bool:
        nonlocal row

        # Criar adaptadores para o módulo headless
        msg_adapter = TkMessageAdapter(parent=win)
        data_adapter = FormDataAdapter(ents, status_var)

        # Montar contexto
        ctx = client_form_actions.ClientFormContext(
            is_new=(current_client_id is None),
            client_id=state.client_id or current_client_id,
            row=row,
            duplicate_check_exclude_id=current_client_id,
        )

        # Montar dependências
        deps = client_form_actions.ClientFormDeps(
            messages=msg_adapter,
            data_collector=data_adapter,
            parent_window=win,
        )

        # Delegar ao módulo headless
        ctx = client_form_actions.perform_save(ctx, deps, show_success=show_success)

        # Processar resultado
        if ctx.abort:
            return False

        # Atualizar estado local
        if ctx.saved_id:
            state.client_id = ctx.saved_id
            state.mark_clean()
            _update_title()

            if update_row:
                if row:
                    row = (ctx.saved_id,) + tuple(row[1:])
                else:
                    row = (ctx.saved_id,)

        try:
            _refresh_send_button()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar botao de envio apos salvar cliente: %s", exc)

        if refresh_list:
            try:
                self.carregar()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao recarregar lista apos salvar cliente: %s", exc)

        if close_window:
            try:
                if hasattr(self, "unregister_edit_form"):
                    self.unregister_edit_form(win)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao remover form_cliente do host: %s", exc)
            win.destroy()

        return True

    def _persist_client(*, refresh_list: bool = False, update_row: bool = False) -> bool:
        """
        Salva cliente sem fechar a janela nem for?ar refresh da lista.
        """
        return _perform_save(
            show_success=False,
            close_window=False,
            refresh_list=refresh_list,
            update_row=update_row,
        )

    def _salvar() -> bool:
        ok = _perform_save(show_success=True, close_window=True)
        return ok

    def _salvar_e_enviar() -> None:
        nonlocal row

        # Adaptador para persistir cliente antes do upload
        class TkClientPersistence:
            """Adaptador para persistir cliente antes do upload."""

            def persist_if_new(self, client_id: int | None) -> tuple[bool, int | None]:
                """Salva o cliente se for novo, retorna (success, client_id)."""
                if client_id is not None:
                    return (True, client_id)

                # Cliente novo: salvar
                created_ok = _persist_client(refresh_list=False, update_row=False)
                if not created_ok:
                    return (False, None)

                # Atualizar row nonlocal
                nonlocal row
                if state.client_id is not None:
                    row = (state.client_id,)

                # Marcar estado como limpo
                try:
                    state.is_dirty = False
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao marcar estado limpo apos criacao: %s", exc)

                return (True, state.client_id)

        # Adaptador para executar upload (usa lógica unificada de upload existente)
        class TkUploadExecutor:
            """Adaptador que delega para a lógica de upload unificada."""

            def execute_upload(
                self,
                host: Any,
                row: tuple[Any, ...] | None,
                ents: dict[str, Any],
                arquivos_selecionados: list | None,
                win: Any,
                **kwargs: Any,
            ) -> Any:
                """Executa upload delegando para módulo de upload unificado."""
                parent_widget = win or host

                # Importar helpers de formatação e lógica de upload
                from src.modules.clientes.forms.client_form_upload_helpers import (
                    execute_upload_flow,
                )

                # Delegar para helper headless
                try:
                    execute_upload_flow(
                        parent_widget=parent_widget,
                        ents=ents,
                        client_id=state.client_id,
                        host=host,
                    )
                except Exception as exc:
                    logger.exception("Erro durante upload de documentos")
                    messagebox.showerror("Erro", f"Erro durante upload: {exc}", parent=parent_widget)

                return None

        # Preparar contexto de upload
        upload_ctx = client_form_upload_actions.prepare_upload_context(
            client_id=state.client_id,
            row=row,
            ents=ents,
            win=win,
            arquivos_selecionados=None,
        )

        # Preparar dependências
        upload_deps = client_form_upload_actions.UploadDeps(
            executor=TkUploadExecutor(),
            persistence=TkClientPersistence(),
            host=self,
        )

        # Executar fluxo de salvar e enviar
        upload_ctx = client_form_upload_actions.execute_salvar_e_enviar(upload_ctx, upload_deps)

        # Processar resultado
        if upload_ctx.abort:
            logger.warning("Upload abortado: %s", upload_ctx.error_message or "Razão desconhecida")
            return

        # Atualizar estado local se cliente foi criado
        if upload_ctx.newly_created and upload_ctx.client_id:
            state.client_id = upload_ctx.client_id
            if row is None or len(row) == 0:
                row = (upload_ctx.client_id,)

    # --- Botões ---
    btns = ttk.Frame(win)
    btns.grid(row=1, column=0, columnspan=3, sticky="w", pady=10, padx=10)
    btn_salvar = tb.Button(btns, text="Salvar", command=_salvar, bootstyle="success")
    btn_salvar.pack(side="left", padx=5)
    # Botão Cartão CNPJ com bloqueio de múltiplas aberturas
    btn_cartao_cnpj = tb.Button(btns, text="Cartão CNPJ", command=lambda: None, bootstyle="info")
    btn_cartao_cnpj.pack(side="left", padx=5)
    # Flag para controlar reentrância
    _cnpj_busy = [False]  # usar lista para mutabilidade em closure

    def _on_cartao_cnpj() -> None:
        """Handler com bloqueio de múltiplos cliques usando módulo headless CF-3."""
        if _cnpj_busy[0]:
            return
        _cnpj_busy[0] = True
        try:
            # Desativa visualmente o botão
            try:
                btn_cartao_cnpj.state(["disabled"])
            except Exception as exc:  # noqa: BLE001
                try:
                    btn_cartao_cnpj.configure(state="disabled")
                except Exception as inner_exc:  # noqa: BLE001
                    logger.debug("Falha ao desativar botao Cartao CNPJ: %s / %s", exc, inner_exc)

            # --- CF-3: Delegação para módulo headless ---
            from src.modules.clientes.forms.client_form_cnpj_actions import (
                CnpjActionDeps,
                handle_cartao_cnpj_action,
            )

            # Adaptador para mensagens
            class _TkMessageSink:
                def warn(self, title: str, message: str) -> None:
                    messagebox.showwarning(title, message, parent=win)

                def info(self, title: str, message: str) -> None:
                    messagebox.showinfo(title, message, parent=win)

            # Adaptador para seleção de diretório
            class _TkDirectorySelector:
                def select_directory(self, title: str) -> str | None:
                    return filedialog.askdirectory(title=title, parent=win)

            # Adaptador para preenchimento de campos
            class _TkFormFieldSetter:
                def set_value(self, field_name: str, value: str) -> None:
                    if field_name in ents:
                        widget = ents[field_name]
                        widget.delete(0, "end")
                        widget.insert(0, value)

            deps = CnpjActionDeps(
                messages=_TkMessageSink(),
                field_setter=_TkFormFieldSetter(),
                directory_selector=_TkDirectorySelector(),
            )

            result = handle_cartao_cnpj_action(deps)

            # Marca formulário como modificado se houve sucesso
            if result.ok:
                state.mark_dirty()

        finally:
            # Reativa o botão após o processamento
            _cnpj_busy[0] = False
            try:
                btn_cartao_cnpj.state(["!disabled"])
            except Exception as exc:  # noqa: BLE001
                try:
                    btn_cartao_cnpj.configure(state="normal")
                except Exception as inner_exc:  # noqa: BLE001
                    logger.debug("Falha ao reativar botao Cartao CNPJ: %s / %s", exc, inner_exc)

    btn_cartao_cnpj.configure(command=_on_cartao_cnpj)
    btn_salvar_enviar = tb.Button(btns, text="Enviar documentos", command=_salvar_e_enviar, bootstyle="info")
    btn_salvar_enviar.pack(side="left", padx=5)
    _upload_button_ref["btn"] = btn_salvar_enviar
    _refresh_send_button()

    def _cancelar() -> None:
        try:
            if hasattr(self, "unregister_edit_form"):
                self.unregister_edit_form(win)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao cancelar registro do form_cliente: %s", exc)
        win.destroy()

    tb.Button(btns, text="Cancelar", command=_cancelar, bootstyle="danger").pack(side="left", padx=5)

    def _on_close() -> None:
        try:
            if hasattr(self, "unregister_edit_form"):
                self.unregister_edit_form(win)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao remover registro do form_cliente ao fechar: %s", exc)
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)
    initializing[0] = False

    # Centraliza e mostra (apenas uma vez, após todo o layout estar montado)
    logger.debug("[FORM_CLIENTE] Antes de update_idletasks()")
    win.update_idletasks()
    logger.debug("[FORM_CLIENTE] Antes de show_centered()")
    show_centered(win)
    logger.debug("[FORM_CLIENTE] Após show_centered()")

    # Verifica estado da janela
    try:
        window_state = win.state()
        geometry = win.geometry()
        logger.debug(f"[FORM_CLIENTE] Janela exibida: state={window_state}, geometry={geometry}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[FORM_CLIENTE] Não foi possível verificar estado: {exc}")

    _update_title()
    win.grab_set()
    win.focus_force()
    logger.debug("[FORM_CLIENTE] Fim da função form_cliente")
