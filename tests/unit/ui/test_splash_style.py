# -*- coding: utf-8 -*-
"""Testes de estilo do splash sem inicializar Tk/ttkbootstrap."""

from __future__ import annotations

from ttkbootstrap.constants import INFO

from src.ui.splash import get_splash_progressbar_bootstyle


def test_splash_progressbar_uses_info_style_constant() -> None:
    bootstyle = get_splash_progressbar_bootstyle()
    assert str(bootstyle) == str(INFO)
