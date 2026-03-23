# -*- coding: utf-8 -*-
"""Mixin de callbacks/ações para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _on_return_key, _on_cancel, _on_arquivos, _on_enviar_documentos.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import EditorDialogProto

log = logging.getLogger(__name__)


def _resolve_supabase_client() -> object:
    """Resolve o cliente Supabase de forma robusta com fallback.

    Tenta localizar o singleton Supabase em diferentes módulos do projeto.
    Retorna o cliente ou None se não encontrado.
    """
    candidates = [
        ("src.infra.supabase_client", ("supabase", "get_supabase", "client")),
        ("src.infra.supabase.db_client", ("supabase", "supabase_client", "client", "get_client")),
        ("src.infra.supabase.auth_client", ("supabase", "supabase_client", "client")),
    ]
    for mod_name, attrs in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:  # nosec B112 - Fallback: tenta múltiplos caminhos até encontrar módulo válido
            continue
        for attr in attrs:
            if hasattr(mod, attr):
                obj = getattr(mod, attr)
                if callable(obj) and not hasattr(obj, "table"):
                    try:
                        return obj()
                    except Exception:  # nosec B112 - Fallback: invoca se for factory function
                        continue
                return obj
    log.warning("[EditorArquivos] Não foi possível resolver o cliente Supabase")
    return None


from src.modules.clientes.ui.views._editor_helpers import _conflict_desc  # noqa: E402
from src.ui.widgets.textbox_placeholder import get_textbox_content  # noqa: E402


class EditorActionsMixin:
    """Mixin responsável pelos callbacks e ações do ClientEditorDialog."""

    def _on_return_key(self: EditorDialogProto, event: Any) -> str:
        """Handler centralizado para tecla Enter.

        Comportamento:
        - Se foco em Observações, Contatos ou Bloco de notas:
            * Enter quebra linha normalmente (binding de classe do tk.Text já inseriu \\n).
            * Retorna "break" para impedir o save.
        - Fora de textbox: Enter/KP_Enter salva o cliente.

        Args:
            event: Evento de teclado

        Returns:
            "break" para impedir propagação
        """
        # Detectar se o foco está em textbox multiline (Observações, Contatos ou Bloco de notas)
        focus_widget = self.focus_get()
        is_focus_on_textbox = False

        if focus_widget is not None:
            # Verificar Observações
            obs_internal = getattr(self.obs_text, "_textbox", None)
            if focus_widget is self.obs_text or focus_widget is obs_internal:
                is_focus_on_textbox = True

            # Verificar Contatos
            contatos_internal = getattr(self.contatos_text, "_textbox", None)
            if focus_widget is self.contatos_text or focus_widget is contatos_internal:
                is_focus_on_textbox = True

            # Verificar Bloco de notas
            bloco_notas_internal = getattr(self.bloco_notas_text, "_textbox", None)
            if focus_widget is self.bloco_notas_text or focus_widget is bloco_notas_internal:
                is_focus_on_textbox = True

        if is_focus_on_textbox:
            # tk.Text já inseriu \n via binding de classe; apenas impede o save.
            return "break"

        # Foco fora de textbox: Enter confirma/salva o cliente.
        self._on_save_clicked()
        return "break"

    def _on_cancel(self: EditorDialogProto) -> None:
        """Handler do botão Cancelar e tecla ESC.

        Usa o mesmo cleanup centralizado que WM_DELETE_WINDOW.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Cancelamento solicitado")
        self._cleanup_and_destroy()

    def _on_arquivos(self: EditorDialogProto) -> None:
        """Handler do botão Arquivos — abre UploadsBrowserWindowV2."""
        if not self.client_id:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(
                self,
                "Cliente não salvo",
                "Salve o cliente antes de acessar os arquivos.",
            )
            return

        # Dados reais do cliente — preferir _client_data já carregado
        if self._client_data:
            razao = str(self._client_data.get("razao_social", "") or "")
            cnpj = str(self._client_data.get("cnpj", "") or "")
        else:
            razao = self.razao_entry.get().strip()
            cnpj = self.cnpj_entry.get().strip()

        # Resolver org_id (necessário para construir o storage prefix correto)
        org_id = ""
        try:
            from src.modules.uploads.components.helpers import get_current_org_id

            sb = _resolve_supabase_client()
            if sb is not None:
                org_id = get_current_org_id(sb) or ""
        except Exception as exc:  # noqa: BLE001
            log.debug("[EditorArquivos] Não foi possível obter org_id: %s", exc)

        # Computar bucket e prefix do Storage
        bucket = ""
        base_prefix = ""
        try:
            from src.modules.uploads.components.helpers import (
                get_clients_bucket,
                client_prefix_for_id,
            )

            bucket = get_clients_bucket()
            if org_id:
                base_prefix = client_prefix_for_id(int(self.client_id), org_id)
        except Exception as exc:  # noqa: BLE001
            log.debug("[EditorArquivos] Não foi possível computar prefix: %s", exc)

        # Liberar grab para que o V2 possa responder ao usuário
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass

        # Abrir Browser V2
        from src.modules.uploads.views.browser_v2 import open_files_browser_v2

        _files_mutated = [False]

        def _on_mutation_cb() -> None:
            _files_mutated[0] = True
            log.info("[EditorArquivos] on_mutation disparado para cliente %s — _files_mutated=True", self.client_id)

        dlg = open_files_browser_v2(
            self,
            client_id=int(self.client_id),
            razao=razao,
            cnpj=cnpj,
            org_id=org_id,
            bucket=bucket,
            base_prefix=base_prefix,
            on_mutation=_on_mutation_cb,
        )

        if dlg is None:
            # Falha na abertura: restaurar grab imediatamente
            from src.ui.dialogs.rc_dialogs import show_warning as _sw

            _sw(self, "Erro", "Não foi possível abrir o navegador de arquivos.")
            try:
                if self.winfo_exists():
                    self.grab_set()
            except Exception:  # noqa: BLE001
                pass
            return

        # Forçar foco no browser para encerrar qualquer janela de tempo sem modal
        # causada pelo grab_release() acima. Sem isso, o foco poderia retornar ao
        # treeview de clientes da janela principal, e Delete excluiria o cliente.
        try:
            if dlg.winfo_exists():
                dlg.focus_force()
        except Exception:  # noqa: BLE001
            pass

        # Reativar grab do editor quando o browser fechar
        def _on_browser_close(event: object) -> None:
            if event.widget is dlg:  # type: ignore[union-attr]
                log.info(
                    "[EditorArquivos] browser fechado para cliente %s (_files_mutated=%s)",
                    self.client_id,
                    _files_mutated[0],
                )
                try:
                    if self.winfo_exists():
                        self.after(50, self.grab_set)
                except Exception:  # noqa: BLE001
                    pass
                if _files_mutated[0]:
                    try:
                        self.after(100, _touch_and_refresh)
                        log.info("[EditorArquivos] _touch_and_refresh agendado para cliente %s", self.client_id)
                    except Exception:  # noqa: BLE001
                        pass

        def _touch_and_refresh() -> None:
            # Roda no main thread (agendado via self.after).
            import threading

            cid = self.client_id
            log.info("[EditorArquivos] _touch_and_refresh iniciado para cliente %s", cid)

            def _bg() -> None:
                # I/O puro — NUNCA chamar métodos Tk aqui.
                log.info("[EditorArquivos] _bg: iniciando touch_ultima_alteracao para cliente %s", cid)
                try:
                    from src.modules.clientes.core.service import touch_ultima_alteracao

                    touch_ultima_alteracao(int(cid))
                    log.info("[EditorArquivos] _bg: touch_ultima_alteracao concluído para cliente %s", cid)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[EditorArquivos] _bg: Falha ao tocar ultima_alteracao para cliente %s: %s", cid, exc)
                # Retorna ao main thread para qualquer operação Tk.
                # self.after(0, ...) é thread-safe (fila interna do Tcl).
                try:
                    self.after(0, _notify_main)
                except Exception:  # noqa: BLE001
                    pass

            def _notify_main() -> None:
                # Roda no main thread — seguro checar winfo_exists e chamar on_save.
                log.info("[EditorArquivos] _notify_main: verificando editor para cliente %s", cid)
                try:
                    if self.winfo_exists() and callable(getattr(self, "on_save", None)):
                        log.info("[EditorArquivos] _notify_main: chamando on_save para cliente %s", cid)
                        self.on_save({"_source": "upload"})
                    else:
                        log.info(
                            "[EditorArquivos] _notify_main: editor destruído ou on_save ausente para cliente %s", cid
                        )
                except Exception:  # noqa: BLE001
                    pass

            threading.Thread(target=_bg, daemon=True).start()

        dlg.bind("<Destroy>", _on_browser_close)

    def _on_enviar_documentos(self: EditorDialogProto) -> None:
        """Handler do botão Enviar documentos.

        Implementa o fluxo COMPLETO igual ao legado:
        1. Verifica se cliente está salvo
        2. Seleciona PASTA (não arquivos)
        3. Solicita subpasta em GERAL
        4. Seleciona arquivos da pasta
        5. Executa upload com progresso
        """
        try:
            # Verificar se cliente já foi salvo
            if not self.client_id:
                from src.ui.dialogs.rc_dialogs import ask_yes_no

                result = ask_yes_no(
                    self,
                    "Cliente não salvo",
                    "O cliente precisa ser salvo antes de enviar documentos.\n\nDeseja salvar agora?",
                )

                if not result:
                    return

                # Salvar primeiro
                if not self._validate_fields():
                    return

                # Coletar e salvar (sem fechar dialog)
                status_text = self.status_var.get()
                obs_body = get_textbox_content(self.obs_text)

                from src.modules.clientes.core.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                obs_completa = vm_temp.apply_status_to_observacoes(status_text, obs_body)

                valores = {
                    "Razão Social": self.razao_entry.get().strip(),
                    "CNPJ": self.cnpj_entry.get().strip(),
                    "Nome": self.nome_entry.get().strip(),
                    "WhatsApp": self.whatsapp_entry.get().strip(),
                    "Observações": obs_completa,
                }

                from src.modules.clientes.core import service as clientes_service
                from src.modules.clientes.core.service import ClienteCNPJDuplicadoError
                from src.ui.dialogs.rc_dialogs import show_error as _upload_show_error

                try:
                    result_save = clientes_service.salvar_cliente_a_partir_do_form(None, valores)

                    # Extrair ID do resultado
                    if result_save and len(result_save) > 0:
                        self.client_id = (
                            result_save[0] if isinstance(result_save[0], int) else int(result_save[0].get("id", 0))
                        )
                        self._set_window_title()
                        try:
                            if hasattr(self, "arquivos_btn") and self.arquivos_btn:
                                self.arquivos_btn.configure(state="normal")
                        except Exception:  # noqa: BLE001
                            pass
                except ClienteCNPJDuplicadoError as dup_err:
                    # CNPJ duplicado detectado - mostrar mensagem amigável e PARAR
                    _upload_show_error(
                        self,
                        "CNPJ Duplicado",
                        f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(dup_err.cliente)}\n\n"
                        f"Edite o cliente existente ou use um CNPJ diferente.\n\n"
                        f"Upload cancelado.",
                    )
                    return  # CRÍTICO: não prosseguir para upload

            # Executar upload usando o FLUXO COMPLETO do legado (pasta → subpasta → arquivos)
            log.info(f"[ClientEditor] Iniciando upload de documentos para cliente {self.client_id}")

            # Criar widgets mock para compatibilidade com o legado
            class EntryMock:
                def __init__(self, value: str):
                    self._value = value

                def get(self) -> str:
                    return self._value

            ents_mock = {
                "Razão Social": EntryMock(self.razao_entry.get()),
                "CNPJ": EntryMock(self.cnpj_entry.get()),
                "Nome": EntryMock(self.nome_entry.get()),
                "WhatsApp": EntryMock(self.whatsapp_entry.get()),
            }

            # Usar a função COMPLETA do legado (pasta → subpasta → arquivos → upload)
            from src.modules.clientes.forms.client_form_upload_helpers import execute_upload_flow

            # Callback chamado pelo UploadDialog APÓS upload bem-sucedido (no main thread).
            # Roda touch_ultima_alteracao em background e despacha on_save via self.after(0, ...).
            def _on_mutation_enviar_docs() -> None:
                import threading

                cid = self.client_id
                log.info("[EnviarDocs] upload concluído para cliente %s — iniciando touch_ultima_alteracao", cid)

                def _bg() -> None:
                    try:
                        from src.modules.clientes.core.service import touch_ultima_alteracao

                        touch_ultima_alteracao(int(cid))
                        log.info("[EnviarDocs] touch_ultima_alteracao concluído para cliente %s", cid)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("[EnviarDocs] touch_ultima_alteracao falhou para cliente %s: %s", cid, exc)
                    try:
                        self.after(0, _notify_main)
                    except Exception:  # noqa: BLE001
                        pass

                def _notify_main() -> None:
                    log.info("[EnviarDocs] solicitando refresh da lista para cliente %s", cid)
                    try:
                        if self.winfo_exists() and callable(getattr(self, "on_save", None)):
                            self.on_save({"_source": "upload"})
                        else:
                            log.info("[EnviarDocs] editor destruído ou on_save ausente para cliente %s", cid)
                    except Exception:  # noqa: BLE001
                        pass

                threading.Thread(target=_bg, daemon=True).start()

            # execute_upload_flow já faz:
            # 1. Solicita pasta
            # 2. Coleta PDFs da pasta
            # 3. Solicita subpasta em GERAL
            # 4. Valida arquivos
            # 5. Executa upload com progresso
            # 6. Exibe resultado
            # on_mutation é chamado apenas quando ok_count > 0 (upload com sucesso real).
            execute_upload_flow(
                parent_widget=self,
                ents=ents_mock,
                client_id=self.client_id,
                host=self,  # Precisa ter self.supabase para resolver org_id
                on_mutation=_on_mutation_enviar_docs,
            )

        except Exception as e:
            log.error(f"[ClientEditor] Erro no fluxo de upload: {e}", exc_info=True)
            # Não usar messagebox com parent=self pois o dialog pode já estar destruído
            try:
                if self.winfo_exists():
                    from src.modules.clientes.forms.client_form_upload_helpers import _show_msg

                    _show_msg(self, "Erro", f"Erro ao enviar documentos:\n{e}")
            except Exception:  # noqa: BLE001
                pass
