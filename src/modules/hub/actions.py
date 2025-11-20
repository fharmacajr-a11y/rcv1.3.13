"""Event handlers and UI actions for the Hub screen."""

from __future__ import annotations


import threading


from tkinter import messagebox


from src.core.logger import get_logger
from src.ui import custom_dialogs

from src.modules.notas import service as notes_service


from src.modules.hub.controller import (
    refresh_notes_async,
)


logger = get_logger("gui.hub_screen")


log = logger


def on_show(screen) -> None:
    """
    Chamado sempre que a tela do Hub fica visível (navegação de volta).

    Garante renderização imediata dos dados em cache e mantém live-sync ativo.
    """

    try:
        screen._start_live_sync()

    except Exception as e:
        log.warning("Erro ao iniciar live-sync no on_show: %s", e)

    try:
        is_empty = screen.notes_history.index("end-1c") == "1.0"

    except Exception:
        is_empty = True

    if is_empty and getattr(screen, "_notes_last_data", None):
        try:
            screen.render_notes(screen._notes_last_data, force=True)

        except Exception as e:
            log.warning("Erro ao renderizar notas no on_show: %s", e)

    try:
        screen._author_names_cache = {}

        screen._email_prefix_map = {}

        screen._names_cache_loaded = False

        screen._last_org_for_names = None

        screen._refresh_author_names_cache_async(force=True)

    except Exception as e:
        log.warning("Erro ao atualizar cache de nomes no on_show: %s", e)


def on_add_note_clicked(screen) -> None:
    """Handler do botão 'Adicionar' anotação."""

    text = screen.new_note.get("1.0", "end").strip()

    if not text:
        return

    if not screen._auth_ready():
        messagebox.showerror(
            "Não autenticado",
            "Você precisa estar autenticado para adicionar uma anotação.",
            parent=screen,
        )

        return

    app = screen._get_app()

    if not app or not screen._is_online(app):
        messagebox.showerror(
            "Sem conexão",
            "Não é possível adicionar anotações sem conexão com a internet.",
            parent=screen,
        )

        return

    org_id = screen._get_org_id_safe()

    user_email = screen._get_email_safe()

    if not org_id or not user_email:
        messagebox.showerror(
            "Erro",
            "Sessão incompleta (organização/usuário não identificados). Tente novamente após o login.",
            parent=screen,
        )

        return

    screen.btn_add_note.configure(state="disabled")

    def _work():
        ok = True

        error_msg = ""

        table_missing = False

        auth_error = False

        transient_error = False

        try:
            notes_service.add_note(org_id, user_email, text)

        except notes_service.NotesTransientError:
            transient_error = True
            error_msg = "Conexão instável, tentando novamente…"
            log.debug("HubScreen: Erro transitório ao adicionar nota")

        except notes_service.NotesTableMissingError as exc:
            table_missing = True
            error_msg = "Tabela de anotações não encontrada no Supabase."
            log.warning("HubScreen: %s", exc)

            def _mark_table_missing():
                screen._notes_table_missing = True

                screen._notes_table_missing_notified = True

            try:
                screen.after(0, _mark_table_missing)

            except Exception:
                pass

        except notes_service.NotesAuthError as exc:
            auth_error = True

            error_msg = str(exc)

            log.warning("HubScreen: %s", exc)

        except Exception as exc:
            ok = False

            error_msg = str(exc)

            log.warning("HubScreen: Falha ao adicionar nota: %s", exc)

        def _ui():
            try:
                screen.btn_add_note.configure(state="normal")

            except Exception:
                pass

            if transient_error and not table_missing and not auth_error:
                try:
                    messagebox.showwarning(
                        "Conexão Instável",
                        "A nota será salva assim que a conexão estabilizar.",
                        parent=screen,
                    )

                except Exception:
                    pass

            elif table_missing:
                try:
                    messagebox.showerror(
                        "Anotações Indisponíveis",
                        "Bloco de anotações indisponível:\n\n"
                        "A tabela 'rc_notes' não existe no Supabase.\n"
                        "Execute a migração em: migrations/rc_notes_migration.sql\n\n"
                        "Tentaremos novamente em 60 segundos.",
                        parent=screen,
                    )
                except Exception:
                    pass

            elif auth_error:
                try:
                    messagebox.showerror(
                        "Sem Permissão",
                        f"Sem permissão para anotar nesta organização.\nVerifique seu cadastro em 'profiles'.\n\nDetalhes: {error_msg}",
                        parent=screen,
                    )

                except Exception:
                    pass

            elif ok:
                try:
                    screen.new_note.delete("1.0", "end")

                except Exception:
                    pass

                refresh_notes_async(screen, force=True)

                screen._refresh_author_names_cache_async(force=False)

                try:
                    custom_dialogs.show_info(screen, "Sucesso", "Anotação adicionada com sucesso!")

                except Exception:
                    pass

            else:
                try:
                    messagebox.showerror(
                        "Erro",
                        f"Falha ao adicionar anotação: {error_msg}",
                        parent=screen,
                    )

                except Exception:
                    pass

        try:
            screen.after(0, _ui)

        except Exception:
            pass

    threading.Thread(target=_work, daemon=True).start()
