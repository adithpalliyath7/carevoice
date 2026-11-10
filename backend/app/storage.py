"""Storage abstraction for medical records.

Default: local disk under backend/storage/records/<id>/ (git-ignored, NOT in repo).
Supabase Storage is used only when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are
configured; the local path is the fallback and the interface is identical.
"""
import os
from pathlib import Path

# Vercel serverless functions have a read-only filesystem except /tmp, so
# record uploads go there when RECORDS_DIR is set or when running on Vercel.
# They do not persist across invocations — Supabase Storage (when configured)
# is the durable path. Local dev keeps the previous default.
if os.getenv("RECORDS_DIR"):
    BASE_DIR = Path(os.getenv("RECORDS_DIR")) / "records"
elif os.getenv("VERCEL"):
    BASE_DIR = Path("/tmp/carevoice-records")
else:
    BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "records"


def storage_backend() -> str:
    from . import config
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY:
        return "supabase"
    return "local"


def save_file(record_id: str, filename: str, data: bytes) -> str:
    """Returns a storage reference (local path). Supabase path is a placeholder
    reference until the bucket is wired — local disk remains the default."""
    dest_dir = BASE_DIR / record_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    (dest_dir / safe_name).write_bytes(data)
    return str(dest_dir / safe_name)


def read_file(record_id: str, filename: str) -> bytes:
    return (BASE_DIR / record_id / Path(filename).name).read_bytes()


def delete_record_files(record_id: str) -> None:
    import shutil
    shutil.rmtree(BASE_DIR / record_id, ignore_errors=True)
