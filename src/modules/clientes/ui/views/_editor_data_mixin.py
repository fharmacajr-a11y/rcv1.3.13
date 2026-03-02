# -*- coding: utf-8 -*-
"""Mixin de dados/persistência para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _load_client_data, _parse_contatos_from_textbox, _load_contatos_from_db,
         _save_contatos_to_db, _validate_fields, _on_save_clicked.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from src.utils.formatters import format_cnpj
from src.utils.phone_utils import format_phone_br

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import EditorDialogProto

log = logging.getLogger(__name__)


# Referência local ao helper (importado em client_editor_dialog.py)
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


class EditorDataMixin:
    """Mixin responsável por dados e persistência do ClientEditorDialog."""

    def _parse_contatos_from_textbox(self: EditorDialogProto) -> list[dict]:
        """Parse contatos do textbox.

        Formato esperado por linha: "Nome - WhatsApp" ou "Nome | WhatsApp" ou "Nome ; WhatsApp"
        Se não houver separador, linha inteira é nome.

        Returns:
            Lista de dicts: [{"nome": str, "whatsapp": str}, ...]
        """
        texto = self.contatos_text.get("1.0", "end").strip()
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
        """Carrega contatos do Supabase e preenche textbox.

        Args:
            cliente_id: ID do cliente (BIGINT)
        """
        try:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            response = (
                supabase.table("cliente_contatos").select("nome,whatsapp").eq("cliente_id", int(cliente_id)).execute()  # pyright: ignore[reportAttributeAccessIssue]
            )

            if response.data:
                linhas = []
                for contato in response.data or []:
                    # Robustez: verificar se é dict
                    if not isinstance(contato, dict):
                        continue

                    # Tratar NULL do banco (vira None em Python)
                    nome = (contato.get("nome") or "").strip()
                    whatsapp = (contato.get("whatsapp") or "").strip()

                    # Ignorar registros sem nome
                    if not nome:
                        continue

                    # Montar linha
                    if whatsapp:
                        linhas.append(f"{nome} - {whatsapp}")
                    else:
                        linhas.append(nome)

                # Preencher textbox
                if linhas:
                    texto_contatos = "\n".join(linhas)
                    self.contatos_text.delete("1.0", "end")
                    self.contatos_text.insert("1.0", texto_contatos)

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao carregar contatos do Supabase: {e}", exc_info=True)

    def _save_contatos_to_db(self: EditorDialogProto, cliente_id: int) -> None:
        """Salva contatos no Supabase (delete + insert).

        Args:
            cliente_id: ID do cliente (BIGINT)
        """
        try:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            cliente_id_int = int(cliente_id)

            # 1. Delete antigos
            supabase.table("cliente_contatos").delete().eq("cliente_id", cliente_id_int).execute()  # pyright: ignore[reportAttributeAccessIssue]

            # 2. Parse contatos do textbox
            contatos = self._parse_contatos_from_textbox()

            # 3. Insert em lote
            if contatos:
                records = [
                    {
                        "cliente_id": cliente_id_int,
                        "nome": c["nome"],
                        "whatsapp": c["whatsapp"] or None,
                    }
                    for c in contatos
                ]
                supabase.table("cliente_contatos").insert(records).execute()  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao salvar contatos no Supabase: {e}", exc_info=True)

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

            # Atualizar título com dados do cliente (igual ao legado)
            razao = _safe_get(cliente, "razao_social", "")
            cnpj_raw = _safe_get(cliente, "cnpj", "")
            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw  # Formatar CNPJ com pontos/barra

            # Extrair sufixo WhatsApp das observações (se existir)
            obs = _safe_get(cliente, "observacoes", "") or ""
            sufixo = ""
            if "(Não está respondendo)" in obs:
                sufixo = " (Não está respondendo)"
            elif "(Respondendo)" in obs:
                sufixo = " (Respondendo)"

            self.title(f"Editar Cliente - ID: {self.client_id} - {razao} - {cnpj_fmt}{sufixo}")

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

            # Preencher campos internos (endereço) - usar helper para preservar placeholders
            # Nota: Esses campos podem não estar no banco ainda, usar valores vazios como padrão
            self._set_entry_value(self.endereco_entry, _safe_get(cliente, "endereco", ""))
            self._set_entry_value(self.bairro_entry, _safe_get(cliente, "bairro", ""))
            self._set_entry_value(self.cidade_entry, _safe_get(cliente, "cidade", ""))
            self._set_entry_value(self.cep_entry, _safe_get(cliente, "cep", ""))

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

            # Aplicar observações
            if obs:
                self.obs_text.delete("1.0", "end")
                self.obs_text.insert("1.0", obs)

            # Carregar contatos adicionais do Supabase
            self._load_contatos_from_db(self.client_id)

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

        Returns:
            True se campos válidos, False se há erros
        """
        razao = self.razao_entry.get().strip()
        cnpj = self.cnpj_entry.get().strip()

        erros = []

        if not razao:
            erros.append("Razão Social é obrigatória")

        if not cnpj:
            erros.append("CNPJ é obrigatório")
        elif cnpj:
            # Validar formato básico do CNPJ (14 dígitos)
            digits = re.sub(r"\D", "", cnpj)
            if len(digits) != 14:
                erros.append("CNPJ deve ter 14 dígitos")

        if erros:
            from src.ui.dialogs.rc_dialogs import show_warning

            show_warning(self, "Campos obrigatórios", "\n".join(erros))
            return False

        return True

    def _on_save_clicked(self: EditorDialogProto) -> None:
        """Handler do botão Salvar - com validações de duplicatas."""
        if not self._validate_fields():
            return

        try:
            # Coletar dados do form
            status_text = self.status_var.get()
            obs_body = self.obs_text.get("1.0", "end").strip()

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
                # Campos internos (não persistidos no legado, mas incluídos para futuro)
                "Endereço": self.endereco_entry.get().strip(),
                "Bairro": self.bairro_entry.get().strip(),
                "Cidade": self.cidade_entry.get().strip(),
                "CEP": self.cep_entry.get().strip(),
                # Contatos adicionais (textbox do painel direito)
                "Contatos adicionais": self.contatos_text.get("1.0", "end").strip(),
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
            log.debug(f"[ClientEditor] Salvando cliente: {valores['Razão Social']}")

            try:
                result = clientes_service.salvar_cliente_a_partir_do_form(row, valores)
                log.info(f"[ClientEditor] Cliente salvo: {result}")

                # Obter ID do cliente (result é tupla: (int, str) -> (id, pasta))
                cliente_id_salvo = None
                if self.client_id:
                    cliente_id_salvo = int(self.client_id)
                elif isinstance(result, tuple) and len(result) >= 1:
                    cliente_id_salvo = int(result[0])  # Primeiro elemento da tupla é o ID

                # Salvar contatos no Supabase
                if cliente_id_salvo:
                    self._save_contatos_to_db(cliente_id_salvo)

            except ClienteCNPJDuplicadoError as dup_err:
                # CNPJ duplicado detectado no service (fallback)
                show_error(
                    self,
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(dup_err.cliente)}\n\n"
                    f"Edite o cliente existente ou use um CNPJ diferente.",
                )
                return

            # Chamar callback
            if self.on_save:
                self.on_save(valores)

            # Fechar dialog
            self.destroy()

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao salvar: {e}", exc_info=True)
            from src.ui.dialogs.rc_dialogs import show_error

            show_error(self, "Erro", f"Erro ao salvar cliente: {e}")
