import pytest

from src.core.services import clientes_service
from src.modules.clientes.forms import client_form


def _patch_service_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "_pasta_do_cliente", lambda *a, **k: "pasta")
    monkeypatch.setattr(clientes_service, "_migrar_pasta_se_preciso", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "log_client_action", lambda *a, **k: None)


def test_salvar_cliente_ignora_notas_no_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_defaults(monkeypatch)

    captured: dict[str, object] = {}

    def fake_insert(numero, nome, razao_social, cnpj, obs, *, cnpj_norm=None):  # noqa: ANN001
        captured.update(
            numero=numero,
            nome=nome,
            razao_social=razao_social,
            cnpj=cnpj,
            obs=obs,
            cnpj_norm=cnpj_norm,
        )
        return 99

    monkeypatch.setattr(clientes_service, "insert_cliente", fake_insert)
    monkeypatch.setattr(clientes_service, "update_cliente", lambda *a, **k: None)

    saved_id, _ = clientes_service.salvar_cliente(
        None,
        {
            "Razão Social": "ACME",
            "CNPJ": "",
            "Nome": "",
            "WhatsApp": "",
            "Observações": "",
            "Observação interna 1": "nota1",
            "Observação interna 2": "nota2",
            "Observação interna 3": "nota3",
        },
    )

    assert "nota1" not in captured
    assert "nota2" not in captured
    assert "nota3" not in captured
    assert captured["obs"] == ""
    assert saved_id == 99


def test_salvar_cliente_ignora_notas_no_update(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_defaults(monkeypatch)

    captured: dict[str, object] = {}

    def fake_update(cliente_id, numero, nome, razao_social, cnpj, obs, *, cnpj_norm=None):  # noqa: ANN001
        captured.update(
            cliente_id=cliente_id,
            numero=numero,
            nome=nome,
            razao_social=razao_social,
            cnpj=cnpj,
            obs=obs,
            cnpj_norm=cnpj_norm,
        )
        return 1

    monkeypatch.setattr(clientes_service, "insert_cliente", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "update_cliente", fake_update)

    clientes_service.salvar_cliente(
        (10, "RZ", "", "", "", "", ""),
        {
            "Razão Social": "ACME",
            "CNPJ": "",
            "Nome": "",
            "WhatsApp": "",
            "Observações": "",
            "Observação interna 1": "interno A",
            "Observação interna 2": "interno B",
            "Observação interna 3": "interno C",
        },
    )

    assert captured["cliente_id"] == 10
    assert "nota1" not in captured
    assert "nota2" not in captured
    assert "nota3" not in captured


def test_form_cliente_cria_campos_internos(monkeypatch: pytest.MonkeyPatch) -> None:
    tk = pytest.importorskip("tkinter")
    created: list[object] = []
    real_toplevel = client_form.tk.Toplevel

    def fake_toplevel(parent):  # noqa: ANN001
        w = real_toplevel(parent)
        created.append(w)
        return w

    monkeypatch.setattr(client_form.tk, "Toplevel", fake_toplevel)
    monkeypatch.setattr(client_form, "apply_rc_icon", lambda *_args, **_kwargs: None)

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk indisponível no ambiente de teste")
    root.withdraw()
    try:
        client_form.form_cliente(root)
        assert created
        win = created[-1]
        vars_map = getattr(win, "_rc_internal_notes_vars", {})
        entries_map = getattr(win, "_rc_internal_notes_entries", {})
        assert set(vars_map.keys()) == {"endereco", "bairro", "cidade", "cep"}
        assert len(entries_map) == 4
    finally:
        for w in created:
            try:
                w.destroy()
            except Exception:
                pass
        try:
            root.destroy()
        except Exception:
            pass


def test_form_cliente_preenche_endereco_quando_disponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    tk = pytest.importorskip("tkinter")
    created: list[object] = []
    real_toplevel = client_form.tk.Toplevel

    def fake_toplevel(parent):  # noqa: ANN001
        w = real_toplevel(parent)
        created.append(w)
        return w

    monkeypatch.setattr(client_form.tk, "Toplevel", fake_toplevel)
    monkeypatch.setattr(client_form, "apply_rc_icon", lambda *_args, **_kwargs: None)

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk indisponível no ambiente de teste")
    root.withdraw()
    root._cliente_atual = type(
        "C",
        (),
        {"endereco": "Rua X", "bairro": "Centro", "cidade": "Sao Paulo", "cep": "01000-000"},
    )()

    try:
        client_form.form_cliente(root)
        win = created[-1]
        vars_map = getattr(win, "_rc_internal_notes_vars", {})
        assert vars_map["endereco"].get() == "Rua X"
        assert vars_map["bairro"].get() == "Centro"
        assert vars_map["cidade"].get() == "Sao Paulo"
        assert vars_map["cep"].get() == "01000-000"
    finally:
        for w in created:
            try:
                w.destroy()
            except Exception:
                pass
        try:
            root.destroy()
        except Exception:
            pass


def test_form_cliente_define_titulo_dinamico(monkeypatch: pytest.MonkeyPatch) -> None:
    tk = pytest.importorskip("tkinter")
    created: list[object] = []
    real_toplevel = client_form.tk.Toplevel

    def fake_toplevel(parent):  # noqa: ANN001
        w = real_toplevel(parent)
        created.append(w)
        return w

    monkeypatch.setattr(client_form.tk, "Toplevel", fake_toplevel)
    monkeypatch.setattr(client_form, "apply_rc_icon", lambda *_args, **_kwargs: None)

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk indisponível no ambiente de teste")
    root.withdraw()
    row = (21, "Cliente X", "12.345.678/0001-99", "", "", "", "")

    try:
        client_form.form_cliente(root, row)
        win = created[-1]
        assert "Editar Cliente" in win.title()
        assert "21" in win.title()
        assert "Cliente X" in win.title()
        assert "12.345.678/0001-99" in win.title()
    finally:
        for w in created:
            try:
                w.destroy()
            except Exception:
                pass
        try:
            root.destroy()
        except Exception:
            pass
