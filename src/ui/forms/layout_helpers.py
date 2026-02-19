import ttkbootstrap as tb


def make_labeled_entry(parent, label: str, width: int = 40, show: str | None = None):
    """Cria um par Label+Entry."""
    frm = tb.Frame(parent)
    frm.pack(fill="x", pady=3)
    tb.Label(frm, text=label).pack(side="left")
    ent = tb.Entry(frm, width=width, show=show)
    ent.pack(side="left", padx=6, fill="x", expand=True)
    return ent
