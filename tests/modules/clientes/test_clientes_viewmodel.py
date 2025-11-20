from __future__ import annotations

from typing import Dict

from src.modules.clientes.viewmodel import ClientesViewModel


def _make_vm(order_label: str = "Razão Social (A→Z)") -> ClientesViewModel:
    order_choices: Dict[str, tuple[str | None, bool]] = {
        "Razão Social (A→Z)": ("razao_social", False),
        "Nome (A→Z)": ("nome", False),
    }
    return ClientesViewModel(order_choices=order_choices, default_order_label=order_label)


def _sample_client(
    *,
    cid: int,
    razao: str,
    nome: str,
    status: str,
    obs: str = "",
) -> dict:
    observations = f"[{status}] {obs}".strip() if status else obs
    return {
        "id": cid,
        "razao_social": razao,
        "nome": nome,
        "cnpj": f"00.000.000/000{cid}-00",
        "whatsapp": f"+55 (11) 90000-00{cid:02d}",
        "observacoes": observations,
        "ultima_alteracao": "2024-05-01T12:00:00",
        "ultima_por": "ana@example.com",
    }


def test_extract_status_and_observacoes() -> None:
    vm = _make_vm()
    status, text = vm.extract_status_and_observacoes(" [APROVADO] Cliente bom ")
    assert status == "APROVADO"
    assert text == "Cliente bom"

    status, text = vm.extract_status_and_observacoes("Cliente sem status")
    assert status == ""
    assert text == "Cliente sem status"


def test_apply_status_to_observacoes() -> None:
    vm = _make_vm()
    assert vm.apply_status_to_observacoes("PENDENTE", "Analisar documentos") == "[PENDENTE] Analisar documentos"
    assert vm.apply_status_to_observacoes("", "Somente texto") == "Somente texto"


def test_filters_and_ordering() -> None:
    vm = _make_vm()
    clientes = [
        _sample_client(cid=1, razao="Farmácia Alfa", nome="Alfa Contato", status="ATIVO", obs="Cliente bom"),
        _sample_client(cid=2, razao="Farmácia Beta", nome="Beta Contato", status="PENDENTE", obs="Revisar documentos"),
        _sample_client(cid=3, razao="Clínica Gama", nome="Contato Gama", status="", obs="Sem prefixo"),
    ]

    vm.set_search_text("", rebuild=False)
    vm.set_status_filter(None, rebuild=False)
    vm.load_from_iterable(clientes)

    rows = vm.get_rows()
    assert [row.razao_social for row in rows] == ["Clínica Gama", "Farmácia Alfa", "Farmácia Beta"]
    assert vm.get_status_choices() == ["ATIVO", "PENDENTE"]

    vm.set_status_filter("ATIVO")
    ativos = vm.get_rows()
    assert len(ativos) == 1
    assert ativos[0].razao_social == "Farmácia Alfa"

    vm.set_status_filter(None)
    vm.set_search_text("beta")
    beta_rows = vm.get_rows()
    assert [row.razao_social for row in beta_rows] == ["Farmácia Beta"]

    vm.set_search_text("", rebuild=False)
    vm.set_order_label("Nome (A→Z)")
    ordered = vm.get_rows()
    assert [row.nome for row in ordered] == ["Alfa Contato", "Beta Contato", "Contato Gama"]
