"""High level helper for uploading folders to Supabase Storage."""
from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Iterable, Optional

try:
    from utils.hash_utils import sha256_file as _sha256_file
except Exception:  # pragma: no cover
    def _sha256_file(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

from supabase import Client, create_client

DEFAULT_BUCKET = (os.getenv("SUPABASE_BUCKET") or "rc-docs").strip() or "rc-docs"


class SupabaseUploader:
    """Mirror of the UI upload logic for scripts or background tasks."""

    def __init__(self, url: str, anon_key: str, *, bucket: Optional[str] = None) -> None:
        self.url = url
        self.anon_key = anon_key
        self.bucket = bucket or DEFAULT_BUCKET
        self.sb: Client = create_client(url, anon_key)
        self._user_id: Optional[str] = None

    # ------------------------------------------------------------------ helpers
    def _current_user_id(self) -> Optional[str]:
        try:
            resp = self.sb.auth.get_user()
            user = getattr(resp, "user", None)
            if user and getattr(user, "id", None):
                return user.id
            if isinstance(resp, dict):
                return (resp.get("user") or {}).get("id")
        except Exception:
            return None
        return None

    def _resolve_org_id(self) -> str:
        uid = self._current_user_id()
        fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip()
        if not uid:
            return fallback
        try:
            resp = (
                self.sb.table("memberships")
                .select("org_id")
                .eq("user_id", uid)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None) or []
            if data:
                return data[0]["org_id"]
        except Exception:
            pass
        return fallback

    # ------------------------------------------------------------------ auth
    def sign_in(self, email: str, password: str) -> str:
        """Authenticate and remember the user id for later uploads."""
        res = self.sb.auth.sign_in_with_password({"email": email, "password": password})
        if not res or not res.user:
            raise RuntimeError("Falha ao autenticar no Supabase.")
        self._user_id = res.user.id
        return self._user_id

    # ------------------------------------------------------------------ storage
    @staticmethod
    def _sha256(path: Path) -> str:
        return _sha256_file(path)

    @staticmethod
    def _guess_content_type(path: Path) -> str:
        ctype, _ = mimetypes.guess_type(str(path))
        return ctype or "application/octet-stream"

    def _storage_upload(self, local_path: Path, storage_path: str) -> None:
        with local_path.open("rb") as handle:
            self.sb.storage.from_(self.bucket).upload(storage_path, handle.read())

    # ------------------------------------------------------------------ metadata
    def _insert_document(self, client_id: int, title: str, kind: str) -> str:
        payload = {"client_id": client_id, "title": title, "kind": kind}
        res = self.sb.table("documents").insert(payload).select("id").execute()
        if not res.data:
            raise RuntimeError("INSERT em 'documents' foi bloqueado por RLS ou falhou.")
        return res.data[0]["id"]

    def _insert_version_and_set_current(
        self,
        doc_id: str,
        storage_path: str,
        size_bytes: int,
        sha256_hex: str,
    ) -> str:
        version_payload = {
            "document_id": doc_id,
            "storage_path": storage_path,
            "size_bytes": size_bytes,
            "sha256": sha256_hex,
        }
        response = (
            self.sb.table("document_versions")
            .insert(version_payload)
            .select("id")
            .execute()
        )
        if not response.data:
            raise RuntimeError("INSERT em 'document_versions' foi bloqueado por RLS ou falhou.")
        version_id = response.data[0]["id"]
        self.sb.table("documents").update({"current_version": version_id}).eq("id", doc_id).execute()
        return version_id

    # ------------------------------------------------------------------ public API
    def upload_folder(
        self,
        folder: Path | str,
        client_id: int,
        subdir: str = "SIFAP",
        ignore_names: Iterable[str] = ("desktop.ini",),
    ) -> list[dict[str, str]]:
        """Upload every file inside a folder to Supabase Storage."""
        base = Path(folder).resolve()
        if not base.exists():
            raise FileNotFoundError(f"Folder not found: {base}")
        if not self._user_id:
            raise RuntimeError("Execute sign_in() antes de enviar arquivos.")

        org_id = self._resolve_org_id() or "unknown-org"
        results: list[dict[str, str]] = []

        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name.lower() in ignore_names:
                continue

            relative_path = path.relative_to(base).as_posix()
            storage_path = f"{org_id}/{client_id}/{subdir}/{relative_path}"

            self._storage_upload(path, storage_path)

            size = path.stat().st_size
            checksum = self._sha256(path)
            kind = (path.suffix[1:] or self._guess_content_type(path)).lower()

            document_id = self._insert_document(client_id=client_id, title=path.name, kind=kind)
            version_id = self._insert_version_and_set_current(document_id, storage_path, size, checksum)

            results.append(
                {
                    "relative_path": relative_path,
                    "storage_path": storage_path,
                    "document_id": document_id,
                    "version_id": version_id,
                }
            )

        return results


__all__ = ["SupabaseUploader"]
