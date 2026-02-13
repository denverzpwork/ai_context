"""Load .aictx/config.yaml and resolve ai_context root."""

import os
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONVENTION_VERSION = "0.0.1"
RELATION_TYPES = frozenset({"uses", "depends", "supersedes"})
STATUS_VALUES = frozenset({"active", "historical", "obsolete"})
COMPLEXITY_VALUES = frozenset({"trivial", "normal", "critical"})


def resolve_path(value: str, base: Path) -> Path:
    """Resolve path: if absolute use as-is, else relative to base."""
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (base / p).resolve()


def validate_context_root(path: Path) -> None:
    """Raise ValueError if path is not a valid context root (has .aictx or rules/)."""
    if not path.exists():
        raise ValueError(f"Context root does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Context root is not a directory: {path}")
    if not (path / ".aictx").is_dir() and not (path / "rules").is_dir():
        raise ValueError(
            f"Context root must contain .aictx or rules/: {path}"
        )


def validate_project_root(path: Path, check_writable: bool = True) -> None:
    """Raise ValueError if path is not a valid project root (exists, is dir; optionally writable)."""
    if not path.exists():
        raise ValueError(f"Project root does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Project root is not a directory: {path}")
    if check_writable and not os.access(path, os.W_OK):
        raise ValueError(f"Project root is not writable: {path}")


def find_aictx_dir(start: Path) -> Optional[Path]:
    """Walk upward from start until .aictx is found."""
    current = start.resolve()
    while True:
        if (current / ".aictx").is_dir():
            return current / ".aictx"
        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_ai_context_root(start: Path, explicit_root: Optional[Path] = None) -> Path:
    """
    Resolve ai_context root: explicit_root, or directory containing manifests.yaml
    or rules/ or tasks/, or cwd. Prefer walking up from start (cwd).
    """
    if explicit_root is not None:
        return Path(explicit_root).resolve()
    current = start.resolve()
    while True:
        if (current / "manifests.yaml").exists():
            return current
        if (current / "rules").is_dir() or (current / "tasks").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return start.resolve()
        current = parent


def load_config(aictx_dir: Path) -> dict:
    """Load .aictx/config.yaml; return dict with convention_version, adapters, project_root."""
    config_path = aictx_dir / "config.yaml"
    if not config_path.exists():
        return {
            "convention_version": DEFAULT_CONVENTION_VERSION,
            "adapters": ["cursor", "copilot"],
        }
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    project_root_raw = data.get("project_root")
    project_root = None
    if project_root_raw is not None and str(project_root_raw).strip():
        project_root = str(project_root_raw).strip()
    return {
        "convention_version": data.get("convention_version", DEFAULT_CONVENTION_VERSION),
        "adapters": data.get("adapters") or ["cursor", "copilot"],
        "project_root": project_root,
    }
