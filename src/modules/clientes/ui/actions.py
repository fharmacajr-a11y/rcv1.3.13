# -*- coding: utf-8 -*-
"""Helpers de fluxo de ação do módulo clientes — zero dependências de UI.

Funções puras ou procedurais que encapsulam lógica extraída de
ClientesV2Frame, reduzindo o acoplamento interno de view.py.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

log = logging.getLogger(__name__)


def resolve_client_label(client_id: int, row_data_map: dict) -> str:
    """Retorna '{razao_social} (ID {n})' ou 'ID {n}' para um cliente no mapa de linhas."""
    for data in row_data_map.values():
        if int(data.id) == client_id:
            razao = data.razao_social or ""
            return f"{razao} (ID {client_id})" if razao else f"ID {client_id}"
    return f"ID {client_id}"


def client_row_to_dict(row: Any) -> dict[str, str]:
    """Converte um ClienteRow para o dict esperado pelos callbacks de pick mode (ANVISA)."""
    return {
        "id": row.id,
        "razao_social": row.razao_social,
        "cnpj": row.cnpj or "",
        "nome": row.nome or "",
        "whatsapp": row.whatsapp or "",
        "status": row.status or "",
    }


def execute_soft_delete(
    *,
    client_id: int,
    label_cli: str,
    top: Any,
    service: Any,
    refresh_lixeira: Callable,
    on_success: Callable,
    ask_fn: Callable,
    show_info_fn: Callable,
    show_error_fn: Callable,
) -> bool:
    """Executa o fluxo soft-delete: confirmação → serviço → feedback.

    Returns:
        True se o usuário confirmou (independente de sucesso/erro no serviço).
        False se o usuário cancelou o diálogo de confirmação.
    """
    confirm = ask_fn(
        top,
        "Enviar para Lixeira",
        f"Deseja enviar o cliente {label_cli} para a Lixeira?",
        confirm_label="Enviar para Lixeira",
    )
    if not confirm:
        return False

    log.info("[Clientes] Soft delete: cliente ID=%s", client_id)
    try:
        service.mover_cliente_para_lixeira(client_id)
        show_info_fn(top, "Lixeira", f"Cliente {label_cli} movido para a Lixeira.")
        log.info("[Clientes] Soft delete OK: cliente ID=%s", client_id)
        refresh_lixeira()
        on_success()
    except Exception as e:
        log.error("[Clientes] Erro ao mover cliente para lixeira ID=%s: %s", client_id, e, exc_info=True)
        show_error_fn(top, "Erro", f"Erro ao enviar cliente para lixeira: {e}")
    return True


def execute_hard_delete(
    *,
    client_id: int,
    label_cli: str,
    top: Any,
    service: Any,
    on_success: Callable,
    ask_danger_fn: Callable,
    show_info_fn: Callable,
    show_error_fn: Callable,
) -> bool:
    """Executa o fluxo hard-delete: confirmação → serviço → feedback.

    Returns:
        True se o usuário confirmou (independente de sucesso/erro no serviço).
        False se o usuário cancelou o diálogo de confirmação.
    """
    confirm = ask_danger_fn(
        top,
        "Excluir definitivamente",
        f"Tem certeza que deseja EXCLUIR DEFINITIVAMENTE o cliente {label_cli}?\n\nEsta ação não pode ser desfeita.",
        confirm_label="Excluir definitivamente",
    )
    if not confirm:
        return False

    log.info("[Clientes] Hard delete: cliente ID=%s", client_id)
    try:
        ok, errs = service.excluir_clientes_definitivamente([client_id])
        if errs:
            msgs = "\n".join(f"  • {e}" for _, e in errs)
            show_error_fn(top, "Erro ao excluir", f"Falha ao excluir cliente {label_cli}:\n{msgs}")
            log.error("[Clientes] Hard delete falhou para ID=%s: %s", client_id, errs)
            return True

        show_info_fn(top, "Excluído", f"Cliente {label_cli} excluído definitivamente.")
        log.info("[Clientes] Hard delete OK: cliente ID=%s", client_id)
        on_success()
    except Exception as e:
        log.error("[Clientes] Erro no hard delete do cliente ID=%s: %s", client_id, e, exc_info=True)
        show_error_fn(top, "Erro", f"Erro ao excluir definitivamente: {e}")
    return True


def normalize_phone_for_whatsapp(raw: str) -> str | None:
    """Normaliza número de telefone para formato WhatsApp.

    Remove formatação e adiciona código do país (55) se necessário.

    Args:
        raw: Número bruto (ex: '(11) 98765-4321', '+55 11 98765-4321')

    Returns:
        Número normalizado apenas com dígitos e prefixo 55, ou None se inválido

    Examples:
        >>> normalize_phone_for_whatsapp('(11) 98765-4321')
        '5511987654321'
        >>> normalize_phone_for_whatsapp('+55 11 98765-4321')
        '5511987654321'
        >>> normalize_phone_for_whatsapp('11987654321')
        '5511987654321'
        >>> normalize_phone_for_whatsapp('')
        None
    """
    if not raw or not raw.strip():
        return None

    # Remover tudo que não é dígito
    digits = "".join(c for c in raw if c.isdigit())

    if not digits:
        return None

    # Se não começa com 55, adicionar (código do Brasil)
    if not digits.startswith("55"):
        digits = "55" + digits

    # Validação básica: mínimo 12 dígitos (55 + DDD + número)
    if len(digits) < 12:
        return None

    return digits


def whatsapp_url(phone_digits: str) -> str:
    """Gera URL do WhatsApp Web/App.

    Args:
        phone_digits: Número normalizado apenas com dígitos (ex: '5511987654321')

    Returns:
        URL completa do WhatsApp

    Examples:
        >>> whatsapp_url('5511987654321')
        'https://wa.me/5511987654321'
    """
    return f"https://wa.me/{phone_digits}"


WHATSAPP_COLUMN_ID = "#5"
WHATSAPP_COLUMN_INDEX = 4


def resolve_whatsapp_click(
    region: str,
    row_id: str,
    column_id: str,
    values: tuple,
) -> str | None:
    """Determina se um clique na Treeview alvo a célula WhatsApp e retorna o valor bruto.

    Centraliza todos os guards da cadeia de decisão, permitindo teste unitário sem
    dependência de widget Tkinter.

    Args:
        region: Resultado de tree.identify_region (ex: 'cell', 'heading')
        row_id: Resultado de tree.identify_row
        column_id: Resultado de tree.identify_column (ex: '#5')
        values: Tuple retornado por tree.item(row_id, 'values')

    Returns:
        Valor bruto do campo WhatsApp (não vazio) se o clique deve acionar a ação,
        None em qualquer outro caso.
    """
    if region != "cell":
        return None
    if not row_id or not column_id:
        return None
    if column_id != WHATSAPP_COLUMN_ID:
        return None
    if not values or len(values) <= WHATSAPP_COLUMN_INDEX:
        return None
    whatsapp_raw = str(values[WHATSAPP_COLUMN_INDEX])
    if not whatsapp_raw or whatsapp_raw.strip() == "":
        return None
    return whatsapp_raw


def trigger_dialog_upload(dialog: Any) -> None:
    """Dispara o upload automático em um dialog ClientEditorDialog já aberto.

    Aciona ``dialog._on_enviar_documentos()`` se o método existir no objeto
    recebido. Silencia exceções para não interromper o fluxo principal.

    Args:
        dialog: Instância do dialog aberto (duck-typed: qualquer objeto com
            ``_on_enviar_documentos`` opcional e suporte a after()).
    """
    try:
        if hasattr(dialog, "_on_enviar_documentos"):
            dialog._on_enviar_documentos()  # pyright: ignore[reportAttributeAccessIssue]
    except Exception as e:
        log.error("[Clientes] Erro ao acionar upload automático: %s", e)


def editor_dialog_is_live(dialog: Any) -> bool:
    """Retorna True se o dialog não é None e winfo_exists() é truthy.

    Centraliza o guard "diálogo ainda visível" usado em múltiplos handlers,
    isolando a interação com Tkinter e silenciando exceções de widgets destruídos.

    Args:
        dialog: Qualquer objeto com winfo_exists() (duck-typed). Aceita None.

    Returns:
        True se dialog não é None e winfo_exists() retorna valor truthy.
        False se dialog é None, winfo_exists() retorna falsy, ou levanta exceção.
    """
    if dialog is None:
        return False
    try:
        return bool(dialog.winfo_exists())
    except Exception:
        return False


def execute_restore(
    *,
    client_id: int,
    label_cli: str,
    top: Any,
    service: Any,
    on_success: Callable,
    ask_fn: Callable,
    show_info_fn: Callable,
    show_error_fn: Callable,
) -> bool:
    """Executa o fluxo de restauração de cliente: confirmação → serviço → feedback.

    Returns:
        True se o usuário confirmou (independente de sucesso/erro no serviço).
        False se o usuário cancelou o diálogo de confirmação.
    """
    confirm = ask_fn(
        top,
        "Restaurar Cliente",
        f"Deseja restaurar o cliente {label_cli} para a lista de ativos?",
        confirm_label="Restaurar",
    )
    if not confirm:
        return False

    log.info("[Clientes] Restaurando cliente ID=%s da lixeira", client_id)
    try:
        service.restaurar_clientes_da_lixeira([client_id])
        show_info_fn(
            top,
            "Restaurado",
            f"Cliente {label_cli} restaurado com sucesso.\n\nEle voltará a aparecer na lista de ativos.",
        )
        log.info("[Clientes] Restauração OK: cliente ID=%s", client_id)
        on_success()
    except Exception as e:
        log.error("[Clientes] Erro ao restaurar cliente ID=%s: %s", client_id, e, exc_info=True)
        show_error_fn(top, "Erro", f"Erro ao restaurar cliente: {e}")
    return True


def execute_export(
    *,
    rows_to_export: list,
    top: Any,
    ask_save_fn: Callable,
    show_info_fn: Callable,
    show_error_fn: Callable,
    export_module: Any,
) -> None:
    """Executa o fluxo de exportação: diálogo de arquivo → exportar → feedback.

    Args:
        rows_to_export: Lista de ClienteRow a exportar.
        top: Widget toplevel para diálogos filhos.
        ask_save_fn: Callable para diálogo de salvar arquivo (ex.: filedialog.asksaveasfilename).
        show_info_fn: Callable para mostrar mensagem informativa.
        show_error_fn: Callable para mostrar mensagem de erro.
        export_module: Módulo de exportação (src.modules.clientes.core.export).
    """
    from pathlib import Path

    try:
        filetypes: list = [("CSV (separado por vírgulas)", "*.csv")]
        if export_module.is_xlsx_available():
            filetypes.append(("Excel (XLSX)", "*.xlsx"))

        filepath = ask_save_fn(
            parent=top,
            title="Exportar Clientes",
            defaultextension=".csv",
            filetypes=filetypes,
            initialfile="clientes_export",
        )
        if not filepath:
            log.debug("[Clientes] Exportação cancelada pelo usuário")
            return

        filepath_obj = Path(filepath)
        if filepath_obj.suffix.lower() == ".xlsx":
            export_module.export_clients_to_xlsx(rows_to_export, filepath_obj)
            format_name = "Excel"
        else:
            export_module.export_clients_to_csv(rows_to_export, filepath_obj)
            format_name = "CSV"

        show_info_fn(
            top,
            "Sucesso",
            f"Dados exportados com sucesso!\n\n"
            f"Arquivo: {filepath_obj.name}\n"
            f"Formato: {format_name}\n"
            f"Clientes: {len(rows_to_export)}",
        )
        log.info("[Clientes] Exportados %d clientes para %s", len(rows_to_export), filepath_obj)

    except ImportError as e:
        log.error("[Clientes] Erro de importação ao exportar: %s", e)
        show_error_fn(top, "Erro", f"Biblioteca necessária não está disponível:\n{e}")
    except Exception as e:
        log.error("[Clientes] Erro ao exportar: %s", e, exc_info=True)
        show_error_fn(top, "Erro", f"Erro ao exportar dados:\n{e}")


def identify_clicked_row(tree: Any, event: Any) -> str | None:
    """Identifica o item_id da linha clicada numa Treeview a partir de um evento de mouse.

    Retorna None se o clique não foi numa célula válida (ex.: heading, scrollbar,
    área vazia) ou se não há linha sob o cursor.

    Args:
        tree: Instancia de ttk.Treeview (ou compatível).
        event: Evento de mouse com atributos .x e .y.

    Returns:
        item_id (str) da linha clicada, ou None.
    """
    region = tree.identify("region", event.x, event.y)
    if region != "cell":
        return None
    item_id = tree.identify_row(event.y)
    return item_id or None


def resolve_selection_id(tree: Any) -> int | None:
    """Resolve o client_id do item selecionado numa Treeview.

    Retorna o inteiro da primeira coluna da seleção,
    ou None se não houver seleção ou os valores estiverem vazios.

    Args:
        tree: Instância de ttk.Treeview (ou compatível).

    Returns:
        int com o client_id, ou None.
    """
    selection = tree.selection()
    if not selection:
        return None
    values = tree.item(selection[0], "values")
    if not values:
        return None
    try:
        return int(values[0])
    except (ValueError, TypeError):
        return None


def handle_column_lock_region(region: str) -> str | None:
    """Decide se um evento em `region` deve ser bloqueado na Treeview.

    Retorna ``"break"`` para ``"separator"`` e ``"heading"`` (impedindo resize
    e reordenação de colunas), e ``None`` para qualquer outra região.

    Args:
        region: String retornada por ``tree.identify_region()``.

    Returns:
        ``"break"`` se a região deve ser bloqueada, ``None`` caso contrário.
    """
    if region in ("separator", "heading"):
        return "break"
    return None
