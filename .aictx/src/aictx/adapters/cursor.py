"""Cursor adapter: read spec from ai_context/adapters/cursor/context.json (read-only), build payload with source/target, copy files to output_dir, write context.json."""

from pathlib import Path
from typing import Any, Dict

from .base import run_export


def export_cursor(root: Path, aictx_dir: Path, index: Dict[str, Any]) -> None:
    """Export to Cursor: same protocol as base (context.json, file copies, context.json in output_dir)."""
    run_export(root, aictx_dir, index, "cursor")
