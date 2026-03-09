# -*- coding: utf-8 -*-
"""Mixin de callbacks/ações para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _on_return_key, _on_cancel, _on_arquivos,
         _on_cartao_cnpj, _on_enviar_documentos.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import EditorDialogProto

log = logging.getLogger(__name__)


# Helper local (duplicado do data mixin para evitar dependência cruzada)
def _safe_get(obj: Any, key: str, default: Any = "") -> Any:
    """Obtém valor de dict ou objeto de forma segura."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _conflict_desc(conflict: Any) -> str:
    """Formata descrição de conflito para mensagens de duplicata."""
    if isinstance(conflict, dict):
        cid = conflict.get("id", "?")
        razao = conflict.get("razao_social", "")
        cnpj = conflict.get("cnpj", "")
    else:
        cid = getattr(conflict, "id", "?")
        razao = getattr(conflict, "razao_social", "")
        cnpj = getattr(conflict, "cnpj", "")

    desc = f"ID {cid}"
    if razao:
        desc += f" — {razao}"
    if cnpj:
        desc += f" ({cnpj})"

    return desc


class EditorActionsMixin:
    """Mixin responsável pelos callbacks e ações do ClientEditorDialog."""

    def _on_return_key(self: EditorDialogProto, event: Any) -> str:
        """Handler centralizado para tecla Enter.

        Comportamento:
        - Se SHIFT pressionado E foco em Observações ou Contatos: insere nova linha
        - Caso contrário: salva o cliente

        Args:
            event: Evento de teclado

        Returns:
            "break" para impedir propagação
        """
        # Detectar se SHIFT está pressionado
        shift_pressed = bool(event.state & 0x0001)

        # Detectar se o foco está em textbox multiline (Observações ou Contatos)
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

        # Se Shift+Enter E foco em textbox: inserir nova linha
        if shift_pressed and is_focus_on_textbox:
            try:
                focus_widget.insert("insert", "\n")  # pyright: ignore[reportAttributeAccessIssue]
            except Exception as e:
                log.debug(f"[ClientEditor] Erro ao inserir newline: {e}")
            return "break"

        # Caso contrário: salvar
        self._on_save_clicked()
        return "break"

    def _on_cancel(self: EditorDialogProto) -> None:
        """Handler do botão Cancelar e tecla ESC.

        Usa o mesmo cleanup centralizado que WM_DELETE_WINDOW.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Cancelamento solicitado")
        self._cleanup_and_destroy()

    def _on_arquivos(self: EditorDialogProto) -> None:
        """Handler do botão Arquivos — abre ClientFilesDialog."""
        if not self.client_id:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(
                self,
                "Cliente não salvo",
                "Salve o cliente antes de acessar os arquivos.",
            )
            return

        # Preferir dados já carregados; caso contrário, ler dos entries
        if self._client_data:
            razao = self._client_data.get("razao_social", "") or ""
            cnpj = self._client_data.get("cnpj", "") or ""
        else:
            razao = self.razao_entry.get().strip()
            cnpj = self.cnpj_entry.get().strip()

        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass

        from src.modules.clientes.ui.views.client_files_dialog import ClientFilesDialog

        dlg = ClientFilesDialog(
            parent=self,
            client_id=int(self.client_id),
            client_name=razao or "Cliente",
            razao_social=razao or "",
            cnpj=cnpj or "",
        )

        # Reativar grab do editor quando o browser fechar
        def _on_files_close(event: object) -> None:
            if event.widget is dlg:  # type: ignore[union-attr]
                try:
                    if self.winfo_exists():
                        self.after(50, self.grab_set)
                except Exception:  # noqa: BLE001
                    pass

        dlg.bind("<Destroy>", _on_files_close)

    def _on_cartao_cnpj(self: EditorDialogProto) -> None:
        """Handler do botão Cartão CNPJ."""
        try:
            from tkinter.filedialog import askdirectory
            from src.modules.clientes.core import service as clientes_service

            # Solicitar pasta
            base_dir = askdirectory(title="Escolha a pasta do cliente (com o Cartão CNPJ)", parent=self)

            if not base_dir:
                return

            # Extrair dados do Cartão CNPJ
            dados = clientes_service.extrair_dados_cartao_cnpj_em_pasta(base_dir)

            cnpj_extraido = dados.get("cnpj")
            razao_extraida = dados.get("razao_social")

            if not cnpj_extraido and not razao_extraida:
                from src.ui.dialogs.rc_dialogs import show_warning

                show_warning(self, "Atenção", "Nenhum Cartão CNPJ válido encontrado.")
                return

            # Preencher campos
            if cnpj_extraido:
                self.cnpj_entry.delete(0, "end")
                self.cnpj_entry.insert(0, cnpj_extraido)

            if razao_extraida:
                self.razao_entry.delete(0, "end")
                self.razao_entry.insert(0, razao_extraida)

            from src.ui.dialogs.rc_dialogs import show_info

            show_info(self, "Sucesso", "Dados do Cartão CNPJ carregados com sucesso.")

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao processar Cartão CNPJ: {e}", exc_info=True)
            from src.ui.dialogs.rc_dialogs import show_error

            show_error(self, "Erro", f"Erro ao processar Cartão CNPJ: {e}")

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
                obs_body = self.obs_text.get("1.0", "end").strip()

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

            # execute_upload_flow já faz:
            # 1. Solicita pasta
            # 2. Coleta PDFs da pasta
            # 3. Solicita subpasta em GERAL
            # 4. Valida arquivos
            # 5. Executa upload com progresso
            # 6. Exibe resultado
            execute_upload_flow(
                parent_widget=self,
                ents=ents_mock,
                client_id=self.client_id,
                host=self,  # Precisa ter self.supabase para resolver org_id
            )

            # Se sucesso, atualizar callback
            if self.on_save:
                valores_atualizados = {
                    "Razão Social": self.razao_entry.get().strip(),
                    "CNPJ": self.cnpj_entry.get().strip(),
                }
                self.on_save(valores_atualizados)

        except Exception as e:
            log.error(f"[ClientEditor] Erro no fluxo de upload: {e}", exc_info=True)
            # Não usar messagebox com parent=self pois o dialog pode já estar destruído
            try:
                if self.winfo_exists():
                    from src.modules.clientes.forms.client_form_upload_helpers import _show_msg

                    _show_msg(self, "Erro", f"Erro ao enviar documentos:\n{e}")
            except Exception:  # noqa: BLE001
                pass
