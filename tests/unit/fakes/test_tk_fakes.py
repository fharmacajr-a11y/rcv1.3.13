# -*- coding: utf-8 -*-
"""Fakes minimalistas para componentes Tkinter (testes headless)."""

import tkinter as tk
from typing import Any, Callable


# ============================================================================
# MF48: Fakes completos para popup de histórico
# ============================================================================


class FakeToplevel:
    """Fake para tk.Toplevel sem UI real."""

    def __init__(self, master=None, exists: bool = True, **kwargs):
        self._exists = exists
        self._destroyed = False
        self._title = ""
        self._resizable = (True, True)
        self._transient = None
        self._grab = False
        self._protocol_handlers: dict[str, Callable[[], None]] = {}
        self._children: list[Any] = []
        self._geometry = ""
        self.lift_called = False
        self.focus_called = False
        self.deiconify_called = False
        self.withdraw_called = False
        self.update_idletasks_called = False

    def winfo_exists(self) -> bool:
        """Retorna se janela existe."""
        return self._exists and not self._destroyed

    def winfo_children(self) -> list[Any]:
        """Retorna children."""
        return self._children.copy()

    def winfo_width(self) -> int:
        """Retorna largura."""
        return 800

    def winfo_height(self) -> int:
        """Retorna altura."""
        return 600

    def winfo_screenwidth(self) -> int:
        """Retorna largura da tela."""
        return 1920

    def winfo_screenheight(self) -> int:
        """Retorna altura da tela."""
        return 1080

    def winfo_reqwidth(self) -> int:
        """Retorna largura requisitada."""
        return 750

    def winfo_reqheight(self) -> int:
        """Retorna altura requisitada."""
        return 480

    def title(self, text: str | None = None) -> str | None:
        """Get/set título."""
        if text is not None:
            self._title = text
            return None
        return self._title

    def resizable(self, width: bool, height: bool) -> None:
        """Define resizable."""
        self._resizable = (width, height)

    def transient(self, master: Any = None) -> None:
        """Define transient."""
        self._transient = master

    def grab_set(self) -> None:
        """Seta grab."""
        self._grab = True

    def grab_release(self) -> None:
        """Libera grab."""
        self._grab = False

    def protocol(self, name: str, func: Callable[[], None] | None = None) -> None:
        """Registra protocol handler."""
        if func is not None:
            self._protocol_handlers[name] = func

    def destroy(self) -> None:
        """Destrói janela."""
        self._destroyed = True
        self._exists = False

    def lift(self) -> None:
        """Traz para frente."""
        self.lift_called = True

    def focus_force(self) -> None:
        """Força foco."""
        self.focus_called = True

    def geometry(self, spec: str | None = None) -> str | None:
        """Get/set geometry."""
        if spec is not None:
            self._geometry = spec
            return None
        return self._geometry

    def deiconify(self) -> None:
        """Deiconify."""
        self.deiconify_called = True

    def withdraw(self) -> None:
        """Withdraw (oculta janela)."""
        self.withdraw_called = True

    def update_idletasks(self) -> None:
        """Update idletasks (no-op)."""
        self.update_idletasks_called = True

    def update(self) -> None:
        """Update (no-op)."""
        pass

    def attributes(self, name: str, value: Any = None) -> Any:
        """Get/set attributes."""
        return None

    def winfo_x(self) -> int:
        """Retorna posição X."""
        return 100

    def winfo_y(self) -> int:
        """Retorna posição Y."""
        return 100

    def winfo_rootx(self) -> int:
        """Retorna posição X da janela no root."""
        return 100

    def winfo_rooty(self) -> int:
        """Retorna posição Y da janela no root."""
        return 100

    def after(self, ms: int, func: Callable[[], None] | None = None) -> str | None:
        """Schedule callback (executa imediatamente para testes)."""
        if func is not None:
            func()
        return None

    def add_child(self, child: Any) -> None:
        """Adiciona child (helper para testes)."""
        self._children.append(child)


class FakeWidgetBase:
    """Base para widgets fake."""

    def __init__(self, master=None, **kwargs):
        self._master = master
        self._config = kwargs.copy()
        self._children: list[Any] = []
        self._packed = False
        self._gridded = False
        self._grid_config: dict[str, Any] = {}

    def pack(self, **kwargs) -> None:
        """Pack widget."""
        self._packed = True

    def grid(self, **kwargs) -> None:
        """Grid widget."""
        self._gridded = True
        self._grid_config = kwargs

    def configure(self, **kwargs) -> None:
        """Configura widget."""
        self._config.update(kwargs)

    def cget(self, option: str) -> Any:
        """Retorna config."""
        return self._config.get(option, "")

    def columnconfigure(self, index: int, **kwargs) -> None:
        """Configura coluna (no-op)."""
        pass

    def winfo_children(self) -> list[Any]:
        """Retorna children."""
        return self._children.copy()

    def add_child(self, child: Any) -> None:
        """Adiciona child (helper para testes)."""
        self._children.append(child)

    def bind(self, event: str, callback: Any) -> None:
        """Bind evento."""
        pass

    def unbind(self, event: str) -> None:
        """Unbind evento."""
        pass


class FakeFrame(FakeWidgetBase):
    """Fake para ttk.Frame."""

    pass


class FakeLabel(FakeWidgetBase):
    """Fake para ttk.Label."""

    def __init__(self, master=None, text: str = "", **kwargs):
        super().__init__(master, text=text, **kwargs)


class FakeLabelframe(FakeWidgetBase):
    """Fake para ttk.Labelframe."""

    def __init__(self, master=None, text: str = "", **kwargs):
        super().__init__(master, text=text, **kwargs)


class FakeScrollbar(FakeWidgetBase):
    """Fake para ttk.Scrollbar."""

    def __init__(self, master=None, orient: str = "vertical", command: Any = None, **kwargs):
        super().__init__(master, orient=orient, **kwargs)
        self._command = command

    def set(self, first: float, last: float) -> None:
        """Set scrollbar position."""
        pass


class FakeStringVar:
    """Fake para tk.StringVar."""

    def __init__(self, master=None, value: str = "", **kwargs):
        self._value = value

    def set(self, value: str) -> None:
        """Set value."""
        self._value = value

    def get(self) -> str:
        """Get value."""
        return self._value


# ============================================================================
# Fakes originais (mantidos para compatibilidade)
# ============================================================================


class FakeButton(FakeWidgetBase):
    """Fake para ttk.Button sem UI real."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.state_value = kwargs.get("state", "normal")
        self.text = kwargs.get("text", "")

    def configure(self, **kwargs):
        """Atualiza state."""
        super().configure(**kwargs)
        if "state" in kwargs:
            self.state_value = kwargs["state"]

    def cget(self, option: str) -> Any:
        """Retorna config."""
        if option == "state":
            return self.state_value
        return super().cget(option)


class FakeVar:
    """Fake para tk.StringVar/IntVar."""

    def __init__(self, value: Any = ""):
        self._value = value

    def set(self, value: Any):
        self._value = value

    def get(self) -> Any:
        return self._value


class FakeMenu:
    """Fake para tk.Menu sem UI real."""

    def __init__(self, *args, **kwargs):
        self.commands = []
        self.separators = 0
        self.popup_called = False
        self.popup_x = 0
        self.popup_y = 0

    def add_command(self, label: str = "", command=None, state: str = "normal"):
        """Adiciona comando ao menu."""
        self.commands.append({"label": label, "command": command, "state": state})

    def add_separator(self):
        """Adiciona separador."""
        self.separators += 1

    def delete(self, start: int | str, end: int | str | None = None):
        """Remove items do menu."""
        if start == 0 and end == "end":
            self.commands = []
            self.separators = 0

    def tk_popup(self, x_root, y_root):
        """Simula popup."""
        self.popup_called = True
        self.popup_x = x_root
        self.popup_y = y_root

    def grab_release(self):
        """Release grab (no-op)."""
        pass


class FakeTreeview:
    """Fake para ttk.Treeview sem UI real."""

    def __init__(self, master=None, columns: tuple = (), **kwargs):
        self._master = master
        self._items: dict[str, dict[str, Any]] = {}
        self._selection: list[str] = []
        self._identify_row_result = ""
        self._children: list[str] = []
        self._columns = columns
        self._headings: dict[str, dict[str, Any]] = {}
        self._column_config: dict[str, dict[str, Any]] = {}
        self._yscrollcommand: Callable[[float, float], None] | None = None
        self._packed = False

    def selection(self) -> list[str]:
        """Retorna seleção atual."""
        return self._selection.copy()

    def selection_set(self, iid: str):
        """Define seleção."""
        self._selection = [iid]

    def focus(self, iid: str = ""):
        """Define focus."""
        if iid:
            self._focus_item = iid

    def see(self, iid: str):
        """Scroll para item (no-op)."""
        pass

    def identify_row(self, y: int) -> str:
        """Retorna iid na posição y."""
        return self._identify_row_result

    def item(self, iid: str, **kwargs) -> dict[str, Any]:
        """Retorna/atualiza item data."""
        if kwargs:
            if iid not in self._items:
                self._items[iid] = {"values": []}
            self._items[iid].update(kwargs)
            return {}
        return self._items.get(iid, {"values": []})

    def get_children(self, item: str = "") -> list[str]:
        """Retorna children."""
        return self._children.copy()

    def insert(self, parent: str, index: int | str, iid: str = "", values: tuple = (), **kwargs) -> str:
        """Insere item."""
        if not iid:
            iid = f"I{len(self._items):03d}"
        self._items[iid] = {"values": list(values)}
        self._children.append(iid)
        return iid

    def delete(self, iid: str):
        """Remove item."""
        if iid in self._items:
            del self._items[iid]
        if iid in self._children:
            self._children.remove(iid)

    def set_identify_row_result(self, result: str):
        """Configura resultado de identify_row."""
        self._identify_row_result = result

    def heading(self, column: str, **kwargs) -> None:
        """Configura heading de coluna."""
        self._headings[column] = kwargs

    def column(self, column: str, **kwargs) -> None:
        """Configura coluna."""
        self._column_config[column] = kwargs

    def configure(self, **kwargs) -> None:
        """Configura treeview."""
        if "yscrollcommand" in kwargs:
            self._yscrollcommand = kwargs["yscrollcommand"]

    def pack(self, **kwargs) -> None:
        """Pack widget."""
        self._packed = True

    def clear(self) -> None:
        """Limpa todos os itens (compatível com CTkTableView)."""
        self._items.clear()
        self._children.clear()
        self._selection.clear()

    def get_selected_iid(self) -> str | None:
        """Retorna iid do item selecionado (compatível com CTkTableView)."""
        if self._selection:
            return self._selection[0]
        return None

    def bind(self, event: str, callback: Any) -> None:
        """Bind evento."""
        pass

    def unbind(self, event: str) -> None:
        """Unbind evento."""
        pass

    def yview(self, *args) -> None:
        """Yview (no-op)."""
        pass


class FakeTextWidget:
    """Fake para tk.Text/ScrolledText sem UI real."""

    def __init__(self, *args, **kwargs):
        self._tags = {}
        self._binds = {}
        self._selection = ""
        self._clipboard = ""
        self._note_meta = {}

    def index(self, location: str) -> str:
        """Retorna índice."""
        if location.startswith("@"):
            return "1.0"
        return location

    def tag_names(self, index: str | None = None) -> tuple:
        """Retorna tags no índice."""
        if index and index in self._tags:
            return self._tags[index]
        return ()

    def clipboard_clear(self):
        """Limpa clipboard."""
        self._clipboard = ""

    def clipboard_append(self, text: str):
        """Adiciona ao clipboard."""
        self._clipboard += text

    def update(self):
        """Update (no-op)."""
        pass

    def bind(self, event: str, callback):
        """Registra bind."""
        self._binds[event] = callback

    def selection_get(self) -> str:
        """Retorna seleção."""
        if not self._selection:
            raise tk.TclError("SELECTION doesn't exist")
        return self._selection

    def set_tag_names(self, index: str, tags: tuple):
        """Configura tags para índice."""
        self._tags[index] = tags

    def set_selection(self, text: str):
        """Configura seleção."""
        self._selection = text
