"""Isolated temporary workspace for scan materialization."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

DEFAULT_MAX_BYTES = 512 * 1024 * 1024  # 512 MiB
DEFAULT_MAX_FILES = 50_000
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
        ".idea",
    }
)


class WorkspaceLimitError(Exception):
    """Raised when materialization exceeds configured workspace limits."""


@dataclass
class MaterializedWorkspace:
    """Temporary directory holding materialized scan content."""

    path: Path
    scan_id: UUID = field(default_factory=uuid4)
    digest: str | None = None
    max_bytes: int = DEFAULT_MAX_BYTES
    max_files: int = DEFAULT_MAX_FILES
    _bytes_used: int = field(default=0, repr=False)
    _files_used: int = field(default=0, repr=False)
    _temp_dir: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)
    _cleaned: bool = field(default=False, repr=False)

    @classmethod
    def create(
        cls,
        *,
        scan_id: UUID | None = None,
        root: str | Path | None = None,
        prefix: str = "gie-scan-",
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_files: int = DEFAULT_MAX_FILES,
    ) -> MaterializedWorkspace:
        if root is not None:
            path = Path(root)
            path.mkdir(parents=True, exist_ok=True)
            return cls(
                path=path,
                scan_id=scan_id or uuid4(),
                max_bytes=max_bytes,
                max_files=max_files,
            )

        temp = tempfile.TemporaryDirectory(prefix=prefix)
        return cls(
            path=Path(temp.name),
            scan_id=scan_id or uuid4(),
            max_bytes=max_bytes,
            max_files=max_files,
            _temp_dir=temp,
        )

    def track_file(self, size: int) -> None:
        self._files_used += 1
        self._bytes_used += size
        if self._files_used > self.max_files:
            raise WorkspaceLimitError(
                f"Workspace file limit exceeded ({self.max_files} files)"
            )
        if self._bytes_used > self.max_bytes:
            raise WorkspaceLimitError(
                f"Workspace size limit exceeded ({self.max_bytes} bytes)"
            )

    def compute_digest(self) -> str:
        hasher = hashlib.sha256()
        for file_path in sorted(self.path.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(self.path).as_posix().encode()
            hasher.update(rel)
            hasher.update(str(file_path.stat().st_size).encode())
            try:
                with file_path.open("rb") as handle:
                    while chunk := handle.read(65536):
                        hasher.update(chunk)
            except OSError:
                hasher.update(b"<unreadable>")
        self.digest = hasher.hexdigest()
        return self.digest

    async def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            return
        if self.path.exists() and os.environ.get("GIE_PRESERVE_WORKSPACE") != "1":
            shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self) -> MaterializedWorkspace:
        return self

    def __exit__(self, *_: object) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._cleaned = True
