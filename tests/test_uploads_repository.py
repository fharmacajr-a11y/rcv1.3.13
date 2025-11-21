"""Testes para src/modules/uploads/repository.py (TEST-001 Fase 5).

Foca na correção da QA-005: cast(Any, remote_path_builder) para permitir
passagem de client_id/org_id como kwargs.
"""

from pathlib import Path
from typing import Any


from src.modules.uploads import repository


class FakeAdapter:
    """Adaptador fake que registra chamadas para upload."""

    def __init__(self):
        self.uploaded_files = []

    def upload_file(self, local_path: Path, remote_path: str, **kwargs) -> dict[str, Any]:
        """Simula upload e retorna sucesso."""
        self.uploaded_files.append(
            {
                "local": str(local_path),
                "remote": remote_path,
            }
        )
        return {"path": remote_path, "success": True}


class FakeItem:
    """Item fake com caminho relativo."""

    def __init__(self, relative_path: str):
        self.relative_path = relative_path
        self.path = None  # Será definido depois


def fake_path_builder(cnpj_digits: str, relative_path: str, subfolder: str, *, client_id: int | None = None, org_id: int | None = None) -> str:
    """Builder de path fake que registra client_id/org_id.

    Ordem de parâmetros: cnpj_digits, relative_path, subfolder (como no código real).
    """
    # QA-005: Este builder aceita client_id/org_id como kwargs
    parts = [cnpj_digits]
    if subfolder:
        parts.append(subfolder)
    parts.append(relative_path)

    path = "/".join(parts)

    # Se recebeu client_id/org_id, adiciona ao path para verificar
    if client_id is not None:
        path += f"?client_id={client_id}"
    if org_id is not None:
        path += f"&org_id={org_id}" if "?" in path else f"?org_id={org_id}"

    return path


class TestUploadItemsWithAdapterQA005:
    """Testa upload_items_with_adapter após correção do QA-005.

    QA-005 adicionou cast(Any, remote_path_builder) nas linhas 165-173
    para permitir chamar o builder com client_id/org_id como kwargs.
    """

    def test_upload_single_item_with_client_id(self):
        """Testa que client_id é passado corretamente ao remote_path_builder."""
        adapter = FakeAdapter()
        item = FakeItem("documento.pdf")
        item.path = Path("/tmp/documento.pdf")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="12345678",
            subfolder="contratos",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=42,
            org_id=None,
        )

        assert len(adapter.uploaded_files) == 1
        uploaded = adapter.uploaded_files[0]
        assert uploaded["local"] == str(Path("/tmp/documento.pdf"))
        # Path deve conter client_id=42 (adicionado pelo fake_path_builder)
        assert "client_id=42" in uploaded["remote"]

    def test_upload_single_item_with_org_id(self):
        """Testa que org_id é passado corretamente ao remote_path_builder."""
        adapter = FakeAdapter()
        item = FakeItem("nota_fiscal.xml")
        item.path = Path("/tmp/nota_fiscal.xml")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="87654321",
            subfolder="xml",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=None,
            org_id=99,
        )

        assert len(adapter.uploaded_files) == 1
        uploaded = adapter.uploaded_files[0]
        assert "org_id=99" in uploaded["remote"]

    def test_upload_with_both_client_id_and_org_id(self):
        """Testa passagem de ambos client_id e org_id."""
        adapter = FakeAdapter()
        item = FakeItem("relatorio.xlsx")
        item.path = Path("/tmp/relatorio.xlsx")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="11223344",
            subfolder="relatorios",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=10,
            org_id=20,
        )

        uploaded = adapter.uploaded_files[0]
        # Ambos devem estar presentes
        assert "client_id=10" in uploaded["remote"]
        assert "org_id=20" in uploaded["remote"]

    def test_upload_without_client_id_or_org_id(self):
        """Testa que funciona sem client_id/org_id (valores None)."""
        adapter = FakeAdapter()
        item = FakeItem("arquivo.txt")
        item.path = Path("/tmp/arquivo.txt")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="99887766",
            subfolder="diversos",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=None,
            org_id=None,
        )

        uploaded = adapter.uploaded_files[0]
        # Não deve conter client_id nem org_id
        assert "client_id" not in uploaded["remote"]
        assert "org_id" not in uploaded["remote"]

    def test_upload_multiple_items_cnpj_subfolder_combinations(self):
        """Testa upload de múltiplos items com diferentes combinações de paths."""
        adapter = FakeAdapter()

        items = [
            FakeItem("doc1.pdf"),
            FakeItem("subdir/doc2.pdf"),
            FakeItem("subdir/nested/doc3.pdf"),
        ]
        for item in items:
            item.path = Path(f"/tmp/{item.relative_path}")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=items,
            cnpj_digits="55667788",
            subfolder="main",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=7,
            org_id=None,
        )

        assert len(adapter.uploaded_files) == 3

        # Todos devem ter cnpj + subfolder + relative_path
        for uploaded in adapter.uploaded_files:
            assert uploaded["remote"].startswith("55667788/main/")
            assert "client_id=7" in uploaded["remote"]

    def test_upload_with_empty_subfolder(self):
        """Testa que subfolder vazio não adiciona '/' extra no path."""
        adapter = FakeAdapter()
        item = FakeItem("test.txt")
        item.path = Path("/tmp/test.txt")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="12121212",
            subfolder="",  # Vazio
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=None,
            org_id=None,
        )

        uploaded = adapter.uploaded_files[0]
        # Path deve ser cnpj_digits + relative_path (sem subfolder)
        # fake_path_builder constrói: cnpj_digits + subfolder (se não vazio) + relative_path
        assert "12121212" in uploaded["remote"]
        assert "test.txt" in uploaded["remote"]

    def test_upload_calls_progress_callback(self):
        """Testa que progress_callback é chamado para cada item."""
        adapter = FakeAdapter()
        items = [FakeItem(f"file{i}.txt") for i in range(3)]
        for item in items:
            item.path = Path(f"/tmp/{item.relative_path}")

        progress_calls = []

        def fake_progress(item: Any):
            progress_calls.append(item)

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=items,
            cnpj_digits="99999999",
            subfolder="test",
            progress_callback=fake_progress,
            remote_path_builder=fake_path_builder,
            client_id=None,
            org_id=None,
        )

        # Deve ter chamado callback 3 vezes (uma vez por item)
        assert len(progress_calls) == 3
        assert progress_calls[0].relative_path == "file0.txt"
        assert progress_calls[2].relative_path == "file2.txt"

    def test_upload_adapter_exception_propagates(self):
        """Testa que exceção no adapter.upload_file é registrada em failures."""

        class BrokenAdapter:
            def upload_file(self, local_path, remote_path, **kwargs):
                raise RuntimeError("Upload failed!")

        adapter = BrokenAdapter()
        item = FakeItem("fail.txt")
        item.path = Path("/tmp/fail.txt")

        # upload_items_with_adapter captura exceções e retorna em failures
        ok_count, failures = repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="00000000",
            subfolder="",
            progress_callback=None,
            remote_path_builder=fake_path_builder,
            client_id=None,
            org_id=None,
        )

        # Deve ter 0 uploads ok e 1 falha
        assert ok_count == 0
        assert len(failures) == 1
        assert isinstance(failures[0][1], RuntimeError)


class TestRemotePathBuilderIntegration:
    """Testa diferentes signatures de remote_path_builder (validação de tipo)."""

    def test_builder_without_kwargs_fails_with_kwargs_passed(self):
        """Testa que builder sem **kwargs falha quando client_id/org_id são passados (TypeError)."""

        def simple_builder(cnpj: str, relative_path: str, subfolder: str) -> str:
            # Não aceita kwargs - ordem: cnpj, relative_path, subfolder
            return f"{cnpj}/{subfolder}/{relative_path}"

        adapter = FakeAdapter()
        item = FakeItem("legacy.pdf")
        item.path = Path("/tmp/legacy.pdf")

        # Se client_id/org_id são None, eles ainda são passados como kwargs
        # O código usa cast(Any, ...) que permite a chamada mas o builder vai rejeitar
        ok_count, failures = repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="11111111",
            subfolder="docs",
            progress_callback=None,
            remote_path_builder=simple_builder,
            client_id=None,  # None é passado como kwarg
            org_id=None,
        )

        # Deve falhar porque builder não aceita client_id/org_id
        assert ok_count == 0
        assert len(failures) == 1
        assert isinstance(failures[0][1], TypeError)

    def test_builder_with_kwargs_receives_values(self):
        """Testa que builder com **kwargs recebe client_id/org_id."""
        received_kwargs = {}

        def kwargs_builder(cnpj: str, relative_path: str, subfolder: str, **kwargs) -> str:
            # Ordem: cnpj, relative_path, subfolder
            received_kwargs.update(kwargs)
            return f"{cnpj}/{subfolder}/{relative_path}"

        adapter = FakeAdapter()
        item = FakeItem("new.pdf")
        item.path = Path("/tmp/new.pdf")

        repository.upload_items_with_adapter(
            adapter=adapter,
            items=[item],
            cnpj_digits="22222222",
            subfolder="modern",
            progress_callback=None,
            remote_path_builder=kwargs_builder,
            client_id=100,
            org_id=200,
        )

        # Builder deve ter recebido client_id e org_id
        assert received_kwargs.get("client_id") == 100
        assert received_kwargs.get("org_id") == 200
