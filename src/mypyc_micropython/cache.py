"""
Compilation cache for incremental builds.

Tracks source file hashes and compilation metadata to skip unchanged files.
Cache is stored in .mpy_cache/ directory alongside the project.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# Default cache directory name
CACHE_DIR_NAME = ".mpy_cache"

# Cache format version - bump when format changes
CACHE_VERSION = 1


@dataclass
class FileCacheEntry:
    """Cache entry for a single compiled file."""

    source_path: str  # Absolute path to source file
    source_hash: str  # SHA256 of source content
    source_mtime: float  # Last modification time
    output_dir: str  # Where the C output was written
    module_name: str  # Generated module name
    compiler_version: str  # Compiler version used
    success: bool  # Whether compilation succeeded
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileCacheEntry:
        return cls(**data)


@dataclass
class CompilationCache:
    """Manages the compilation cache for incremental builds."""

    cache_dir: Path
    version: int = CACHE_VERSION
    entries: dict[str, FileCacheEntry] = field(default_factory=dict)

    @classmethod
    def load(cls, project_root: Path) -> CompilationCache:
        """Load cache from disk, or create empty cache if not found."""
        cache_dir = project_root / CACHE_DIR_NAME
        cache_file = cache_dir / "cache.json"

        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                if data.get("version") == CACHE_VERSION:
                    entries = {
                        k: FileCacheEntry.from_dict(v) for k, v in data.get("entries", {}).items()
                    }
                    return cls(cache_dir=cache_dir, entries=entries)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass  # Invalid cache, start fresh

        return cls(cache_dir=cache_dir)

    def save(self) -> None:
        """Persist cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "cache.json"

        data = {
            "version": self.version,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
        }
        cache_file.write_text(json.dumps(data, indent=2))

    def get_entry(self, source_path: Path) -> FileCacheEntry | None:
        """Get cache entry for a source file."""
        key = str(source_path.resolve())
        return self.entries.get(key)

    def set_entry(self, entry: FileCacheEntry) -> None:
        """Store cache entry for a source file."""
        key = entry.source_path
        self.entries[key] = entry

    def is_up_to_date(self, source_path: Path, output_dir: Path) -> bool:
        """Check if cached output is still valid for the source file.

        Returns True if:
        - Cache entry exists
        - Source hash matches
        - Output directory exists
        - Compilation was successful
        """
        entry = self.get_entry(source_path)
        if entry is None:
            return False

        # Check if source has changed
        current_hash = hash_file(source_path)
        if current_hash != entry.source_hash:
            return False

        # Check if output still exists
        output_path = Path(entry.output_dir)
        if not output_path.exists():
            return False

        # Check if output_dir matches expected
        if output_path.resolve() != output_dir.resolve():
            return False

        # Only consider successful compilations as cached
        return entry.success

    def invalidate(self, source_path: Path) -> None:
        """Remove cache entry for a source file."""
        key = str(source_path.resolve())
        self.entries.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.entries.clear()
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists():
            cache_file.unlink()


def hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of a file's contents."""
    hasher = hashlib.sha256()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def hash_source(source: str) -> str:
    """Compute SHA256 hash of source code string."""
    hasher = hashlib.sha256()
    hasher.update(source.encode("utf-8"))
    return hasher.hexdigest()


def get_compiler_version() -> str:
    """Get current compiler version for cache invalidation."""
    try:
        from mypyc_micropython import __version__

        return __version__
    except ImportError:
        return "dev"
