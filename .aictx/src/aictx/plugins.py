"""Lifecycle hooks: load plugins from .aictx/plugins/ and invoke before/after events."""

from pathlib import Path
from typing import Any, Callable, Dict, List

HOOKS = (
    "before_validate",
    "after_validate",
    "before_build_manifest",
    "after_build_manifest",
    "before_export",
    "after_export",
)

_registry: Dict[str, List[Callable[..., None]]] = {h: [] for h in HOOKS}


def register(hook: str, fn: Callable[..., None]) -> None:
    if hook not in HOOKS:
        raise ValueError(f"Unknown hook: {hook}")
    _registry[hook].append(fn)


def emit(hook: str, **context: Any) -> None:
    for fn in _registry[hook]:
        try:
            fn(**context)
        except Exception:
            pass  # fail soft for plugins


def load_plugins_from_dir(plugins_dir: Path) -> None:
    """Load Python modules from plugins_dir and register their hooks. Optional."""
    if not plugins_dir.is_dir():
        return
    import importlib.util
    import sys
    for path in plugins_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"aictx_plugin_{path.stem}", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                for h in HOOKS:
                    if hasattr(mod, h) and callable(getattr(mod, h)):
                        register(h, getattr(mod, h))
        except Exception:
            pass
