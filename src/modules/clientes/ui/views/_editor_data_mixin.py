# -*- coding: utf-8 -*-
"""Mixin de dados/persistência para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _load_client_data, _parse_contatos_from_textbox, _load_contatos_from_db,
         _save_contatos_to_db, _load_bloco_notas_from_db, _save_bloco_notas_to_db,
         _validate_fields, _on_save_clicked.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import TYPE_CHECKING, Any

from src.utils.formatters import format_cnpj
from src.utils.phone_utils import format_phone_br
from src.ui.widgets.textbox_placeholder import clear_textbox_placeholder, get_textbox_content

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.modules.clientes.ui.views._dialogs_typing import EditorDialogProto

from src.modules.clientes.ui.views._editor_helpers import _conflict_desc, _safe_get

log = logging.getLogger(__name__)


class EditorDataMixin:
    """Mixin responsável por dados e persistência do ClientEditorDialog."""

    # -- helper genérico para I/O em background ------------------------------

    def _run_in_thread(
        self: EditorDialogProto,
        work: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Execute *work* in a daemon thread; dispatch result to UI thread.

        Callbacks are scheduled via ``self.after(0, ...)`` so they run safely
        on the Tk main-loop.  If the widget has already been destroyed
        (``winfo_exists()`` returns *False*) the callback is dropped and logged
        at DEBUG level.
        """

        def _wrapper() -> None:
            try:
                result = work()
            except Exception as exc:
                if on_error:
                    if self.winfo_exists():
                        self.after(0, on_error, exc)
                    else:
                        log.debug(
                            "[EditorDataMixin] on_error descartado: widget destruído (%s)",
                            type(exc).__name__,
                        )
                return
            if on_success:
                if self.winfo_exists():
                    self.after(0, on_success, result)
                else:
                    log.debug("[EditorDataMixin] on_success descartado: widget destruído")

        threading.Thread(target=_wrapper, daemon=True).start()

    # -- parse helpers -------------------------------------------------------

    def _parse_contatos_from_textbox(self: EditorDialogProto) -> list[dict]:
        """Parse contatos do textbox.

        Formato esperado por linha: "Nome - WhatsApp" ou "Nome | WhatsApp" ou "Nome ; WhatsApp"
        Se não houver separador, linha inteira é nome.

        Returns:
            Lista de dicts: [{"nome": str, "whatsapp": str}, ...]
        """
        texto = get_textbox_content(self.contatos_text)
        if not texto:
            return []

        contatos = []
        for linha in texto.split("\n"):
            linha = linha.strip()
            if not linha:
                continue

            # Tentar separadores (prioridade: " - ", "|", ";")
            nome = ""
            whatsapp = ""

            if " - " in linha:
                partes = linha.split(" - ", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            elif "|" in linha:
                partes = linha.split("|", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            elif ";" in linha:
                partes = linha.split(";", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            else:
                # Sem separador: linha inteira é nome
                nome = linha

            if nome:  # Só adicionar se tiver nome
                contatos.append({"nome": nome, "whatsapp": whatsapp})

        return contatos

    def _load_contatos_from_db(self: EditorDialogProto, cliente_id: int) -> None:
        """Carrega contatos do Supabase **em background** e preenche textbox.

        A query de rede roda numa daemon-thread; o preenchimento do widget
        acontece de volta na thread principal via ``self.after()``.

        Args:
            cliente_id: ID do cliente (BIGINT)
        """

        def _fetch() -> list[str]:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            response = (
                supabase.table("cliente_contatos").select("nome,whatsapp").eq("cliente_id", int(cliente_id)).execute()  # pyright: ignore[reportAttributeAccessIssue]
            )
            linhas: list[str] = []
            for contato in response.data or []:
                if not isinstance(contato, dict):
                    continue
                nome = (contato.get("nome") or "").strip()
                whatsapp = (contato.get("whatsapp") or "").strip()
                if not nome:
                    continue
                if whatsapp:
                    linhas.append(f"{nome} - {whatsapp}")
                else:
                    linhas.append(nome)
            return linhas

        def _on_loaded(linhas: list[str]) -> None:
            if linhas:
                texto_contatos = "\n".join(linhas)
                clear_textbox_placeholder(self.contatos_text)
                self.contatos_text.delete("1.0", "end")
                self.contatos_text.insert("1.0", texto_contatos)

        def _on_error(exc: Exception) -> None:
            log.error(
                "[ClientEditor] Erro ao carregar contatos do Supabase: %s",
                exc,
                exc_info=exc,
            )

        self._run_in_thread(_fetch, on_success=_on_loaded, on_error=_on_error)

    def _load_bloco_notas_from_db(self: EditorDialogProto, cliente_id: int) -> None:
        """Carrega o Bloco de notas do Supabase **em background** e preenche o textbox.

        Args:
            cliente_id: ID do cliente (BIGINT)
        """

        def _fetch() -> str:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            response = supabase.rpc(
                "rc_get_cliente_bloco_notas",
                {"p_cliente_id": int(cliente_id)},
            ).execute()
            # RPC retorna text diretamente
            body = response.data if isinstance(response.data, str) else ""
            return body.strip()

        def _on_loaded(body: str) -> None:
            if body:
                clear_textbox_placeholder(self.bloco_notas_text)
                self.bloco_notas_text.delete("1.0", "end")
                self.bloco_notas_text.insert("1.0", body)

        def _on_error(exc: Exception) -> None:
            log.error(
                "[ClientEditor] Erro ao carregar bloco de notas do Supabase: %s",
                exc,
                exc_info=exc,
            )

        self._run_in_thread(_fetch, on_success=_on_loaded, on_error=_on_error)

    def _save_bloco_notas_to_db(
        self: EditorDialogProto,
        cliente_id: int,
        *,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Salva o Bloco de notas no Supabase **em background** via RPC upsert/delete.

        O texto é lido na thread principal (leitura de widget), a chamada de rede
        roda em daemon-thread.  Ao terminar (sucesso ou erro), *on_done* é chamado
        na UI thread.

        Args:
            cliente_id: ID do cliente (BIGINT)
            on_done: callback opcional executado na UI thread após conclusão.
        """
        # Ler widget na UI thread (obrigatório)
        texto = get_textbox_content(self.bloco_notas_text)
        cliente_id_int = int(cliente_id)

        def _persist() -> None:
            from src.infra.supabase_client import exec_postgrest, get_supabase

            supabase = get_supabase()
            exec_postgrest(
                supabase.rpc(
                    "rc_save_cliente_bloco_notas",
                    {"p_cliente_id": cliente_id_int, "p_body": texto or None},
                )
            )

        def _on_saved(_result: Any) -> None:
            if on_done:
                on_done()

        def _on_error(exc: Exception) -> None:
            log.error(
                "[ClientEditor] Erro ao salvar bloco de notas no Supabase: %s",
                exc,
                exc_info=exc,
            )
            # P1-3: registrar falha parcial para feedback ao usuário
            if hasattr(self, "_save_warnings"):
                self._save_warnings.append("Falha ao salvar bloco de notas")
            if on_done:
                on_done()

        self._run_in_thread(_persist, on_success=_on_saved, on_error=_on_error)

    def _save_contatos_to_db(
        self: EditorDialogProto,
        cliente_id: int,
        *,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Salva contatos no Supabase **em background** (delete + insert).

        O parse do textbox é feito na thread principal (leitura de widget),
        enquanto as operações de rede rodam em daemon-thread.
        Ao terminar (sucesso ou erro), *on_done* é chamado na UI thread.

        Args:
            cliente_id: ID do cliente (BIGINT)
            on_done: callback opcional executado na UI thread após conclusão.
        """
        # Ler widget na UI thread (obrigatório)
        contatos = self._parse_contatos_from_textbox()
        cliente_id_int = int(cliente_id)

        # Desabilitar botão para evitar duplo-clique
        self.save_btn.configure(state="disabled")

        def _persist() -> None:
            from src.infra.supabase_client import exec_postgrest, get_supabase

            supabase = get_supabase()

            # Montar payload JSONB (lista de contatos)
            payload: list[dict[str, str | None]] = [
                {"nome": c["nome"], "whatsapp": c["whatsapp"] or None} for c in contatos
            ]

            # Chamada RPC atômica — DELETE + INSERT dentro de uma transação PG
            exec_postgrest(
                supabase.rpc(
                    "rc_save_cliente_contatos",
                    {"p_cliente_id": cliente_id_int, "p_contatos": payload},
                )
            )

        def _on_saved(_result: Any) -> None:
            if on_done:
                on_done()

        def _on_error(exc: Exception) -> None:
            log.error(
                "[ClientEditor] Erro ao salvar contatos no Supabase: %s",
                exc,
                exc_info=exc,
            )
            # P1-3: registrar falha parcial para feedback ao usuário
            if hasattr(self, "_save_warnings"):
                self._save_warnings.append("Falha ao salvar contatos")
            if on_done:
                on_done()

        self._run_in_thread(_persist, on_success=_on_saved, on_error=_on_error)

    def _load_client_data(self: EditorDialogProto) -> None:
        """Carrega dados do cliente para edição."""
        if self.client_id is None:
            return

        try:
            # Buscar cliente via service
            from src.modules.clientes.core import service as clientes_service

            cliente = clientes_service.fetch_cliente_by_id(self.client_id)

            if not cliente:
                log.error(f"[ClientEditor] Cliente {self.client_id} não encontrado")
                return

            self._client_data = cliente

            # Atualizar título com dados do cliente — padrão do browser de arquivos
            razao = _safe_get(cliente, "razao_social", "")
            cnpj_raw = _safe_get(cliente, "cnpj", "")
            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw  # Formatar CNPJ com pontos/barra

            _title = f"Editar Cliente — ID: {self.client_id} — {razao}"
            if cnpj_fmt:
                _title = f"{_title} — {cnpj_fmt}"
            self.title(_title)

            # Preencher campos principais (usar helper para preservar placeholders)
            self._set_entry_value(self.razao_entry, _safe_get(cliente, "razao_social", ""))

            # CNPJ FORMATADO (padrão 00.000.000/0000-00)
            cnpj_raw = _safe_get(cliente, "cnpj", "")
            cnpj_fmt = format_cnpj(cnpj_raw) if cnpj_raw else ""
            self._set_entry_value(self.cnpj_entry, cnpj_fmt or cnpj_raw)

            # Nome
            self._set_entry_value(self.nome_entry, _safe_get(cliente, "nome", ""))

            # WhatsApp FORMATADO (padrão +55 DD XXXXX-XXXX)
            whatsapp_raw = _safe_get(cliente, "numero", "") or _safe_get(cliente, "whatsapp", "")
            whatsapp_fmt = format_phone_br(whatsapp_raw) if whatsapp_raw else ""
            self._set_entry_value(self.whatsapp_entry, whatsapp_fmt or whatsapp_raw)

            # Extrair status das observações (padrão legacy: "[Status] texto")
            obs = _safe_get(cliente, "observacoes", "") or _safe_get(cliente, "obs", "")
            status = "Novo Cliente"  # Default

            if obs:
                # Usar método do viewmodel para extrair status
                from src.modules.clientes.core.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                status_extracted, obs_clean = vm_temp.extract_status_and_observacoes(obs)
                if status_extracted:
                    status = status_extracted
                    obs = obs_clean

            # Aplicar status
            self.status_var.set(status)

            # Aplicar status Anvisa e Farmácia Popular
            _sa = (_safe_get(cliente, "status_anvisa") or "").strip()
            _sfp = (_safe_get(cliente, "status_farmacia_popular") or "").strip()
            self.status_anvisa_var.set(_sa if _sa else "---")
            self.status_farmacia_popular_var.set(_sfp if _sfp else "---")

            # Aplicar observações
            if obs:
                clear_textbox_placeholder(self.obs_text)
                self.obs_text.delete("1.0", "end")
                self.obs_text.insert("1.0", obs)

            # Carregar contatos adicionais do Supabase
            self._load_contatos_from_db(self.client_id)

            # Carregar Bloco de notas do Supabase
            self._load_bloco_notas_from_db(self.client_id)

            log.debug(f"[ClientEditor] Dados carregados para cliente {self.client_id}")

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao carregar cliente: {e}", exc_info=True)
            from src.ui.dialogs.rc_dialogs import show_error

            show_error(self, "Erro", f"Erro ao carregar dados do cliente: {e}")

    def _on_cnpj_focus_out(self: EditorDialogProto, event: Any = None) -> None:
        """Formata CNPJ ao sair do campo."""
        try:
            raw = self.cnpj_entry.get().strip()
            if raw:
                formatted = format_cnpj(raw)
                if formatted and formatted != raw:
                    self._set_entry_value(self.cnpj_entry, formatted)
        except Exception as e:
            log.debug(f"[ClientEditor] Erro ao formatar CNPJ: {e}")

    def _on_whatsapp_focus_out(self: EditorDialogProto, event: Any = None) -> None:
        """Formata WhatsApp ao sair do campo."""
        try:
            raw = self.whatsapp_entry.get().strip()
            if raw:
                formatted = format_phone_br(raw)
                if formatted and formatted != raw:
                    self._set_entry_value(self.whatsapp_entry, formatted)
        except Exception as e:
            log.debug(f"[ClientEditor] Erro ao formatar WhatsApp: {e}")

    def _validate_fields(self: EditorDialogProto) -> bool:
        """Valida campos obrigatórios.

        Razão Social e CNPJ são ambos obrigatórios.
        Se CNPJ informado, deve ter 14 dígitos.

        Returns:
            True se campos válidos, False se há erros
        """
        razao = self.razao_entry.get().strip()
        cnpj = self.cnpj_entry.get().strip()

        # Validar presença dos campos obrigatórios
        falta_razao = not razao
        falta_cnpj = not cnpj

        if falta_razao and falta_cnpj:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(
                self,
                "Campos obrigatórios",
                "Preencha a Razão Social e o CNPJ antes de salvar.",
            )
            return False

        if falta_razao:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(
                self,
                "Campos obrigatórios",
                "Preencha a Razão Social antes de salvar.",
            )
            return False

        if falta_cnpj:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(
                self,
                "Campos obrigatórios",
                "Preencha o CNPJ antes de salvar.",
            )
            return False

        # Validar formato básico do CNPJ (14 dígitos)
        digits = re.sub(r"\D", "", cnpj)
        if len(digits) != 14:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(self, "Campos obrigatórios", "CNPJ deve ter 14 dígitos.")
            return False

        return True

    def _on_save_clicked(self: EditorDialogProto) -> None:
        """Handler do botão Salvar - com validações de duplicatas."""
        if not self._validate_fields():
            return

        try:
            # Coletar dados do form
            status_text = self.status_var.get()
            obs_body = get_textbox_content(self.obs_text)

            # Aplicar status nas observações (padrão legacy: "[Status] texto")
            from src.modules.clientes.core.viewmodel import ClientesViewModel

            vm_temp = ClientesViewModel()
            obs_completa = vm_temp.apply_status_to_observacoes(status_text, obs_body)

            valores = {
                "Razão Social": self.razao_entry.get().strip(),
                "CNPJ": self.cnpj_entry.get().strip(),
                "Nome": self.nome_entry.get().strip(),
                "WhatsApp": self.whatsapp_entry.get().strip(),
                "Observações": obs_completa,
                "status_anvisa": self.status_anvisa_var.get(),
                "status_farmacia_popular": self.status_farmacia_popular_var.get(),
                # Contatos adicionais (textbox do painel esquerdo)
                "Contatos adicionais": get_textbox_content(self.contatos_text),
                # Bloco de notas é salvo em tabela separada (cliente_bloco_notas)
                # via _save_bloco_notas_to_db — não entra no payload de clientes.
            }

            # FASE 3.2: Validar duplicatas antes de salvar
            from src.modules.clientes.core import service as clientes_service
            from src.modules.clientes.core.service import ClienteCNPJDuplicadoError
            from src.ui.dialogs.rc_dialogs import show_error, ask_yes_no

            # Montar row (None para novo, tupla (id,) para editar)
            row = None if self.client_id is None else (self.client_id,)

            # Checar duplicatas
            duplicatas = clientes_service.checar_duplicatas_para_form(valores, row)

            # 1. CNPJ duplicado é bloqueante (hard block)
            cnpj_conflict = duplicatas.get("cnpj_conflict")
            if cnpj_conflict:
                show_error(
                    self,
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(cnpj_conflict)}\n\n"
                    f"Edite o cliente existente ou use um CNPJ diferente.",
                )
                return

            # 2. Razão Social e/ou Telefone similares são warnings (soft block)
            razao_conflicts = duplicatas.get("razao_conflicts", [])
            numero_conflicts = duplicatas.get("numero_conflicts", [])

            if razao_conflicts or numero_conflicts:
                # Montar mensagem com conflitos
                msg_parts = ["Encontrado(s) cliente(s) similar(es):\n"]

                if razao_conflicts:
                    msg_parts.append("\n• Razão Social similar:")
                    for conf in razao_conflicts[:3]:  # Limitar a 3
                        conf_id = _safe_get(conf, "id", "?")
                        conf_razao = _safe_get(conf, "razao_social", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao}")

                if numero_conflicts:
                    msg_parts.append("\n• Telefone similar:")
                    for conf in numero_conflicts[:3]:  # Limitar a 3
                        conf_id = _safe_get(conf, "id", "?")
                        conf_razao = _safe_get(conf, "razao_social", "")
                        conf_numero = _safe_get(conf, "numero", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao} ({conf_numero})")

                msg_parts.append("\n\nDeseja prosseguir mesmo assim?")

                resposta = ask_yes_no(self, "Clientes Similares", "\n".join(msg_parts))

                if not resposta:
                    # Usuário cancelou
                    return

            # 3. Se passou as validações, salvar
            log.debug("[ClientEditor] Salvando cliente (id=%s)", self.client_id or "novo")

            # P1-3: inicializar tracker de falhas parciais
            self._save_warnings: list[str] = []

            try:
                result = clientes_service.salvar_cliente_a_partir_do_form(row, valores)
                log.info(f"[ClientEditor] Cliente salvo: {result}")

                # Obter ID do cliente (result é tupla: (int, str) -> (id, pasta))
                cliente_id_salvo = None
                if self.client_id:
                    cliente_id_salvo = int(self.client_id)
                elif isinstance(result, tuple) and len(result) >= 1:
                    cliente_id_salvo = int(result[0])  # Primeiro elemento da tupla é o ID

                # Salvar contatos no Supabase (background)
                def _finish_save() -> None:
                    """Callback executado na UI thread após contatos serem salvos."""
                    # P1-3: avisar sobre falhas parciais antes de fechar
                    if getattr(self, "_save_warnings", None) and self.winfo_exists():
                        from src.ui.dialogs.rc_dialogs import show_warning

                        msg = "O cliente foi salvo, mas houve falhas parciais:\n\n"
                        msg += "\n".join(f"• {w}" for w in self._save_warnings)
                        show_warning(self, "Salvo com ressalvas", msg)

                    if self.on_save:
                        self.on_save(valores)
                    if self.winfo_exists():
                        self.destroy()

                if cliente_id_salvo:
                    self._save_contatos_to_db(
                        cliente_id_salvo,
                        on_done=lambda: self._save_bloco_notas_to_db(
                            cliente_id_salvo,
                            on_done=_finish_save,
                        ),
                    )
                else:
                    _finish_save()

            except ClienteCNPJDuplicadoError as dup_err:
                # CNPJ duplicado detectado no service (fallback)
                show_error(
                    self,
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(dup_err.cliente)}\n\n"
                    f"Edite o cliente existente ou use um CNPJ diferente.",
                )
                return

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao salvar: {e}", exc_info=True)
            from src.ui.dialogs.rc_dialogs import show_error

            show_error(self, "Erro", f"Erro ao salvar cliente: {e}")
