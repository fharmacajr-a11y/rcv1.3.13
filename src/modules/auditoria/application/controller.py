"""Application/controller layer for the Auditoria UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .. import service as auditoria_service
from ..archives import AuditoriaArchivePlan
from ..service import (
    AuditoriaServiceError,
    AuditoriaUploadContext,
    AuditoriaUploadProgress,
    AuditoriaUploadResult,
)
from ..viewmodel import AuditoriaRow, AuditoriaViewModel
from src.modules.uploads import service as uploads_service


@dataclass(slots=True)
class AuditoriaApplicationConfig:
    """Configuration options for the Auditoria application layer."""

    viewmodel: AuditoriaViewModel | None = None


class AuditoriaApplication:
    """High-level application/controller facade for the Auditoria UI."""

    def __init__(self, config: AuditoriaApplicationConfig | None = None) -> None:
        cfg = config or AuditoriaApplicationConfig()
        self._service = auditoria_service
        self._vm = cfg.viewmodel or AuditoriaViewModel()

    # --- ViewModel helpers -------------------------------------------------
    @property
    def viewmodel(self) -> AuditoriaViewModel:
        return self._vm

    def refresh_clientes(self) -> None:
        self._vm.refresh_clientes(fetcher=self._service.fetch_clients)

    def refresh_auditorias(self) -> list[AuditoriaRow]:
        return self._vm.refresh_auditorias(fetcher=self._service.fetch_auditorias)

    # --- Connectivity helpers ---------------------------------------------
    def is_online(self) -> bool:
        return self._service.is_online()

    def ensure_storage_ready(self) -> None:
        self._service.ensure_storage_ready()

    def get_supabase_client(self) -> Any | None:
        return self._service.get_supabase_client()

    # --- Data operations ---------------------------------------------------
    def start_auditoria(self, cliente_id: int, *, status: str) -> dict[str, Any]:
        return self._service.start_auditoria(cliente_id, status=status)

    def update_auditoria_status(self, auditoria_id: str, new_status: str) -> dict[str, Any]:
        return self._service.update_auditoria_status(auditoria_id, new_status)

    def delete_auditorias(self, auditoria_ids: Iterable[str | int]) -> None:
        self._service.delete_auditorias(auditoria_ids)

    # --- Storage helpers ---------------------------------------------------
    def get_current_org_id(self, *, force_refresh: bool = False) -> str:
        return self._service.get_current_org_id(force_refresh=force_refresh)

    def get_storage_context(self, client_id: int, *, org_id: str | None = None):
        return self._service.get_storage_context(client_id, org_id=org_id)

    def ensure_auditoria_folder(self, client_id: int, *, org_id: str | None = None) -> None:
        self._service.ensure_auditoria_folder(client_id, org_id=org_id)

    def remove_storage_objects(self, bucket: str, paths: Sequence[str]) -> None:
        self._service.remove_storage_objects(bucket, paths)

    def get_clients_bucket(self) -> str:
        return self._service.get_clients_bucket()

    def delete_auditoria_folder(self, bucket: str, prefix: str) -> int:
        if not self._service.is_online():
            raise AuditoriaServiceError("Supabase client is not available.")
        keys = self._collect_storage_keys(bucket, prefix)
        if not keys:
            return 0
        batch_size = 1000
        for start in range(0, len(keys), batch_size):
            chunk = keys[start : start + batch_size]
            self._service.remove_storage_objects(bucket, chunk)
        return len(keys)

    def make_delete_folder_handler(self, allowed_prefix: str) -> Callable[[str, str], None]:
        allowed_norm = (allowed_prefix or "").strip("/")

        def _handler(bucket: str, prefix: str) -> None:
            target = (prefix or "").strip("/")
            if allowed_norm and not target.startswith(allowed_norm):
                raise AuditoriaServiceError("Operação fora do escopo da pasta de Auditoria.")
            self.delete_auditoria_folder(bucket, target)

        return _handler

    def _collect_storage_keys(self, bucket: str, prefix: str) -> list[str]:
        entries = uploads_service.list_storage_objects(bucket, prefix=prefix) or []
        collected: list[str] = []
        for entry in entries:
            full_path = (entry.get("full_path") or "").strip("/")
            if not full_path:
                continue
            if entry.get("is_folder"):
                collected.extend(self._collect_storage_keys(bucket, full_path))
            else:
                collected.append(full_path)
        return collected

    # --- Archive/upload pipeline ------------------------------------------
    def is_supported_archive(self, path: str | Path) -> bool:
        return self._service.is_supported_archive(path)

    def prepare_upload_context(self, client_id: int, *, org_id: str | None = None) -> AuditoriaUploadContext:
        return self._service.prepare_upload_context(client_id, org_id=org_id)

    def prepare_archive_plan(self, archive_path: str | Path) -> AuditoriaArchivePlan:
        return self._service.prepare_archive_plan(archive_path)

    def cleanup_archive_plan(self, plan: AuditoriaArchivePlan | None) -> None:
        self._service.cleanup_archive_plan(plan)

    def list_existing_names_for_context(self, context: AuditoriaUploadContext) -> set[str]:
        return self._service.list_existing_names_for_context(context)

    def detect_duplicate_file_names(self, plan: AuditoriaArchivePlan, existing_names: set[str]) -> set[str]:
        return self._service.detect_duplicate_file_names(plan, existing_names)

    def execute_archive_upload(
        self,
        plan: AuditoriaArchivePlan,
        context: AuditoriaUploadContext,
        *,
        strategy: str,
        existing_names: set[str],
        duplicates: set[str],
        cancel_check: Callable[[], bool] | None = None,
        progress_callback: Callable[[AuditoriaUploadProgress], None] | None = None,
    ) -> AuditoriaUploadResult:
        return self._service.execute_archive_upload(
            plan,
            context,
            strategy=strategy,
            existing_names=existing_names,
            duplicates=duplicates,
            cancel_check=cancel_check,
            progress_callback=progress_callback,
        )

    def list_existing_file_names(self, bucket: str, prefix: str) -> set[str]:
        return self._service.list_existing_file_names(bucket, prefix)

    # --- Convenience rollback ---------------------------------------------
    def rollback_uploaded_paths(self, context: AuditoriaUploadContext, uploaded_paths: Iterable[str]) -> None:
        self._service.rollback_uploaded_paths(context, uploaded_paths)


__all__ = ["AuditoriaApplication", "AuditoriaApplicationConfig"]
