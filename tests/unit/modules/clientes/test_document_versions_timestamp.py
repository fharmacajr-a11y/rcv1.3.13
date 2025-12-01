from __future__ import annotations

from types import SimpleNamespace

from src.helpers.datetime_utils import now_iso_z
from src.modules.clientes.forms._upload import _build_document_version_payload


def test_document_version_payload_uses_valid_timestamp():
    ctx = SimpleNamespace(user_id="tester", created_at=now_iso_z())
    payload = _build_document_version_payload(
        document_id=1,
        storage_path="org/1/GERAL/sifap/1.pdf",
        size_bytes=123,
        sha256_hash="abc",
        ctx=ctx,
    )

    ts = payload["created_at"]
    assert ts.endswith("Z")
    assert "+00:00Z" not in ts
    assert payload["uploaded_by"] == "tester"
