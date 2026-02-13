"""Validate: required files, frontmatter, schema, references, enums. Fail fast."""

from pathlib import Path
from typing import Dict, List, Tuple

from .document import Document, ValidationError, validate_document_schema
from .indexer import (
    build_index,
    collect_task_dirs,
    required_files_for_complexity,
)
from .config import RELATION_TYPES


def ref_exists(ref_id: str, index: Dict[str, Document]) -> bool:
    """True if ref_id is an index key or a task id (ref_id-spec in index)."""
    if ref_id in index:
        return True
    if f"{ref_id}-spec" in index:
        return True
    return False


def validate_required_files(root: Path, index: Dict[str, Document]) -> List[str]:
    """Check required files per task complexity. Return list of errors."""
    errors = []
    tasks_dir = root / "tasks"
    if not tasks_dir.is_dir():
        return errors
    for task_dir in collect_task_dirs(root):
        spec_id = f"{task_dir.name}-spec"
        spec_doc = index.get(spec_id)
        if not spec_doc:
            continue
        complexity = getattr(spec_doc, "complexity", None) or "normal"
        required = required_files_for_complexity(complexity)
        for f in required:
            if not (task_dir / f).exists():
                errors.append(f"{task_dir / f}: required file missing (complexity={complexity})")
    return errors


def validate_references(index: Dict[str, Document]) -> List[str]:
    """Each reference must point to an existing document id."""
    errors = []
    for doc_id, doc in index.items():
        for ref_id in doc.references:
            if not ref_exists(ref_id, index):
                errors.append(f"{doc.path}: reference to unknown id {ref_id}")
    return errors


def run_validate(root: Path) -> Tuple[bool, List[str], Dict[str, Document]]:
    """
    Build index, validate schema and references. Return (ok, errors, index).
    """
    index, parse_errors = build_index(root)
    if parse_errors:
        return False, parse_errors, index
    errors = list(parse_errors)
    for doc_id, doc in index.items():
        try:
            validate_document_schema(doc)
        except ValidationError as e:
            errors.append(str(e))
    errors.extend(validate_required_files(root, index))
    errors.extend(validate_references(index))
    return len(errors) == 0, errors, index
