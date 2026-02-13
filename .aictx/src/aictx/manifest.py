"""Build and write manifests.yaml; compute checksums; state for diff."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from .document import Document, normalized_content_for_checksum
from .indexer import collect_relations

GENERATOR = "aictx 1.0"


def file_checksum(path: Path) -> str:
    """SHA-256 of file content (normalized line endings)."""
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").strip()
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def content_checksum(raw_content: str) -> str:
    """SHA-256 of normalized content string."""
    normalized = raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def aggregated_checksum(index: Dict[str, Document], root: Path, read_mode: str = "active") -> str:
    """
    Deterministic: only documents eligible under read_mode (default active), sort by id, hash each.
    Rules are always included; task docs (spec, context, plan, ...) only when spec is active.
    """
    active_spec_ids = set()
    for doc_id, doc in index.items():
        if doc.kind == "spec" and doc.status == "active":
            # Task id from doc_id (e.g. TASK-123-spec -> TASK-123)
            task_id = doc_id.replace("-spec", "", 1) if doc_id.endswith("-spec") else doc_id
            active_spec_ids.add(task_id)
    eligible = []
    for doc_id, doc in index.items():
        if doc.kind == "rule":
            eligible.append((doc_id, doc))
            continue
        if doc.kind == "spec":
            if read_mode == "active" and doc.status != "active":
                continue
            eligible.append((doc_id, doc))
            continue
        # Task doc (context, plan, etc.): include if its task spec is active
        if doc.kind in ("context", "plan", "implementation", "review", "tests-review"):
            task_id = doc.path.parent.name if (doc.path.parent.name and doc.path.parent.name != "tasks") else None
            if task_id and task_id in active_spec_ids:
                eligible.append((doc_id, doc))
            elif read_mode != "active":
                eligible.append((doc_id, doc))
    eligible.sort(key=lambda x: x[0])
    h = hashlib.sha256()
    for doc_id, doc in eligible:
        raw = doc.path.read_text(encoding="utf-8")
        h.update(normalized_content_for_checksum(doc, raw))
    return "sha256:" + h.hexdigest()


def build_manifest(
    root: Path,
    index: Dict[str, Document],
    convention_version: str = "0.0.1",
) -> Dict[str, Any]:
    """Build manifest dict (documents, active_set, relations, root_checksum)."""
    relations = collect_relations(index)
    root_checksum = aggregated_checksum(index, root, "active")
    documents = []
    active_set = []
    for doc_id, doc in sorted(index.items()):
        raw = doc.path.read_text(encoding="utf-8")
        checksum = content_checksum(raw)
        # Status/complexity from doc (for spec they're set; for rule status may be missing)
        status = getattr(doc, "status", None)
        complexity = getattr(doc, "complexity", None)
        rel_path = doc.path.relative_to(root) if root in doc.path.parents or doc.path == root else doc.path
        entry = {
            "id": doc_id,
            "kind": doc.kind,
            "path": str(rel_path),
            "version": doc.version,
            "status": status,
            "complexity": complexity,
            "checksum": checksum,
            "tags": doc.tags or [],
        }
        documents.append(entry)
        if status == "active":
            active_set.append(doc_id)
    return {
        "convention_version": convention_version,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": GENERATOR,
        "root_checksum": root_checksum,
        "documents": documents,
        "active_set": active_set,
        "relations": relations,
    }


def write_manifest(root: Path, manifest: Dict[str, Any]) -> None:
    """Write manifest as YAML to root/manifests.yaml."""
    import yaml
    path = root / "manifests.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def save_state(aictx_dir: Path, manifest: Dict[str, Any]) -> None:
    """Save last built manifest to .aictx/state/ for diff."""
    import yaml
    state_dir = aictx_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "last_manifest.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_last_manifest(aictx_dir: Path) -> Dict[str, Any] | None:
    """Load last built manifest from .aictx/state/; None if missing."""
    import yaml
    path = aictx_dir / "state" / "last_manifest.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
