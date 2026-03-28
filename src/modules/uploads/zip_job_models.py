# -*- coding: utf-8 -*-
"""Modelos de dados para jobs de exportação ZIP (server-side).

Define as fases (máquina de estados), métricas de progresso
e representação tipada de um job.

O processamento é feito inteiramente no servidor (Edge Function).
O desktop app apenas cria, acompanha e baixa o artefato final.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ZipJobPhase(str, enum.Enum):
    """Fases do ciclo de vida de um job de exportação ZIP.

    Máquina de estados (server-side):
        queued → scanning → zipping → uploading_artifact → ready
        ready → downloading_artifact → completed
        qualquer fase cancelável → cancelling → cancelled
        qualquer fase não-terminal → failed
    """

    QUEUED = "queued"
    SCANNING = "scanning"
    ZIPPING = "zipping"
    UPLOADING_ARTIFACT = "uploading_artifact"
    READY = "ready"
    DOWNLOADING_ARTIFACT = "downloading_artifact"
    COMPLETED = "completed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_PHASES

    @property
    def is_cancellable(self) -> bool:
        return self in _CANCELLABLE_PHASES


_TERMINAL_PHASES = frozenset(
    {
        ZipJobPhase.COMPLETED,
        ZipJobPhase.CANCELLED,
        ZipJobPhase.FAILED,
    }
)

_CANCELLABLE_PHASES = frozenset(
    {
        ZipJobPhase.QUEUED,
        ZipJobPhase.SCANNING,
        ZipJobPhase.ZIPPING,
        ZipJobPhase.UPLOADING_ARTIFACT,
        ZipJobPhase.READY,
    }
)

VALID_TRANSITIONS: dict[ZipJobPhase, frozenset[ZipJobPhase]] = {
    ZipJobPhase.QUEUED: frozenset(
        {
            ZipJobPhase.SCANNING,
            ZipJobPhase.CANCELLING,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.SCANNING: frozenset(
        {
            ZipJobPhase.ZIPPING,
            ZipJobPhase.CANCELLING,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.ZIPPING: frozenset(
        {
            ZipJobPhase.UPLOADING_ARTIFACT,
            ZipJobPhase.CANCELLING,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.UPLOADING_ARTIFACT: frozenset(
        {
            ZipJobPhase.READY,
            ZipJobPhase.CANCELLING,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.READY: frozenset(
        {
            ZipJobPhase.DOWNLOADING_ARTIFACT,
            ZipJobPhase.CANCELLING,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.DOWNLOADING_ARTIFACT: frozenset(
        {
            ZipJobPhase.COMPLETED,
            ZipJobPhase.FAILED,
        }
    ),
    ZipJobPhase.CANCELLING: frozenset(
        {
            ZipJobPhase.CANCELLED,
        }
    ),
    ZipJobPhase.COMPLETED: frozenset(),
    ZipJobPhase.CANCELLED: frozenset(),
    ZipJobPhase.FAILED: frozenset(),
}


def is_valid_transition(current: ZipJobPhase, target: ZipJobPhase) -> bool:
    """Verifica se a transição de fase é válida."""
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    return target in allowed


@dataclass(slots=True)
class ZipJobProgress:
    """Métricas de progresso de um job de exportação ZIP."""

    total_files: int = 0
    processed_files: int = 0
    total_source_bytes: int = 0
    processed_source_bytes: int = 0
    artifact_bytes_total: int = 0
    artifact_bytes_uploaded: int = 0

    @property
    def file_progress(self) -> float:
        """Progresso de arquivos processados (0.0–1.0)."""
        if self.total_files <= 0:
            return 0.0
        return min(self.processed_files / self.total_files, 1.0)

    @property
    def byte_progress(self) -> float:
        """Progresso de bytes processados (0.0–1.0)."""
        if self.total_source_bytes <= 0:
            return 0.0
        return min(self.processed_source_bytes / self.total_source_bytes, 1.0)

    @property
    def upload_progress(self) -> float:
        """Progresso de upload do artefato (0.0–1.0)."""
        if self.artifact_bytes_total <= 0:
            return 0.0
        return min(self.artifact_bytes_uploaded / self.artifact_bytes_total, 1.0)


@dataclass(slots=True)
class ZipJob:
    """Representação tipada de um job de exportação ZIP."""

    id: str
    org_id: str
    client_id: int
    bucket: str
    prefix: str
    zip_name: str
    phase: ZipJobPhase
    progress: ZipJobProgress
    message: str = ""
    artifact_storage_path: Optional[str] = None
    error_detail: Optional[str] = None
    cancel_requested: bool = False
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_terminal(self) -> bool:
        return self.phase.is_terminal

    @property
    def is_cancellable(self) -> bool:
        return self.phase.is_cancellable

    @classmethod
    def from_row(cls, row: dict) -> ZipJob:
        """Cria ZipJob a partir de uma row do Postgres."""
        return cls(
            id=row["id"],
            org_id=row["org_id"],
            client_id=row["client_id"],
            bucket=row["bucket"],
            prefix=row["prefix"],
            zip_name=row["zip_name"],
            phase=ZipJobPhase(row["phase"]),
            progress=ZipJobProgress(
                total_files=row.get("total_files", 0),
                processed_files=row.get("processed_files", 0),
                total_source_bytes=row.get("total_source_bytes", 0),
                processed_source_bytes=row.get("processed_source_bytes", 0),
                artifact_bytes_total=row.get("artifact_bytes_total", 0),
                artifact_bytes_uploaded=row.get("artifact_bytes_uploaded", 0),
            ),
            message=row.get("message", ""),
            artifact_storage_path=row.get("artifact_storage_path"),
            error_detail=row.get("error_detail"),
            cancel_requested=row.get("cancel_requested", False),
            created_at=_parse_ts(row.get("created_at")),
            started_at=_parse_ts(row.get("started_at")),
            completed_at=_parse_ts(row.get("completed_at")),
            updated_at=_parse_ts(row.get("updated_at")),
        )


def _parse_ts(value: Optional[str | datetime]) -> Optional[datetime]:
    """Parse de timestamp ISO do Postgres."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
