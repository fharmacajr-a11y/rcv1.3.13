from __future__ import annotations

from src.helpers.datetime_utils import now_iso_z


def test_now_iso_z_format():
    ts = now_iso_z()
    assert ts.endswith("Z")
    assert "+00:00Z" not in ts
