"""View principal do módulo Auditoria."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from ttkbootstrap import ttk

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:
    def get_supabase():  # type: ignore[no-redef]
        return None

OFFLINE_MSG = "Recurso on-line. Verifique internet e credenciais do Supabase."


class AuditoriaFrame(ttk.Frame):
    """
    Tela de Auditoria:
      - Combobox para escolher Cliente
      - Botão 'Iniciar auditoria' (insere em public.auditorias)
      - Tabela com auditorias (cliente, status, criado/atualizado)

    Não altera nenhuma lógica global; funciona isolada.
    """

    def __init__(
        self,
        master: tk.Misc,
        go_back: Callable[[], None] | None = None,
        **kwargs
    ) -> None:
        """
        Inicializa a tela de Auditoria.

        Args:
            master: Widget pai (Tk ou Frame)
            go_back: Callback para voltar ao Hub (opcional)
            **kwargs: Argumentos adicionais para ttk.Frame
        """
        super().__init__(master, **kwargs)
        self._sb = get_supabase()
        self._go_back = go_back

        self._clientes: list[tuple[int, str]] = []  # [(id BIGINT, label)]
        self._clientes_map: dict[int, str] = {}  # {id: label}
        self._cliente_var = tk.StringVar()

        self._build_ui()
        self.after(100, self._lazy_load)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        """Constrói a interface da tela."""
        self.columnconfigure(0, weight=0)  # painel esquerdo
        self.columnconfigure(1, weight=1)  # centro (tabela)
        self.rowconfigure(1, weight=1)

        # Título
        title = ttk.Label(
            self,
            text="Auditoria",
            font=("-size", 16, "-weight", "bold")
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

        # Painel esquerdo (filtros/ações)
        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="nsw", padx=12, pady=8)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Cliente para auditoria:").grid(
            row=0, column=0, sticky="w"
        )
        self.cmb_cliente = ttk.Combobox(
            left,
            textvariable=self._cliente_var,
            state="readonly",
            width=40
        )
        self.cmb_cliente.grid(row=1, column=0, sticky="ew", pady=(2, 8))

        btns = ttk.Frame(left)
        btns.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        btns.columnconfigure((0, 1), weight=1)

        self.btn_iniciar = ttk.Button(
            btns,
            text="Iniciar auditoria",
            command=self._on_iniciar
        )
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_refresh = ttk.Button(
            btns,
            text="Atualizar lista",
            command=self._load_auditorias
        )
        self.btn_refresh.grid(row=0, column=1, sticky="ew")

        if self._go_back:
            ttk.Button(
                left,
                text="Voltar",
                command=self._go_back
            ).grid(row=3, column=0, sticky="ew")

        # Centro: tabela
        center = ttk.Frame(self)
        center.grid(row=1, column=1, sticky="nsew", padx=(8, 12), pady=8)
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)

        hdr = ttk.Frame(center)
        hdr.grid(row=0, column=0, sticky="ew")
        ttk.Label(hdr, text="Auditorias recentes").pack(side="left")

        self.tree = ttk.Treeview(
            center,
            columns=("cliente", "status", "created", "updated"),
            show="headings",
            height=16
        )
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("status", text="Status")
        self.tree.heading("created", text="Criado em")
        self.tree.heading("updated", text="Atualizado em")
        self.tree.column("cliente", width=320, anchor="w")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("created", width=140, anchor="center")
        self.tree.column("updated", width=140, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.lbl_offline = ttk.Label(center, text=OFFLINE_MSG, foreground="#666")
        self.lbl_offline.grid(row=2, column=0, sticky="w", pady=(6, 0))

    # ---------- Loaders ----------
    def _lazy_load(self) -> None:
        """Carrega dados após inicialização da UI."""
        if not self._sb:
            self._set_offline(True)
            return
        self._set_offline(False)
        self._load_clientes()
        self._load_auditorias()

    def _set_offline(self, is_offline: bool) -> None:
        """
        Configura estado offline/online da tela.

        Args:
            is_offline: True se offline, False se online
        """
        state = "disabled" if is_offline else "normal"
        self.cmb_cliente.configure(state="disabled" if is_offline else "readonly")
        self.btn_iniciar.configure(state=state)
        self.btn_refresh.configure(state=state)
        self.lbl_offline.configure(text=OFFLINE_MSG if is_offline else "")

    def _load_clientes(self) -> None:
        """Carrega lista de clientes do Supabase."""
        if not self._sb:
            return

        try:
            # Busca todos os campos; ordena por id
            res = (
                self._sb.table("clients")
                .select("*")
                .order("id")
                .execute()
            )
            data = getattr(res, "data", []) or []
            
            self._clientes, self._clientes_map = [], {}
            for row in data:
                cid = int(row.get("id"))
                nome = (
                    row.get("razao_social")
                    or row.get("legal_name")
                    or row.get("name")
                    or row.get("display_name")
                    or f"Cliente {cid}"
                )
                cnpj = row.get("cnpj") or row.get("tax_id") or ""
                label = f"{nome} — {cnpj}" if cnpj else nome
                
                self._clientes.append((cid, label))
                self._clientes_map[cid] = label
            
            self.cmb_cliente["values"] = [label for _id, label in self._clientes]
            if self._clientes:
                self.cmb_cliente.current(0)
        except Exception as e:
            messagebox.showwarning(
                "Clientes",
                f"Não foi possível carregar os clientes.\n{e}"
            )

    def _load_auditorias(self) -> None:
        """
        Carrega lista de auditorias do Supabase.

        Monta o nome do cliente via self._clientes_map, sem usar embed FK.
        """
        if not self._sb:
            return

        try:
            res = (
                self._sb.table("auditorias")
                .select("id, status, created_at, updated_at, cliente_id")
                .order("created_at", desc=True)
                .execute()
            )
            rows = getattr(res, "data", []) or []
            self.tree.delete(*self.tree.get_children())

            for r in rows:
                # Busca nome do cliente via mapa em memória
                cliente_id = r.get("cliente_id")
                if cliente_id is not None:
                    try:
                        cid = int(cliente_id)
                        cliente_nome = self._clientes_map.get(cid, f"#{cid}")
                    except (ValueError, TypeError):
                        cliente_nome = str(cliente_id)
                else:
                    cliente_nome = ""

                # Formata timestamps (remove T e microssegundos)
                created = (r.get("created_at") or "")[:19].replace("T", " ")
                updated = (r.get("updated_at") or "")[:19].replace("T", " ")

                self.tree.insert(
                    "",
                    "end",
                    iid=r["id"],
                    values=(cliente_nome, r.get("status", ""), created, updated)
                )
        except Exception as e:
            messagebox.showwarning(
                "Auditorias",
                f"Falha ao carregar auditorias.\n{e}"
            )

    # ---------- Actions ----------
    def _on_iniciar(self) -> None:
        """Handler do botão 'Iniciar auditoria'."""
        if not self._sb:
            return

        idx = self.cmb_cliente.current()
        if idx < 0 or idx >= len(self._clientes):
            messagebox.showinfo("Auditoria", "Selecione um cliente.")
            return

        cliente_id = int(self._clientes[idx][0])

        try:
            ins = (
                self._sb.table("auditorias")
                .insert({"cliente_id": cliente_id, "status": "em_andamento"})
                .execute()
            )
            if getattr(ins, "data", None):
                self._load_auditorias()
                messagebox.showinfo("Auditoria", "Auditoria iniciada com sucesso.")
        except Exception as e:
            messagebox.showerror(
                "Auditoria",
                f"Não foi possível iniciar a auditoria.\n{e}"
            )
