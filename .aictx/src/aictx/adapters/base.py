"""Common adapter logic: load context.json (read-only), build payload from declaration, copy files, write context.json."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..document import Document


def load_adapter_spec(root: Path, adapter_name: str) -> Dict[str, Any]:
    """Load ai_context/adapters/<name>/context.json (read-only). Raises FileNotFoundError if missing. Requires output_dir."""
    spec_path = root / "adapters" / adapter_name / "context.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"Adapter spec not found: {spec_path}")
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    if not spec.get("output_dir"):
        raise ValueError(f"Adapter spec must contain output_dir: {spec_path}")
    return spec


def _index_by_path(index: Dict[str, "Document"], root: Path) -> Dict[Path, "Document"]:
    """Build path -> Document map (resolved paths) for lookup by source path."""
    by_path: Dict[Path, "Document"] = {}
    for doc in index.values():
        try:
            resolved = doc.path.resolve()
            by_path[resolved] = doc
        except Exception:
            pass
    return by_path


def build_payload(
    spec: Dict[str, Any],
    root: Path,
    index: Dict[str, "Document"],
    adapter_name: str,
) -> Dict[str, Any]:
    """
    Build payload from adapter declaration only. Documents list comes from spec["documents"].
    Validates that every source exists (fail fast). Enriches from index when document is indexed.
    """
    from ..manifest import content_checksum

    output_dir = spec["output_dir"]
    declared = spec.get("documents") or []
    by_path = _index_by_path(index, root)
    documents = []
    for entry in declared:
        source = entry.get("source")
        if not source:
            raise ValueError(f"Adapter {adapter_name}: document entry missing 'source': {entry}")
        src_path = (root / source).resolve()
        if not src_path.is_file():
            raise FileNotFoundError(f"Adapter {adapter_name}: source not found: {source}")
        target = entry.get("target", source)
        doc_entry = {
            "id": entry.get("id", ""),
            "kind": entry.get("kind", ""),
            "source": source,
            "target": target,
        }
        # Enrich from index if present
        indexed = index.get(entry.get("id")) or by_path.get(src_path)
        if indexed:
            raw = indexed.path.read_text(encoding="utf-8")
            doc_entry["version"] = indexed.version
            doc_entry["status"] = getattr(indexed, "status", None)
            doc_entry["complexity"] = getattr(indexed, "complexity", None)
            doc_entry["checksum"] = content_checksum(raw)
            doc_entry["tags"] = getattr(indexed, "tags", None) or []
        else:
            doc_entry["version"] = entry.get("version", 1)
            doc_entry["status"] = None
            doc_entry["complexity"] = None
            doc_entry["checksum"] = None
            doc_entry["tags"] = entry.get("tags", [])
        documents.append(doc_entry)
    return {
        "output_dir": output_dir,
        "documents": documents,
    }


def _copy_documents(root: Path, output_dir: str, documents: list) -> None:
    """Copy each document from root/source to output_dir/target. Sources are already validated by build_payload."""
    out_path = Path(root) / output_dir if not output_dir.startswith("/") else Path(output_dir)
    for doc in documents:
        src = root / doc["source"]
        dst = out_path / doc["target"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def run_export(root: Path, aictx_dir: Path, index: Dict[str, Any], adapter_name: str) -> None:
    """
    Execute export from declaration: read adapters/<name>/context.json, build payload from its documents list,
    validate sources, enrich from index, copy declared set only, write output_dir/context.json (output_dir + documents).
    """
    spec = load_adapter_spec(root, adapter_name)
    payload = build_payload(spec, root, index, adapter_name)
    output_dir = payload["output_dir"]
    out_path = Path(root) / output_dir if not output_dir.startswith("/") else Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    _copy_documents(root, output_dir, payload["documents"])
    context_out = out_path / "context.json"
    with open(context_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "output_dir": output_dir,
                "documents": payload["documents"],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
