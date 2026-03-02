# -*- coding: utf-8 -*-
"""Diálogo de edição/criação de cliente para ClientesV2.

FASE 4 FINAL: Dialog 100% CustomTkinter (CTkToplevel).
MIGRAÇÃO COMPLETA: Equivalente ao formulário legado com todos os campos e botões.

FASE 5: Refatorado em mixins para melhor manutenção:
  - _editor_ui_mixin.py: Construção de UI
  - _editor_data_mixin.py: Dados e persistência
  - _editor_actions_mixin.py: Callbacks e ações
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import APP_BG
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash, apply_window_icon

from src.modules.clientes.ui.views._editor_ui_mixin import EditorUIMixin
from src.modules.clientes.ui.views._editor_data_mixin import EditorDataMixin
from src.modules.clientes.ui.views._editor_actions_mixin import EditorActionsMixin

log = logging.getLogger(__name__)


# ============================================================================
# Helpers locais para lidar com dict OU objeto Cliente
# ============================================================================


def _safe_get(obj: Any, key: str, default: Any = "") -> Any:
    """Extrai valor de dict OU objeto (aceita ambos).

    Usado para trabalhar com objetos Cliente que podem vir como dict
    (do Supabase) ou como dataclass/model (do ORM).

    Args:
        obj: Dict ou objeto (dataclass, Cliente, etc.)
        key: Chave/atributo a buscar
        default: Valor padrão se não encontrar

    Returns:
        Valor extraído ou default
    """
    if obj is None:
        return default

    # Tentar como dict primeiro (mais comum)
    if isinstance(obj, Mapping):
        return obj.get(key, default)

    # Tentar como objeto (getattr)
    return getattr(obj, key, default)


def _conflict_desc(conflict: Any) -> str:
    """Gera descrição amigável de um conflito de cliente.

    Args:
        conflict: Cliente conflitante (dict ou objeto)

    Returns:
        String formatada: "ID 123 - Nome da Empresa (12.345.678/0001-90)"
    """
    if conflict is None:
        return "cliente desconhecido"

    cid = _safe_get(conflict, "id", "?")
    razao = _safe_get(conflict, "razao_social", "cliente desconhecido")
    cnpj = _safe_get(conflict, "cnpj", "")

    desc = f"ID {cid} - {razao}"
    if cnpj:
        desc += f" ({cnpj})"

    return desc


class ClientEditorDialog(EditorActionsMixin, EditorDataMixin, EditorUIMixin, ctk.CTkToplevel):
    """Diálogo para criar ou editar cliente.

    Usa apenas CustomTkinter (CTkToplevel, CTkLabel, CTkEntry, CTkButton).
    MIGRAÇÃO COMPLETA: Equivalente ao formulário legado com layout duas colunas,
    todos os campos (incluindo internos) e todos os botões.

    Mixins (Fase 5):
      - EditorUIMixin: _build_ui, _build_left_panel, _build_right_panel, etc.
      - EditorDataMixin: _load_client_data, _validate_fields, _on_save_clicked, etc.
      - EditorActionsMixin: _on_senhas, _on_arquivos, _on_cartao_cnpj, etc.
    """

    def __init__(
        self,
        parent: Any,
        client_id: Optional[int] = None,
        on_save: Optional[Callable[[dict], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente para editar (None = novo)
            on_save: Callback chamado após salvar com sucesso
            on_close: Callback chamado quando diálogo é fechado
            session_id: ID da sessão para logs (opcional)
        """
        self.session_id = session_id or "unknown"
        log.info(f"[ClientEditorDialog:{self.session_id}] Iniciando criação")

        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.on_save = on_save
        self.on_close = on_close
        self._client_data: Optional[dict] = None

        # After-job IDs — cancelados em cleanup (Fase 12: TclError guard)
        self._setup_modal_job: Optional[str] = None
        self._placeholder_job: Optional[str] = None

        # ANTI-FLASH: Ocultar imediatamente (withdraw + offscreen multi-monitor safe)
        prepare_hidden_window(self)
        log.debug(f"[ClientEditorDialog:{self.session_id}] Janela preparada (hidden + offscreen)")

        # Configurar cores de fundo (evita flash branco)
        self.configure(fg_color=APP_BG)

        # Configurar janela (invisível)
        self._set_window_title()

        # Usar Toplevel.resizable para evitar flicker
        try:
            from tkinter import Toplevel

            Toplevel.resizable(self, False, False)
        except Exception:
            self.resizable(False, False)

        # Modal: transient ANTES de mostrar
        self.transient(parent)

        # Construir UI completa (ainda invisível)
        self._build_ui()  # pyright: ignore[reportAttributeAccessIssue]
        log.debug(f"[ClientEditorDialog:{self.session_id}] UI construída")

        # Sincronizar altura do spacer direito após renderização (pixel-perfect)
        self.after_idle(self._sync_right_spacer_height)  # pyright: ignore[reportAttributeAccessIssue]

        # Carregar dados ANTES de exibir (se editando)
        # CRÍTICO: Previne flash de campos vazios
        if client_id is not None:
            self._load_client_data()  # pyright: ignore[reportAttributeAccessIssue]
            log.debug(f"[ClientEditorDialog:{self.session_id}] Dados carregados")

        # Forçar renderização completa ANTES de mostrar
        self.update_idletasks()

        # Aplicar ícone do app (com reapply em 250ms para CTkToplevel)
        apply_window_icon(self)

        # Mostrar janela centralizada sem flash (offscreen → render → onscreen)
        show_centered_no_flash(self, parent, width=1100, height=700)
        log.debug(f"[ClientEditorDialog:{self.session_id}] Janela visível e centralizada")

        # Ativar placeholders APÓS janela visível (Novo Cliente)
        # Delay de 30ms garante que a janela já está completamente renderizada
        if client_id is None:
            self._placeholder_job = self.after(30, self._activate_all_placeholders)  # pyright: ignore[reportAttributeAccessIssue]

        # Aplicar titlebar escura (Windows) - APÓS deiconify (precisa de handle mapeado)
        try:
            set_win_dark_titlebar(self)
        except Exception as e:
            log.debug(f"[ClientEditorDialog:{self.session_id}] Erro titlebar: {e}")

        # Modal: grab_set após janela visível (com retry se não-viewable)
        self._setup_modal_job = self.after(10, lambda: self._setup_modal_safe())

        log.info(f"[ClientEditorDialog:{self.session_id}] PRONTO")

        # Registrar callback de fechamento
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _setup_modal_safe(self, retry_count: int = 0) -> None:
        """Configura comportamento modal APENAS quando janela está viewable.

        Args:
            retry_count: Contador de tentativas (máx 10 para evitar loop infinito)
        """
        max_retries = 10
        retry_delay_ms = 50

        try:
            # Verificar se a janela ainda existe
            if not self.winfo_exists():
                log.warning(f"[ClientEditorDialog:{self.session_id}] Janela não existe mais, abortando modal setup")
                return

            # Verificar se a janela está viewable (mapeada e visível)
            if not self.winfo_viewable():
                if retry_count < max_retries:
                    log.info(
                        f"[ClientEditorDialog:{self.session_id}] "
                        f"Janela não-viewable (tentativa {retry_count + 1}/{max_retries}), "
                        f"reagendando grab_set em {retry_delay_ms}ms"
                    )
                    self.after(retry_delay_ms, lambda: self._setup_modal_safe(retry_count + 1))
                    return
                else:
                    log.warning(
                        f"[ClientEditorDialog:{self.session_id}] "
                        f"Janela não ficou viewable após {max_retries} tentativas, "
                        f"abortando grab_set (modal pode não funcionar)"
                    )
                    return

            # Janela está viewable, aplicar grab_set
            self.grab_set()
            log.info(f"[ClientEditorDialog:{self.session_id}] grab_set aplicado com sucesso (viewable=True)")

        except Exception as e:
            log.error(f"[ClientEditorDialog:{self.session_id}] Erro ao aplicar grab_set: {e}")

    def _set_window_title(self) -> None:
        """Define título da janela conforme legado."""
        if self.client_id is None:
            self.title("Novo Cliente")
        else:
            # Título será atualizado após carregar dados
            self.title(f"Editar Cliente - ID: {self.client_id}")

    def _on_window_close(self) -> None:
        """Handler quando usuário fecha a janela (X).

        Notifica parent que diálogo foi fechado e faz cleanup completo.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Usuário fechou a janela")
        self._cleanup_and_destroy()

    def _cleanup_and_destroy(self) -> None:
        """Cleanup centralizado: libera grab, notifica parent e destrói janela.

        Usado por:
        - _on_window_close (botão X)
        - _on_cancel (botão Cancelar / tecla ESC)
        """
        # Cancelar after-jobs pendentes antes de destruir (Fase 12: TclError guard)
        for _attr in ("_setup_modal_job", "_placeholder_job"):
            _job = getattr(self, _attr, None)
            if _job is not None:
                try:
                    self.after_cancel(_job)
                except Exception:
                    pass
                setattr(self, _attr, None)

        try:
            # Liberar grab ANTES de destruir (previne grab preso)
            self.grab_release()
            log.debug(f"[ClientEditorDialog:{self.session_id}] grab_release executado")
        except Exception as e:
            log.debug(f"[ClientEditorDialog:{self.session_id}] Erro em grab_release: {e}")

        try:
            # Notificar parent que diálogo foi fechado
            if self.on_close:
                self.on_close()
        except Exception as e:
            log.error(f"[ClientEditorDialog:{self.session_id}] Erro no callback on_close: {e}")

        try:
            # Destruir janela
            self.destroy()
        except Exception as e:
            log.error(f"[ClientEditorDialog:{self.session_id}] Erro ao destruir janela: {e}")
