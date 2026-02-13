"""Discovery and indexing: walk ai_context, collect rules and tasks, build document index."""

from pathlib import Path
from typing import Dict, List, Optional

from .document import Document, parse_document
from .config import RELATION_TYPES

# Required artifacts by complexity (README)
TRIVIAL_FILES = {"spec.md", "implementation.md"}
NORMAL_FILES = {"spec.md", "plan.md", "implementation.md", "tests-review.md"}  # context optional, review short
CRITICAL_FILES = {"spec.md", "context.md", "plan.md", "implementation.md", "review.md", "tests-review.md"}


def collect_rules(root: Path) -> List[Path]:
    """Return list of .md paths under rules/."""
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        return []
    return sorted(rules_dir.glob("*.md"))


def collect_task_dirs(root: Path) -> List[Path]:
    """Return list of task directories under tasks/ (each must have spec.md)."""
    tasks_dir = root / "tasks"
    if not tasks_dir.is_dir():
        return []
    return [p for p in sorted(tasks_dir.iterdir()) if p.is_dir() and (p / "spec.md").exists()]


def required_files_for_complexity(complexity: Optional[str]) -> set:
    if complexity == "trivial":
        return TRIVIAL_FILES
    if complexity == "critical":
        return CRITICAL_FILES
    return NORMAL_FILES


def build_index(root: Path) -> tuple[Dict[str, Document], List[str]]:
    """
    Build id -> Document index from root (ai_context). Also return list of validation errors.
    Does not validate schema or references; only collects and parses.
    """
    index: Dict[str, Document] = {}
    errors: List[str] = []

    for path in collect_rules(root):
        try:
            content = path.read_text(encoding="utf-8")
            doc = parse_document(path, content, root)
            if doc.id in index:
                errors.append(f"{path}: duplicate id {doc.id}")
                continue
            index[doc.id] = doc
        except Exception as e:
            errors.append(f"{path}: {e}")

    for task_dir in collect_task_dirs(root):
        spec_path = task_dir / "spec.md"
        spec_id = f"{task_dir.name}-spec"
        try:
            content = spec_path.read_text(encoding="utf-8")
            doc = parse_document(spec_path, content, root)
            if spec_id in index:
                errors.append(f"{spec_path}: duplicate id {spec_id}")
                continue
            index[spec_id] = doc
        except Exception as e:
            errors.append(f"{spec_path}: {e}")

        # Index other known doc files in task dir (context, plan, implementation, review, tests-review)
        for name in ("context.md", "plan.md", "implementation.md", "review.md", "tests-review.md"):
            if name == "spec.md":
                continue
            path = task_dir / name
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8")
                sub_doc = parse_document(path, content, root)
                composite_id = f"{task_dir.name}-{name.removesuffix('.md')}"
                if composite_id in index:
                    errors.append(f"{path}: duplicate key {composite_id}")
                    continue
                index[composite_id] = sub_doc
            except Exception as e:
                errors.append(f"{path}: {e}")

    return index, errors


def collect_relations(index: Dict[str, Document]) -> List[Dict[str, str]]:
    """Build relations list from documents' references (default type: uses). Use index key as from."""
    relations = []
    for doc_id, doc in index.items():
        for ref_id in doc.references:
            # ref_id may be task id or rule id; keep as-is (manifest may reference by id)
            relations.append({"from": doc_id, "to": ref_id, "type": "uses"})
    return relations
