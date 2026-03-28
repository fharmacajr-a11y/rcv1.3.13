# -*- coding: utf-8 -*-
"""Testes para zip_job_models.py — enums, dataclasses e máquina de estados."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.modules.uploads.zip_job_models import (
    ZipJob,
    ZipJobPhase,
    ZipJobProgress,
    VALID_TRANSITIONS,
    is_valid_transition,
    _parse_ts,
)


# ---------------------------------------------------------------------------
# ZipJobPhase
# ---------------------------------------------------------------------------


class TestZipJobPhase:
    def test_all_phases_defined(self):
        expected = {
            "queued",
            "scanning",
            "zipping",
            "uploading_artifact",
            "ready",
            "downloading_artifact",
            "completed",
            "cancelling",
            "cancelled",
            "failed",
        }
        assert {p.value for p in ZipJobPhase} == expected

    def test_terminal_phases(self):
        assert ZipJobPhase.COMPLETED.is_terminal
        assert ZipJobPhase.CANCELLED.is_terminal
        assert ZipJobPhase.FAILED.is_terminal
        assert not ZipJobPhase.QUEUED.is_terminal
        assert not ZipJobPhase.SCANNING.is_terminal
        assert not ZipJobPhase.ZIPPING.is_terminal
        assert not ZipJobPhase.READY.is_terminal

    def test_cancellable_phases(self):
        cancellable = {
            ZipJobPhase.QUEUED,
            ZipJobPhase.SCANNING,
            ZipJobPhase.ZIPPING,
            ZipJobPhase.UPLOADING_ARTIFACT,
            ZipJobPhase.READY,
        }
        for phase in ZipJobPhase:
            if phase in cancellable:
                assert phase.is_cancellable, f"{phase} should be cancellable"
            else:
                assert not phase.is_cancellable, f"{phase} should NOT be cancellable"

    def test_phase_is_str(self):
        assert ZipJobPhase.QUEUED == "queued"
        assert str(ZipJobPhase.SCANNING) == "ZipJobPhase.SCANNING"


# ---------------------------------------------------------------------------
# Transições de fase
# ---------------------------------------------------------------------------


class TestPhaseTransitions:
    def test_valid_happy_path(self):
        """Fluxo normal: queued → scanning → zipping → uploading → ready → downloading → completed."""
        path = [
            (ZipJobPhase.QUEUED, ZipJobPhase.SCANNING),
            (ZipJobPhase.SCANNING, ZipJobPhase.ZIPPING),
            (ZipJobPhase.ZIPPING, ZipJobPhase.UPLOADING_ARTIFACT),
            (ZipJobPhase.UPLOADING_ARTIFACT, ZipJobPhase.READY),
            (ZipJobPhase.READY, ZipJobPhase.DOWNLOADING_ARTIFACT),
            (ZipJobPhase.DOWNLOADING_ARTIFACT, ZipJobPhase.COMPLETED),
        ]
        for current, target in path:
            assert is_valid_transition(current, target), f"{current} → {target} deveria ser válido"

    def test_valid_cancellation_path(self):
        """Cancelamento: qualquer fase cancelável → cancelling → cancelled."""
        for phase in ZipJobPhase:
            if phase.is_cancellable:
                assert is_valid_transition(phase, ZipJobPhase.CANCELLING), f"{phase} → cancelling deveria ser válido"
        assert is_valid_transition(ZipJobPhase.CANCELLING, ZipJobPhase.CANCELLED)

    def test_valid_failure_from_non_terminal(self):
        """Qualquer fase não-terminal (exc. cancelling) pode ir para failed."""
        for phase in ZipJobPhase:
            if phase.is_terminal:
                continue
            if phase == ZipJobPhase.CANCELLING:
                assert not is_valid_transition(phase, ZipJobPhase.FAILED)
                continue
            if phase == ZipJobPhase.DOWNLOADING_ARTIFACT:
                assert is_valid_transition(phase, ZipJobPhase.FAILED)
                continue
            assert is_valid_transition(phase, ZipJobPhase.FAILED), f"{phase} → failed deveria ser válido"

    def test_invalid_backward_transitions(self):
        """Não se pode voltar de fases avançadas para anteriores."""
        assert not is_valid_transition(ZipJobPhase.ZIPPING, ZipJobPhase.SCANNING)
        assert not is_valid_transition(ZipJobPhase.READY, ZipJobPhase.QUEUED)
        assert not is_valid_transition(ZipJobPhase.COMPLETED, ZipJobPhase.QUEUED)

    def test_terminal_phases_have_no_outgoing(self):
        """Fases terminais não têm transições de saída."""
        for phase in ZipJobPhase:
            if phase.is_terminal:
                assert (
                    VALID_TRANSITIONS[phase] == frozenset()
                ), f"{phase} (terminal) não deveria ter transições de saída"

    def test_all_phases_covered_in_transitions(self):
        """Toda fase aparece nas chaves de VALID_TRANSITIONS."""
        for phase in ZipJobPhase:
            assert phase in VALID_TRANSITIONS


# ---------------------------------------------------------------------------
# ZipJobProgress
# ---------------------------------------------------------------------------


class TestZipJobProgress:
    def test_defaults(self):
        p = ZipJobProgress()
        assert p.total_files == 0
        assert p.file_progress == 0.0
        assert p.byte_progress == 0.0
        assert p.upload_progress == 0.0

    def test_file_progress(self):
        p = ZipJobProgress(total_files=10, processed_files=5)
        assert p.file_progress == pytest.approx(0.5)

    def test_byte_progress(self):
        p = ZipJobProgress(total_source_bytes=1000, processed_source_bytes=750)
        assert p.byte_progress == pytest.approx(0.75)

    def test_upload_progress(self):
        p = ZipJobProgress(artifact_bytes_total=2000, artifact_bytes_uploaded=2000)
        assert p.upload_progress == pytest.approx(1.0)

    def test_progress_capped_at_one(self):
        p = ZipJobProgress(total_files=5, processed_files=10)
        assert p.file_progress == 1.0

    def test_zero_total_returns_zero(self):
        p = ZipJobProgress(total_files=0, processed_files=5)
        assert p.file_progress == 0.0


# ---------------------------------------------------------------------------
# ZipJob.from_row
# ---------------------------------------------------------------------------


class TestZipJobFromRow:
    def _make_row(self, **overrides):
        base = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "org-123",
            "client_id": 42,
            "bucket": "rc-docs",
            "prefix": "org-123/42/SIFAP",
            "zip_name": "SIFAP.zip",
            "phase": "queued",
            "total_files": 0,
            "processed_files": 0,
            "total_source_bytes": 0,
            "processed_source_bytes": 0,
            "artifact_bytes_total": 0,
            "artifact_bytes_uploaded": 0,
            "message": "Aguardando início…",
            "artifact_storage_path": None,
            "error_detail": None,
            "cancel_requested": False,
            "created_at": "2026-03-26T10:00:00+00:00",
            "started_at": None,
            "completed_at": None,
            "updated_at": "2026-03-26T10:00:00+00:00",
        }
        base.update(overrides)
        return base

    def test_from_row_basic(self):
        row = self._make_row()
        job = ZipJob.from_row(row)
        assert job.id == "550e8400-e29b-41d4-a716-446655440000"
        assert job.phase == ZipJobPhase.QUEUED
        assert job.client_id == 42
        assert job.message == "Aguardando início…"
        assert not job.is_terminal
        assert job.is_cancellable
        assert job.progress.total_files == 0

    def test_from_row_with_progress(self):
        row = self._make_row(
            phase="zipping",
            total_files=15,
            processed_files=10,
            total_source_bytes=50000,
            processed_source_bytes=30000,
            artifact_bytes_total=12000,
            artifact_bytes_uploaded=8000,
        )
        job = ZipJob.from_row(row)
        assert job.phase == ZipJobPhase.ZIPPING
        assert job.progress.file_progress == pytest.approx(10 / 15)
        assert job.progress.upload_progress == pytest.approx(8000 / 12000)

    def test_from_row_completed(self):
        row = self._make_row(
            phase="completed",
            artifact_storage_path="exports/org-123/42/SIFAP.zip",
            completed_at="2026-03-26T10:05:00+00:00",
        )
        job = ZipJob.from_row(row)
        assert job.is_terminal
        assert not job.is_cancellable
        assert job.completed_at is not None

    def test_from_row_failed(self):
        row = self._make_row(
            phase="failed",
            error_detail="Timeout ao conectar ao Storage",
        )
        job = ZipJob.from_row(row)
        assert job.is_terminal
        assert job.error_detail == "Timeout ao conectar ao Storage"

    def test_from_row_cancel_requested(self):
        row = self._make_row(cancel_requested=True)
        job = ZipJob.from_row(row)
        assert job.cancel_requested


# ---------------------------------------------------------------------------
# _parse_ts
# ---------------------------------------------------------------------------


class TestParseTimestamp:
    def test_none(self):
        assert _parse_ts(None) is None

    def test_iso_with_z(self):
        dt = _parse_ts("2026-03-26T10:00:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.tzinfo is not None

    def test_iso_with_offset(self):
        dt = _parse_ts("2026-03-26T10:00:00+00:00")
        assert dt is not None

    def test_datetime_passthrough(self):
        now = datetime.now(tz=timezone.utc)
        assert _parse_ts(now) is now

    def test_invalid_returns_none(self):
        assert _parse_ts("not-a-date") is None
