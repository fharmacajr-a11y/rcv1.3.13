"""Testes para src/ui/custom_dialogs.py

Garante que TclError nas operações Tk não propagam para fora dos diálogos
e que OSError em resource_path também é silenciado corretamente.
"""

from __future__ import annotations

from tkinter import TclError
import unittest
from unittest.mock import MagicMock, patch


class TestApplyIcon(unittest.TestCase):
    """_apply_icon deve silenciar TclError e OSError sem propagar."""

    def _make_window(self) -> MagicMock:
        w = MagicMock(spec=["iconbitmap", "iconphoto"])
        return w

    def test_iconbitmap_tclerror_falls_back_to_iconphoto(self) -> None:
        """Se iconbitmap levanta TclError, tenta iconphoto com .png."""
        window = self._make_window()
        window.iconbitmap.side_effect = TclError("no bitmap")

        with (
            patch("src.ui.custom_dialogs.resource_path", side_effect=lambda n: f"/fake/{n}"),
            patch("os.path.exists", return_value=True),
            patch("tkinter.PhotoImage") as mock_photo,
        ):
            mock_img = MagicMock()
            mock_photo.return_value = mock_img
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)  # não deve propagar

        window.iconphoto.assert_called_once_with(True, mock_img)

    def test_iconphoto_tclerror_is_silenced(self) -> None:
        """TclError em iconphoto é logado e não propaga."""
        window = self._make_window()
        window.iconbitmap.side_effect = TclError("no bitmap")
        window.iconphoto.side_effect = TclError("no photo")

        with (
            patch("src.ui.custom_dialogs.resource_path", side_effect=lambda n: f"/fake/{n}"),
            patch("os.path.exists", return_value=True),
            patch("tkinter.PhotoImage"),
        ):
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)  # não deve propagar

    def test_resource_path_oserror_is_silenced(self) -> None:
        """OSError ao buscar ícone é silenciado."""
        window = self._make_window()

        with patch("src.ui.custom_dialogs.resource_path", side_effect=OSError("no file")):
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)  # não deve propagar

        window.iconbitmap.assert_not_called()

    def test_icon_file_not_found_returns_silently(self) -> None:
        """Se rc.ico não existe, retorna sem fazer nada."""
        window = self._make_window()

        with (
            patch("src.ui.custom_dialogs.resource_path", return_value="/fake/rc.ico"),
            patch("os.path.exists", return_value=False),
        ):
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)

        window.iconbitmap.assert_not_called()
        window.iconphoto.assert_not_called()

    def test_iconbitmap_succeeds_no_fallback(self) -> None:
        """Se iconbitmap tem sucesso, iconphoto não é chamado."""
        window = self._make_window()

        with (
            patch("src.ui.custom_dialogs.resource_path", return_value="/fake/rc.ico"),
            patch("os.path.exists", return_value=True),
        ):
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)

        window.iconbitmap.assert_called_once_with("/fake/rc.ico")
        window.iconphoto.assert_not_called()

    def test_tclerror_outer_wrapping_silenced(self) -> None:
        """TclError que escapa do bloco interno é capturado pelo outer except."""
        window = self._make_window()
        # resource_path(rc.ico) OK, exists OK, mas iconbitmap levanta TclError
        # e resource_path(rc.png) também levanta TclError
        call_count = {"n": 0}

        def _side_effect(name: str) -> str:
            call_count["n"] += 1
            if name == "rc.png":
                raise TclError("rc.png tclerror")
            return f"/fake/{name}"

        window.iconbitmap.side_effect = TclError("no bitmap")

        with (
            patch("src.ui.custom_dialogs.resource_path", side_effect=_side_effect),
            patch("os.path.exists", return_value=True),
        ):
            from src.ui.custom_dialogs import _apply_icon

            _apply_icon(window)  # não deve propagar


class TestNoExceptExceptionRemaining(unittest.TestCase):
    """Garante que não há mais # noqa: BLE001 no arquivo custom_dialogs.py."""

    def test_no_noqa_ble001(self) -> None:
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "src" / "ui" / "custom_dialogs.py"
        text = src.read_text(encoding="utf-8")
        count = text.count("noqa: BLE001")
        self.assertEqual(
            count,
            0,
            f"Ainda há {count} ocorrência(s) de '# noqa: BLE001' em custom_dialogs.py",
        )

    def test_no_bare_except_exception(self) -> None:
        """Não deve haver `except Exception:` sem tipo específico no arquivo."""
        import pathlib
        import re

        src = pathlib.Path(__file__).parent.parent / "src" / "ui" / "custom_dialogs.py"
        text = src.read_text(encoding="utf-8")
        # Procura padrão: except Exception: ou except Exception as x:
        matches = re.findall(r"except Exception\b", text)
        self.assertEqual(
            len(matches),
            0,
            f"Ainda há {len(matches)} `except Exception` em custom_dialogs.py: {matches}",
        )


if __name__ == "__main__":
    unittest.main()
