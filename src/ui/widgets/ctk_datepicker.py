# -*- coding: utf-8 -*-
"""DatePicker CustomTkinter - Widget reutilizável para seleção de datas.

CODEC: Componente 100% CTk para substituir ttkbootstrap DateEntry.
"""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from typing import Callable, Optional

from src.ui.ctk_config import ctk  # SSoT


class CTkDatePicker(ctk.CTkFrame):
    """DatePicker CustomTkinter com Entry + botão calendário."""

    def __init__(
        self,
        master: tk.Widget,
        dateformat: str = "%Y-%m-%d",
        startdate: Optional[date] = None,
        command: Optional[Callable[[date], None]] = None,
        **kwargs: any,
    ) -> None:
        """Inicializa o DatePicker.

        Args:
            master: Widget pai
            dateformat: Formato da data (ex: "%Y-%m-%d", "%d/%m/%Y")
            startdate: Data inicial
            command: Callback chamado quando data é selecionada
            **kwargs: Argumentos adicionais para CTkFrame
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.dateformat = dateformat
        self._command = command
        self._selected_date = startdate or date.today()

        # Entry para exibir data
        self.entry_var = tk.StringVar(value=self._selected_date.strftime(dateformat))
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.entry_var,
            width=120,
        )
        self.entry.pack(side="left", padx=(0, 5))

        # Botão calendário
        self.calendar_button = ctk.CTkButton(
            self,
            text="📅",
            width=30,
            command=self._show_calendar,
        )
        self.calendar_button.pack(side="left")

        # Validação ao sair do Entry
        self.entry.bind("<FocusOut>", self._validate_entry)
        self.entry.bind("<Return>", self._validate_entry)

    def _validate_entry(self, event: Optional[tk.Event] = None) -> None:
        """Valida o texto do Entry e atualiza a data selecionada."""
        text = self.entry_var.get().strip()
        if not text:
            return

        try:
            parsed_date = datetime.strptime(text, self.dateformat).date()
            self._selected_date = parsed_date
            self.entry_var.set(parsed_date.strftime(self.dateformat))
            if self._command:
                self._command(parsed_date)
        except ValueError:
            # Restaurar data anterior se inválida
            self.entry_var.set(self._selected_date.strftime(self.dateformat))

    def _show_calendar(self) -> None:
        """Abre popup com calendário para seleção."""
        popup = ctk.CTkToplevel(self)
        popup.title("Selecionar Data")
        popup.resizable(False, False)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        # Centralizar popup
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.winfo_rooty() + self.winfo_height() + 5
        popup.geometry(f"+{x}+{y}")

        # Variáveis de navegação
        current_year = self._selected_date.year
        current_month = self._selected_date.month

        year_var = tk.IntVar(value=current_year)
        month_var = tk.IntVar(value=current_month)

        # Frame de navegação
        nav_frame = ctk.CTkFrame(popup)
        nav_frame.pack(padx=10, pady=(10, 5), fill="x")

        ctk.CTkButton(
            nav_frame,
            text="◀",
            width=30,
            command=lambda: self._prev_month(month_var, year_var, cal_frame, popup),
        ).pack(side="left", padx=2)

        month_label = ctk.CTkLabel(nav_frame, text="", width=120)
        month_label.pack(side="left", expand=True)

        ctk.CTkButton(
            nav_frame,
            text="▶",
            width=30,
            command=lambda: self._next_month(month_var, year_var, cal_frame, popup),
        ).pack(side="left", padx=2)

        # Frame do calendário
        cal_frame = ctk.CTkFrame(popup)
        cal_frame.pack(padx=10, pady=5)

        # Função para atualizar calendário
        def update_calendar() -> None:
            for widget in cal_frame.winfo_children():
                widget.destroy()

            y = year_var.get()
            m = month_var.get()
            month_label.configure(text=f"{calendar.month_name[m]} {y}")

            # Cabeçalho (dias da semana)
            days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            for col, day in enumerate(days):
                ctk.CTkLabel(
                    cal_frame,
                    text=day,
                    width=35,
                    font=("", 10, "bold"),
                ).grid(row=0, column=col, padx=1, pady=1)

            # Dias do mês
            cal = calendar.monthcalendar(y, m)
            for row_idx, week in enumerate(cal, start=1):
                for col_idx, day in enumerate(week):
                    if day == 0:
                        continue

                    day_date = date(y, m, day)
                    is_selected = day_date == self._selected_date

                    btn = ctk.CTkButton(
                        cal_frame,
                        text=str(day),
                        width=35,
                        height=25,
                        fg_color="green" if is_selected else ("gray75", "gray25"),
                        hover_color="darkgreen" if is_selected else ("gray60", "gray40"),
                        command=lambda d=day_date: self._select_date(d, popup),
                    )
                    btn.grid(row=row_idx, column=col_idx, padx=1, pady=1)

        # Botão hoje
        today_frame = ctk.CTkFrame(popup, fg_color="transparent")
        today_frame.pack(pady=(5, 10))

        ctk.CTkButton(
            today_frame,
            text="Hoje",
            width=80,
            command=lambda: self._select_date(date.today(), popup),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            today_frame,
            text="Cancelar",
            width=80,
            fg_color="gray",
            hover_color="darkgray",
            command=popup.destroy,
        ).pack(side="left", padx=5)

        # Mostrar calendário inicial
        update_calendar()

        # Armazenar função de update para navegação
        popup.update_calendar_func = update_calendar  # type: ignore[attr-defined]

    def _prev_month(
        self,
        month_var: tk.IntVar,
        year_var: tk.IntVar,
        cal_frame: ctk.CTkFrame,
        popup: ctk.CTkToplevel,
    ) -> None:
        """Navega para o mês anterior."""
        m = month_var.get()
        y = year_var.get()
        if m == 1:
            month_var.set(12)
            year_var.set(y - 1)
        else:
            month_var.set(m - 1)
        popup.update_calendar_func()  # type: ignore[attr-defined]

    def _next_month(
        self,
        month_var: tk.IntVar,
        year_var: tk.IntVar,
        cal_frame: ctk.CTkFrame,
        popup: ctk.CTkToplevel,
    ) -> None:
        """Navega para o próximo mês."""
        m = month_var.get()
        y = year_var.get()
        if m == 12:
            month_var.set(1)
            year_var.set(y + 1)
        else:
            month_var.set(m + 1)
        popup.update_calendar_func()  # type: ignore[attr-defined]

    def _select_date(self, selected: date, popup: ctk.CTkToplevel) -> None:
        """Seleciona uma data e fecha o popup."""
        self._selected_date = selected
        self.entry_var.set(selected.strftime(self.dateformat))
        if self._command:
            self._command(selected)
        popup.destroy()

    def get(self) -> str:
        """Retorna a data formatada como string."""
        return self.entry_var.get()

    def get_date(self) -> date:
        """Retorna a data como objeto date."""
        return self._selected_date

    def set(self, value: date | str) -> None:
        """Define a data.

        Args:
            value: date object ou string no formato do datepicker
        """
        if isinstance(value, date):
            self._selected_date = value
            self.entry_var.set(value.strftime(self.dateformat))
        elif isinstance(value, str):
            try:
                parsed = datetime.strptime(value, self.dateformat).date()
                self._selected_date = parsed
                self.entry_var.set(value)
            except ValueError:
                pass  # Ignora valores inválidos
