# -*- coding: utf-8 -*-
"""Testes para zip_job_service.py — client-side: start, poll, download, cancel.

Todos os acessos ao Supabase e à Edge Function são mockados. Os testes validam:
- Start (POST à Edge Function)
- Polling até ready/terminal
- Signed URL para artefato
- Download com streaming
- Cancelamento cooperativo
- CRUD mantido (get, update, delete)
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.modules.uploads.zip_job_models import (
    ZipJob,
    ZipJobPhase,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(**overrides: Any) -> dict:
    """Cria uma row de banco simulada."""
    base = {
        "id": "job-001",
        "org_id": "org-1",
        "client_id": 42,
        "bucket": "rc-docs",
        "prefix": "org-1/42/SIFAP",
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


class FakeResponse:
    """Simula resp do exec_postgrest."""

    def __init__(self, rows: list[dict]):
        self.data = rows


class FakeHTTPResponse:
    """Simula resp do requests.Session."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict | None = None,
        content: bytes = b"",
        headers: dict | None = None,
    ):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._json or {}

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def iter_content(self, chunk_size: int = 8192):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        pass


@contextmanager
def _patch_service():
    """Retorna patches para _get_supabase e _exec."""
    with (
        patch("src.modules.uploads.zip_job_service._get_supabase") as mock_sb,
        patch("src.modules.uploads.zip_job_service._exec") as mock_exec,
    ):
        yield mock_sb, mock_exec


# ---------------------------------------------------------------------------
# Testes: get_zip_job
# ---------------------------------------------------------------------------


class TestGetZipJob:
    def test_get_existing(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import get_zip_job

            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="scanning")])

            job = get_zip_job("job-001")
            assert job.phase == ZipJobPhase.SCANNING

    def test_get_not_found(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import get_zip_job, ZipJobNotFoundError

            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([])

            with pytest.raises(ZipJobNotFoundError):
                get_zip_job("nonexistent")


# ---------------------------------------------------------------------------
# Testes: update_zip_job
# ---------------------------------------------------------------------------


class TestUpdateZipJob:
    def test_update_phase_and_message(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import update_zip_job

            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="scanning", message="Escaneando…")])

            job = update_zip_job(
                "job-001",
                phase=ZipJobPhase.SCANNING,
                message="Escaneando…",
            )
            assert job.phase == ZipJobPhase.SCANNING
            assert job.message == "Escaneando…"

    def test_update_progress_metrics(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import update_zip_job

            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(total_files=10, processed_files=5)])

            job = update_zip_job(
                "job-001",
                progress={"total_files": 10, "processed_files": 5},
            )
            assert job.progress.total_files == 10
            assert job.progress.processed_files == 5


# ---------------------------------------------------------------------------
# Testes: cancel_zip_job
# ---------------------------------------------------------------------------


class TestCancelZipJob:
    def test_cancel_cancellable_job(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import cancel_zip_job

            mock_sb.return_value = MagicMock()
            # cancel_zip_job faz 3 chamadas a _exec:
            #   1. get_zip_job (verificar fase atual)
            #   2. update (PATCH cancel_requested=True)
            #   3. get_zip_job dentro de update_zip_job (re-leitura após PATCH)
            mock_exec.side_effect = [
                FakeResponse([_make_row(phase="zipping")]),  # 1. get inicial
                FakeResponse([]),  # 2. update PATCH
                FakeResponse([_make_row(phase="zipping", cancel_requested=True)]),  # 3. re-leitura
            ]

            job = cancel_zip_job("job-001")
            assert job.cancel_requested

    def test_cancel_terminal_job_noop(self):
        with _patch_service() as (mock_sb, mock_exec):
            from src.modules.uploads.zip_job_service import cancel_zip_job

            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="completed")])

            job = cancel_zip_job("job-001")
            assert job.phase == ZipJobPhase.COMPLETED


# ---------------------------------------------------------------------------
# Testes: start_zip_export
# ---------------------------------------------------------------------------


class TestStartZipExport:
    def test_start_happy_path(self):
        """POST → 201 com job_id → get_zip_job retorna job."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            # get_zip_job chamado após start
            mock_exec.return_value = FakeResponse([_make_row(phase="queued")])

            with (
                patch("src.infra.net_session.make_session") as mock_sess,
                patch("src.modules.uploads.zip_job_service._get_zip_export_url", return_value="http://test/fn"),
                patch(
                    "src.modules.uploads.zip_job_service._get_auth_headers", return_value={"Authorization": "Bearer x"}
                ),
            ):
                fake_resp = FakeHTTPResponse(status_code=201, json_data={"job_id": "job-001", "phase": "queued"})
                mock_sess.return_value.post.return_value = fake_resp

                from src.modules.uploads.zip_job_service import start_zip_export

                job = start_zip_export(
                    org_id="org-1",
                    client_id=42,
                    bucket="rc-docs",
                    prefix="org-1/42/SIFAP",
                    zip_name="SIFAP.zip",
                )

                assert isinstance(job, ZipJob)
                assert job.id == "job-001"
                mock_sess.return_value.post.assert_called_once()

    def test_start_server_error_raises(self):
        """POST retorna 500 → ZipJobError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()

            with (
                patch("src.infra.net_session.make_session") as mock_sess,
                patch("src.modules.uploads.zip_job_service._get_zip_export_url", return_value="http://test/fn"),
                patch("src.modules.uploads.zip_job_service._get_auth_headers", return_value={}),
            ):
                fake_resp = FakeHTTPResponse(status_code=500, json_data={"error": "Internal Server Error"})
                mock_sess.return_value.post.return_value = fake_resp

                from src.modules.uploads.zip_job_service import start_zip_export, ZipJobError

                with pytest.raises(ZipJobError, match="HTTP 500"):
                    start_zip_export(
                        org_id="org-1",
                        client_id=42,
                        bucket="rc-docs",
                        prefix="x",
                        zip_name="y.zip",
                    )


# ---------------------------------------------------------------------------
# Testes: poll_zip_job
# ---------------------------------------------------------------------------


class TestPollZipJob:
    def test_poll_until_ready(self):
        """Polling detecta 'ready' e retorna imediatamente."""
        call_n = {"n": 0}

        def fake_exec(builder: Any) -> FakeResponse:
            call_n["n"] += 1
            if call_n["n"] <= 2:
                return FakeResponse([_make_row(phase="scanning")])
            elif call_n["n"] <= 4:
                return FakeResponse([_make_row(phase="zipping", total_files=10, processed_files=5)])
            return FakeResponse([_make_row(phase="ready", artifact_storage_path="exports/test.zip")])

        progress_phases: list[str] = []

        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.side_effect = fake_exec

            from src.modules.uploads.zip_job_service import poll_zip_job

            job = poll_zip_job(
                "job-001",
                interval_s=0.01,
                on_progress=lambda j: progress_phases.append(j.phase.value),
            )

        assert job.phase == ZipJobPhase.READY
        assert "scanning" in progress_phases
        assert "zipping" in progress_phases

    def test_poll_cancelled_raises(self):
        """Job marcado como cancelled → ZipJobCancelledError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="cancelled")])

            from src.modules.uploads.zip_job_service import poll_zip_job, ZipJobCancelledError

            with pytest.raises(ZipJobCancelledError):
                poll_zip_job("job-001", interval_s=0.01)

    def test_poll_failed_raises(self):
        """Job marcado como failed → ZipJobFailedError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="failed", error_detail="Timeout de rede")])

            from src.modules.uploads.zip_job_service import poll_zip_job, ZipJobFailedError

            with pytest.raises(ZipJobFailedError, match="Timeout"):
                poll_zip_job("job-001", interval_s=0.01)

    def test_poll_cancel_event_interrupts(self):
        """cancel_event.set() durante polling → ZipJobCancelledError."""
        cancel = threading.Event()

        def fake_exec(builder: Any) -> FakeResponse:
            cancel.set()  # Simula cancelamento na primeira chamada
            return FakeResponse([_make_row(phase="scanning")])

        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.side_effect = fake_exec

            from src.modules.uploads.zip_job_service import poll_zip_job, ZipJobCancelledError

            with pytest.raises(ZipJobCancelledError, match="cancelado pelo cliente"):
                poll_zip_job("job-001", interval_s=0.01, cancel_event=cancel)

    def test_poll_timeout(self):
        """Timeout expira → TimeoutError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="scanning")])

            from src.modules.uploads.zip_job_service import poll_zip_job

            with pytest.raises(TimeoutError, match="Timeout"):
                poll_zip_job("job-001", interval_s=0.01, timeout_s=0.05)


# ---------------------------------------------------------------------------
# Testes: get_artifact_url
# ---------------------------------------------------------------------------


class TestGetArtifactUrl:
    def test_happy_path(self):
        """GET à Edge Function com phase=ready → download_url retornada."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()

            with (
                patch("src.infra.net_session.make_session") as mock_sess,
                patch("src.modules.uploads.zip_job_service._get_zip_export_url", return_value="http://test/fn"),
                patch(
                    "src.modules.uploads.zip_job_service._get_auth_headers", return_value={"Authorization": "Bearer x"}
                ),
            ):
                fake_resp = FakeHTTPResponse(
                    status_code=200,
                    json_data={
                        "id": "job-001",
                        "phase": "ready",
                        "artifact_storage_path": "exports/org-1/42/SIFAP.zip",
                        "download_url": "https://cdn.example.com/signed/SIFAP.zip",
                    },
                )
                mock_sess.return_value.get.return_value = fake_resp

                from src.modules.uploads.zip_job_service import get_artifact_url

                url = get_artifact_url("job-001")

            assert url == "https://cdn.example.com/signed/SIFAP.zip"

    def test_no_download_url_raises(self):
        """GET retorna job sem download_url (ainda não ready) → ZipJobError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()

            with (
                patch("src.infra.net_session.make_session") as mock_sess,
                patch("src.modules.uploads.zip_job_service._get_zip_export_url", return_value="http://test/fn"),
                patch("src.modules.uploads.zip_job_service._get_auth_headers", return_value={}),
            ):
                fake_resp = FakeHTTPResponse(
                    status_code=200,
                    json_data={"id": "job-001", "phase": "zipping"},
                )
                mock_sess.return_value.get.return_value = fake_resp

                from src.modules.uploads.zip_job_service import get_artifact_url, ZipJobError

                with pytest.raises(ZipJobError, match="não possui download_url"):
                    get_artifact_url("job-001")

    def test_not_found_raises(self):
        """GET retorna 404 → ZipJobNotFoundError."""
        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()

            with (
                patch("src.infra.net_session.make_session") as mock_sess,
                patch("src.modules.uploads.zip_job_service._get_zip_export_url", return_value="http://test/fn"),
                patch("src.modules.uploads.zip_job_service._get_auth_headers", return_value={}),
            ):
                fake_resp = FakeHTTPResponse(status_code=404, json_data={"error": "not found"})
                mock_sess.return_value.get.return_value = fake_resp

                from src.modules.uploads.zip_job_service import get_artifact_url, ZipJobNotFoundError

                with pytest.raises(ZipJobNotFoundError):
                    get_artifact_url("job-001")


# ---------------------------------------------------------------------------
# Testes: download_artifact
# ---------------------------------------------------------------------------


class TestDownloadArtifact:
    def test_happy_path(self, tmp_path: Path):
        """Download streaming completo → arquivo salvo."""
        zip_content = b"PK" + b"\x00" * 100
        dest = tmp_path / "test.zip"

        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()

            # Calls: get_zip_job (mark downloading), update, update (completed)
            mock_exec.side_effect = [
                FakeResponse([_make_row(phase="ready")]),
                FakeResponse([_make_row(phase="downloading_artifact")]),
                FakeResponse([_make_row(phase="completed")]),
            ]

            with (
                patch(
                    "src.modules.uploads.zip_job_service.get_artifact_url",
                    return_value="https://cdn.example.com/test.zip",
                ),
                patch("src.infra.net_session.make_session") as mock_sess,
            ):
                fake_http = FakeHTTPResponse(
                    status_code=200,
                    content=zip_content,
                    headers={"Content-Length": str(len(zip_content))},
                )
                mock_sess.return_value.get.return_value = fake_http

                from src.modules.uploads.zip_job_service import download_artifact

                result = download_artifact("job-001", str(dest))

        assert result == dest
        assert dest.read_bytes() == zip_content

    def test_cancel_during_download(self, tmp_path: Path):
        """cancel_event durante download → remove .part e levanta erro."""
        dest = tmp_path / "test.zip"
        cancel = threading.Event()
        cancel.set()  # Já cancelado antes de iniciar

        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="ready")])

            with (
                patch(
                    "src.modules.uploads.zip_job_service.get_artifact_url",
                    return_value="https://cdn.example.com/test.zip",
                ),
                patch("src.infra.net_session.make_session") as mock_sess,
            ):
                fake_http = FakeHTTPResponse(
                    status_code=200,
                    content=b"PK" + b"\x00" * 50,
                    headers={"Content-Length": "52"},
                )
                mock_sess.return_value.get.return_value = fake_http

                from src.modules.uploads.zip_job_service import download_artifact

                with pytest.raises(Exception, match="[Cc]ancel"):
                    download_artifact("job-001", str(dest), cancel_event=cancel)

        assert not dest.exists()

    def test_progress_callback_called(self, tmp_path: Path):
        """progress_cb é chamado durante download."""
        zip_content = b"PK" + b"\x00" * 100
        dest = tmp_path / "test.zip"
        progress_calls: list[tuple[int, int]] = []

        with _patch_service() as (mock_sb, mock_exec):
            mock_sb.return_value = MagicMock()
            mock_exec.return_value = FakeResponse([_make_row(phase="ready")])

            with (
                patch(
                    "src.modules.uploads.zip_job_service.get_artifact_url",
                    return_value="https://cdn.example.com/test.zip",
                ),
                patch("src.infra.net_session.make_session") as mock_sess,
            ):
                fake_http = FakeHTTPResponse(
                    status_code=200,
                    content=zip_content,
                    headers={"Content-Length": str(len(zip_content))},
                )
                mock_sess.return_value.get.return_value = fake_http

                from src.modules.uploads.zip_job_service import download_artifact

                download_artifact(
                    "job-001",
                    str(dest),
                    progress_cb=lambda w, e: progress_calls.append((w, e)),
                )

        assert len(progress_calls) >= 1
        assert progress_calls[-1][0] == len(zip_content)
