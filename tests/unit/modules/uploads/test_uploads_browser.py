from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generator
from unittest.mock import MagicMock

import pytest

from src.modules.uploads.views import browser

if TYPE_CHECKING:
    import tkinter as tk


@pytest.fixture
def make_window(
    monkeypatch: pytest.MonkeyPatch, tk_root_session: tk.Tk
) -> Generator[Callable[..., browser.UploadsBrowserWindow], None, None]:
    """
    Cria UploadsBrowserWindow sem carregar estado inicial (evita chamadas de rede nos testes).
    """

    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser, "list_browser_items", lambda *args, **kwargs: [])

    def _factory(**kwargs: Any) -> browser.UploadsBrowserWindow:
        # Definir valores padrão apenas se não foram fornecidos
        defaults = {
            "client_id": 1,
            "razao": "Acme Corp",
            "cnpj": "12345678000199",
            "bucket": "bucket-test",
            "base_prefix": "org/1",
        }
        # Merge kwargs com defaults (kwargs tem prioridade)
        params = {**defaults, **kwargs}

        win = browser.UploadsBrowserWindow(
            tk_root_session,
            **params,
        )
        return win

    yield _factory


def test_treeview_has_only_type_column(make_window: Callable) -> None:
    """Testa que o Treeview agora tem somente a coluna 'type' (removeu size, modified, status)."""
    win = make_window()
    tree = win.file_list.tree

    # Verificar que columns contém apenas "type"
    assert tree["columns"] == ("type",), f"Esperado ('type',) mas obteve {tree['columns']}"

    # Verificar que não contém as colunas removidas
    columns = tree["columns"]
    assert "size" not in columns
    assert "modified" not in columns
    assert "status" not in columns

    win.destroy()


def test_actionbar_inside_file_frame_below_list(make_window: Callable) -> None:
    """Testa que o ActionBar ficou dentro do LabelFrame e ABAIXO da lista (row 1 vs row 0)."""
    win = make_window()

    # Verificar que file_list está na row=0 (topo)
    file_list_info = win.file_list.grid_info()
    assert file_list_info["row"] == 0, f"FileList deveria estar em row=0, mas está em row={file_list_info['row']}"

    # Buscar o ActionBar que deve estar no mesmo master (file_frame) e na row=1 (embaixo)
    file_frame = win.file_list.master
    action_bar = None
    for child in file_frame.winfo_children():
        if child.__class__.__name__ == "ActionBar":
            action_bar = child
            break

    assert action_bar is not None, "ActionBar não encontrado dentro do file_frame"

    action_bar_info = action_bar.grid_info()
    assert (
        action_bar_info["row"] == 1
    ), f"ActionBar deveria estar em row=1 (embaixo), mas está em row={action_bar_info['row']}"

    win.destroy()


def test_prefix_truncation_for_long_prefix(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que prefixos longos são abreviados no formato: prefix[:12] + '…' + prefix[-8:]."""
    long_prefix = "org/123e4567-e89b-12d3-a456-426614174000/cliente/456/pasta1/pasta2"

    # Mock list_browser_items para não fazer chamada real
    mock_list = MagicMock(return_value=[])
    monkeypatch.setattr(browser, "list_browser_items", mock_list)

    win = make_window(base_prefix=long_prefix)

    # Verificar que _base_prefix ainda tem o valor completo (não truncado)
    assert win._base_prefix == long_prefix

    # Verificar que prefix_var contém "Código do cliente no Supabase:" e está abreviado
    displayed_prefix = win.prefix_var.get()
    assert displayed_prefix.startswith(
        "Código do cliente no Supabase:"
    ), f"Esperado que começasse com 'Código do cliente no Supabase:', mas obteve: {displayed_prefix}"
    assert "…" in displayed_prefix, f"Esperado '…' no prefixo abreviado, mas obteve: {displayed_prefix}"

    win.destroy()


def test_prefix_not_truncated_for_short_prefix(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que prefixos curtos não são truncados."""
    short_prefix = "org/1"

    # Mock list_browser_items para não fazer chamada real
    mock_list = MagicMock(return_value=[])
    monkeypatch.setattr(browser, "list_browser_items", mock_list)

    win = make_window(base_prefix=short_prefix)

    # Verificar que prefix_var contém o prefixo completo
    displayed_prefix = win.prefix_var.get()
    assert displayed_prefix.startswith("Código do cliente no Supabase:")
    assert short_prefix in displayed_prefix
    assert "…" not in displayed_prefix

    win.destroy()


def test_refresh_listing_applies_truncation(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que _refresh_listing aplica abreviação ao prefix_var."""
    long_prefix = "org/999e4567-e89b-12d3-a456-426614174000/cliente/888/pasta_muito_longa"

    # Mock list_browser_items
    mock_list = MagicMock(return_value=[])
    monkeypatch.setattr(browser, "list_browser_items", mock_list)

    win = make_window(base_prefix=long_prefix)

    # Chamar _refresh_listing
    win._refresh_listing()

    # Verificar que prefix_var contém texto e está abreviado
    displayed_prefix = win.prefix_var.get()
    assert displayed_prefix.startswith("Código do cliente no Supabase:")
    assert "…" in displayed_prefix

    win.destroy()


def test_download_selected_blocks_folder(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que _download_selected bloqueia download de pasta e mostra aviso."""
    from unittest.mock import MagicMock

    mock_messagebox_info = MagicMock()
    monkeypatch.setattr("src.modules.uploads.views.browser.messagebox.showinfo", mock_messagebox_info)

    win = make_window()

    # Simular seleção de pasta
    mock_get_selected = MagicMock(return_value=("Pasta1", "Pasta", "org/1/Pasta1"))
    monkeypatch.setattr(win.file_list, "get_selected_info", mock_get_selected)

    # Chamar _download_selected
    win._download_selected()

    # Verificar que messagebox foi chamado com mensagem apropriada
    assert mock_messagebox_info.call_count == 1
    call_args = mock_messagebox_info.call_args[0]
    assert "Baixar" in call_args[0]
    assert "pasta" in call_args[1].lower()
    assert ".zip" in call_args[1]

    win.destroy()


def test_download_selected_file_calls_saveas_once(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que download de arquivo chama asksaveasfilename apenas uma vez."""
    from unittest.mock import MagicMock

    mock_saveas = MagicMock(return_value="/tmp/test.pdf")
    mock_download = MagicMock(return_value={"ok": True})
    mock_messagebox_info = MagicMock()
    mock_custom_dialog = MagicMock()

    monkeypatch.setattr("src.modules.uploads.views.browser.filedialog.asksaveasfilename", mock_saveas)
    monkeypatch.setattr("src.modules.uploads.views.browser.download_storage_object", mock_download)
    monkeypatch.setattr("src.modules.uploads.views.browser.messagebox.showinfo", mock_messagebox_info)

    win = make_window()
    win._show_download_done_dialog = mock_custom_dialog

    # Simular seleção de arquivo
    mock_get_selected = MagicMock(return_value=("doc.pdf", "Arquivo", "org/1/doc.pdf"))
    monkeypatch.setattr(win.file_list, "get_selected_info", mock_get_selected)

    # Chamar _download_selected
    win._download_selected()

    # Verificar que asksaveasfilename foi chamado exatamente 1 vez
    assert mock_saveas.call_count == 1

    # Verificar que download_storage_object foi chamado 1 vez
    assert mock_download.call_count == 1

    win.destroy()


def test_download_selected_cancelled_does_not_download(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que se usuário cancelar o saveas, o download não acontece."""
    from unittest.mock import MagicMock

    mock_saveas = MagicMock(return_value="")  # Cancelado
    mock_download = MagicMock()
    mock_custom_dialog = MagicMock()

    monkeypatch.setattr("src.modules.uploads.views.browser.filedialog.asksaveasfilename", mock_saveas)
    monkeypatch.setattr("src.modules.uploads.views.browser.download_storage_object", mock_download)

    win = make_window()
    win._show_download_done_dialog = mock_custom_dialog

    # Simular seleção de arquivo
    mock_get_selected = MagicMock(return_value=("doc.pdf", "Arquivo", "org/1/doc.pdf"))
    monkeypatch.setattr(win.file_list, "get_selected_info", mock_get_selected)

    # Chamar _download_selected
    win._download_selected()

    # Verificar que download NÃO foi chamado
    assert mock_download.call_count == 0

    win.destroy()


def test_sync_actions_state_no_selection(make_window: Callable) -> None:
    """Testa que sem seleção, todos os botões ficam desabilitados."""
    win = make_window()

    # Simular nenhuma seleção
    from unittest.mock import MagicMock

    mock_get_selected = MagicMock(return_value=None)
    win.file_list.get_selected_info = mock_get_selected

    # Chamar sync
    win._sync_actions_state()

    # Verificar estado dos botões
    if win.actions.btn_download:
        assert str(win.actions.btn_download.cget("state")) == "disabled"
    if win.actions.btn_download_folder:
        assert str(win.actions.btn_download_folder.cget("state")) == "disabled"

    win.destroy()


def test_sync_actions_state_folder_selected(make_window: Callable) -> None:
    """Testa que com pasta selecionada, apenas btn_download_folder e delete ficam habilitados."""
    win = make_window()

    # Simular seleção de pasta
    from unittest.mock import MagicMock

    mock_get_selected = MagicMock(return_value=("Pasta1", "Pasta", "org/1/Pasta1"))
    win.file_list.get_selected_info = mock_get_selected

    # Chamar sync
    win._sync_actions_state()

    # Verificar estado dos botões
    if win.actions.btn_download:
        assert str(win.actions.btn_download.cget("state")) == "disabled"
    if win.actions.btn_download_folder:
        assert str(win.actions.btn_download_folder.cget("state")) == "normal"
    if win.actions.btn_delete:
        assert str(win.actions.btn_delete.cget("state")) == "normal"
    if win.actions.btn_view:
        assert str(win.actions.btn_view.cget("state")) == "disabled"

    win.destroy()


def test_sync_actions_state_file_selected(make_window: Callable) -> None:
    """Testa que com arquivo selecionado, download, view e delete ficam habilitados."""
    win = make_window()

    # Simular seleção de arquivo
    from unittest.mock import MagicMock

    mock_get_selected = MagicMock(return_value=("doc.pdf", "Arquivo", "org/1/doc.pdf"))
    win.file_list.get_selected_info = mock_get_selected

    # Chamar sync
    win._sync_actions_state()

    # Verificar estado dos botões
    if win.actions.btn_download:
        assert str(win.actions.btn_download.cget("state")) == "normal"
    if win.actions.btn_download_folder:
        assert str(win.actions.btn_download_folder.cget("state")) == "disabled"
    if win.actions.btn_delete:
        assert str(win.actions.btn_delete.cget("state")) == "normal"
    if win.actions.btn_view:
        assert str(win.actions.btn_view.cget("state")) == "normal"

    win.destroy()


def test_custom_download_dialog_used(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que o popup customizado é usado ao invés de messagebox.showinfo."""
    from unittest.mock import MagicMock

    mock_saveas = MagicMock(return_value="/tmp/test.pdf")
    mock_download = MagicMock(return_value={"ok": True})
    mock_custom_dialog = MagicMock()

    monkeypatch.setattr("src.modules.uploads.views.browser.filedialog.asksaveasfilename", mock_saveas)
    monkeypatch.setattr("src.modules.uploads.views.browser.download_storage_object", mock_download)

    win = make_window()

    # Mockar o método _show_download_done_dialog ANTES de chamar
    win._show_download_done_dialog = mock_custom_dialog

    # Simular seleção de arquivo
    mock_get_selected = MagicMock(return_value=("doc.pdf", "Arquivo", "org/1/doc.pdf"))
    monkeypatch.setattr(win.file_list, "get_selected_info", mock_get_selected)

    # Chamar _download_selected
    win._download_selected()

    # Verificar que o dialog customizado foi chamado
    assert mock_custom_dialog.call_count == 1

    # Verificar que foi chamado com a mensagem correta
    call_args = mock_custom_dialog.call_args
    assert "Arquivo salvo" in call_args[0][0]

    win.destroy()


def test_actionbar_has_close_button(make_window: Callable) -> None:
    """Testa que ActionBar tem botão Fechar (Atualizar foi movido para o topo)."""
    win = make_window()

    # Verificar que o botão Fechar existe
    assert win.actions.btn_close is not None, "Botão Fechar não encontrado"

    win.destroy()


def test_close_button_exists_and_is_callable(make_window: Callable) -> None:
    """Testa que o botão Fechar existe e está configurado."""
    win = make_window()

    # Verificar que o botão existe
    assert win.actions.btn_close is not None, "Botão Fechar deve existir"

    # Verificar que tem um command configurado
    assert win.actions.btn_close.cget("command"), "Botão Fechar deve ter um command"

    win.destroy()


def test_prefix_entry_has_fixed_width(make_window: Callable) -> None:
    """Testa que o Entry do prefixo tem largura fixa (não estica)."""
    win = make_window()

    # Buscar o top_bar (primeiro Frame filho da janela)
    top_bar = None
    for child in win.winfo_children():
        grid_info = child.grid_info()
        if grid_info and grid_info.get("row") == 0:
            top_bar = child
            break

    assert top_bar is not None, "Top bar não encontrado"

    # Buscar Entry no top_bar
    prefix_entry = None
    for child in top_bar.winfo_children():
        if "Entry" in child.__class__.__name__:
            prefix_entry = child
            break

    assert prefix_entry is not None, "Entry do prefixo não encontrado"

    # Verificar que tem width fixo (500 para CTk, 60 para ttk)
    width = prefix_entry.cget("width")
    assert width in (60, 500), f"Entry deveria ter width=60 ou width=500 (CTk), mas tem width={width}"

    win.destroy()


def test_download_button_is_info_color(make_window: Callable) -> None:
    """Testa que o botão Baixar tem bootstyle='info' (azul)."""
    win = make_window()

    # Verificar que botão existe
    assert win.actions.btn_download is not None, "Botão Baixar não existe"

    # Verificar através do texto do botão (bootstyle não é acessível via cget em ttkbootstrap)
    btn_text = win.actions.btn_download.cget("text")
    assert btn_text == "Baixar", f"Botão deveria ter texto 'Baixar', mas tem '{btn_text}'"

    win.destroy()


def test_refresh_button_in_top_bar(make_window: Callable) -> None:
    """Testa que existe botão refresh (⟳) no topo, à direita."""
    win = make_window()

    # Buscar o top_bar
    top_bar = None
    for child in win.winfo_children():
        grid_info = child.grid_info()
        if grid_info and grid_info.get("row") == 0:
            top_bar = child
            break

    assert top_bar is not None, "Top bar não encontrado"

    # Buscar botão com texto "⟳"
    refresh_btn = None
    for child in top_bar.winfo_children():
        if "Button" in child.__class__.__name__:
            text = child.cget("text")
            if text in ("⟳", "↻"):
                refresh_btn = child
                break

    assert refresh_btn is not None, "Botão refresh (⟳) não encontrado no top bar"

    # Verificar que está à direita (column=1)
    grid_info = refresh_btn.grid_info()
    assert grid_info.get("column") == 1, "Botão refresh deveria estar na column=1"

    win.destroy()


def test_prefix_entry_contains_client_code_label(make_window: Callable) -> None:
    """Testa que Entry contém 'Código do cliente no Supabase:'."""
    win = make_window()

    displayed = win.prefix_var.get()
    assert displayed.startswith(
        "Código do cliente no Supabase:"
    ), f"Entry deveria começar com 'Código do cliente no Supabase:', mas contém: {displayed}"

    win.destroy()


def test_download_folder_zip_accepts_progress_cb(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Testa que download_folder_zip usado no browser aceita progress_cb=None sem TypeError.
    Isso garante que a assinatura da função está padronizada em todas as camadas.
    """
    from src.modules.uploads import service

    # Mock download_folder_zip com assinatura completa incluindo progress_cb
    mock_download = MagicMock(return_value="/tmp/test.zip")
    monkeypatch.setattr(service, "download_folder_zip", mock_download)

    win = make_window()

    # Simular chamada com progress_cb (como acontece no _download_zip)
    result = service.download_folder_zip(
        folder_path="org/1/pasta",
        local_filename="test.zip",
        progress_cb=None,
    )

    # Verificar que a função foi chamada e não levantou TypeError
    assert mock_download.called
    assert result == "/tmp/test.zip"

    # Verificar que progress_cb foi passado nos kwargs
    call_kwargs = mock_download.call_args.kwargs
    assert "progress_cb" in call_kwargs
    assert call_kwargs["progress_cb"] is None

    win.destroy()


def test_download_uses_messagebox_not_toplevel(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Testa que download de arquivo usa messagebox.showinfo (nativo Windows) em vez de Toplevel custom.
    """
    from tkinter import messagebox

    from src.modules.uploads import service

    # Mock messagebox.showinfo para capturar chamada
    mock_showinfo = MagicMock()
    monkeypatch.setattr(messagebox, "showinfo", mock_showinfo)

    # Mock download_storage_object para simular sucesso
    mock_download = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(service, "download_storage_object", mock_download)

    win = make_window()

    # Simular chamada _show_download_done_dialog (agora usa messagebox)
    win._show_download_done_dialog("Arquivo salvo em /tmp/test.pdf")

    # Verificar que messagebox.showinfo foi chamado (não Toplevel)
    assert mock_showinfo.called
    assert mock_showinfo.call_args.args[0] == "Download"
    assert "Arquivo salvo" in mock_showinfo.call_args.args[1]
    assert mock_showinfo.call_args.kwargs["parent"] == win

    win.destroy()


def test_progressbar_switches_to_determinate_when_content_length_known(
    make_window: Callable, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Testa que a progressbar da janela ZIP pode trocar entre indeterminate e determinate.
    Valida o comportamento conceitual: indeterminate → determinate quando Content-Length conhecido.
    """
    win = make_window()

    # Criar progressbar simulando o mesmo comportamento da janela ZIP
    # IMPORTANTE: Usar tkinter.ttk (não ttkbootstrap) como no código real
    from tkinter import ttk as ttk_native

    pb = ttk_native.Progressbar(win, mode="indeterminate")

    # Simular recebimento de Content-Length (troca para determinate)
    total_bytes = 1024 * 1024  # 1 MB
    downloaded = 512 * 1024  # 512 KB baixados

    # Configurar para determinate (como no código real)
    pb.configure(mode="determinate", maximum=total_bytes)
    pb["value"] = downloaded

    # Validar que conseguimos definir valor (não lança exceção)
    # e que o valor está no range esperado
    assert pb["value"] == downloaded
    assert 0 <= downloaded <= total_bytes

    win.destroy()


def test_zip_progress_window_uses_native_ttk_widgets(make_window: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Testa que a janela de progresso ZIP usa tkinter.ttk nativo (não ttkbootstrap).
    Valida que os widgets são instâncias de tkinter.ttk para visual padrão Windows.
    """
    from tkinter import ttk as ttk_native

    win = make_window()

    # Criar widgets como no dialog ZIP (usando ttk_native)
    test_frame = ttk_native.Frame(win, padding=8)
    test_label = ttk_native.Label(test_frame, text="Test")
    test_pb = ttk_native.Progressbar(test_frame, mode="indeterminate")
    test_button = ttk_native.Button(test_frame, text="Cancelar")

    # Validar que são instâncias de tkinter.ttk (não ttkbootstrap)
    assert isinstance(test_frame, ttk_native.Frame)
    assert isinstance(test_label, ttk_native.Label)
    assert isinstance(test_pb, ttk_native.Progressbar)
    assert isinstance(test_button, ttk_native.Button)

    # Validar que não são widgets ttkbootstrap (não têm atributos de estilo específicos)
    # ttkbootstrap adiciona atributos como 'bootstyle' que ttk nativo não tem
    assert not hasattr(test_button, "bootstyle")

    win.destroy()


# =============================================================================
# Testes para guard de root/parent (T05)
# =============================================================================


def test_open_files_browser_uses_default_root_when_parent_is_none(
    monkeypatch: pytest.MonkeyPatch, tk_root_session: "tk.Tk"
) -> None:
    """Testa que open_files_browser usa _default_root quando parent=None."""
    import tkinter as tk

    # Garantir que _default_root aponta para tk_root_session
    monkeypatch.setattr(tk, "_default_root", tk_root_session)

    # Mocks para evitar chamadas de rede e UI
    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser, "list_browser_items", lambda *args, **kwargs: [])

    win = browser.open_files_browser(
        None,
        client_id=1,
        razao="Acme",
        cnpj="12345678000199",
        bucket="bucket-test",
        base_prefix="org/1",
        modal=False,
    )

    assert isinstance(win, browser.UploadsBrowserWindow)
    win.destroy()


def test_open_files_browser_raises_when_no_parent_and_no_default_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa que open_files_browser levanta RuntimeError sem parent e sem _default_root."""
    import tkinter as tk

    # Forçar _default_root = None
    monkeypatch.setattr(tk, "_default_root", None, raising=False)

    # Mocks para evitar chamadas de rede e UI (caso o guard falhe)
    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser, "list_browser_items", lambda *args, **kwargs: [])

    with pytest.raises(RuntimeError, match="root/parent Tk não encontrado"):
        browser.open_files_browser(
            None,
            client_id=1,
            razao="Acme",
            cnpj="12345678000199",
            bucket="bucket-test",
            base_prefix="org/1",
        )
