"""Disk storage for revision file bytes.

Revision files must be retrievable later so a stored comparison can be
reprocessed (e.g. after a pipeline improvement). Bytes are written once at
revision registration and never modified or deleted (no overwrite behavior).
"""
import os
import re
from pathlib import Path

_STORAGE_ROOT = Path(os.getenv("REVISION_STORAGE_DIR", str(Path(__file__).parent.parent / "storage")))
_REVISIONS_DIR_NAME = "revisions"

_SAFE_EXT = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


def _revisions_dir() -> Path:
    root = Path(os.getenv("REVISION_STORAGE_DIR", str(_STORAGE_ROOT)))
    d = root / _REVISIONS_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_revision_file(revision_id: str, original_filename: str, data: bytes) -> str:
    """Write the revision's file bytes to disk and return the file_reference
    (a relative path under the storage root)."""
    ext = Path(original_filename or "").suffix
    ext = ext if _SAFE_EXT.match(ext) else ".bin"
    path = _revisions_dir() / f"{revision_id}{ext}"
    path.write_bytes(data)
    return f"{_REVISIONS_DIR_NAME}/{path.name}"


def load_revision_file(file_reference: str) -> bytes:
    path = Path(os.getenv("REVISION_STORAGE_DIR", str(_STORAGE_ROOT))) / file_reference
    if not path.is_file():
        raise FileNotFoundError(f"Revision file not found: {file_reference}")
    return path.read_bytes()


def delete_revision_file(file_reference: str) -> None:
    path = Path(os.getenv("REVISION_STORAGE_DIR", str(_STORAGE_ROOT))) / file_reference
    if path.is_file():
        path.unlink(missing_ok=True)

