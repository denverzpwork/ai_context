"""Load .aictx/config.yaml and resolve ai_context root."""

from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONVENTION_VERSION = "0.0.1"
RELATION_TYPES = frozenset({"uses", "depends", "supersedes"})
STATUS_VALUES = frozenset({"active", "historical", "obsolete"})
COMPLEXITY_VALUES = frozenset({"trivial", "normal", "critical"})


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
    """Load .aictx/config.yaml; return dict with convention_version, adapters."""
    config_path = aictx_dir / "config.yaml"
    if not config_path.exists():
        return {
            "convention_version": DEFAULT_CONVENTION_VERSION,
            "adapters": ["cursor", "copilot"],
        }
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "convention_version": data.get("convention_version", DEFAULT_CONVENTION_VERSION),
        "adapters": data.get("adapters") or ["cursor", "copilot"],
    }
