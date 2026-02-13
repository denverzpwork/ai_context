"""Document model: frontmatter parsing and schemas by kind."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .config import COMPLEXITY_VALUES, STATUS_VALUES

FRONTMATTER_DELIM = "---"


@dataclass
class Document:
    """Parsed document with normalized metadata."""

    path: Path
    id: str
    kind: str
    version: int
    status: Optional[str] = None
    complexity: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    references: List[str] = field(default_factory=list)
    owner: Optional[str] = None

    def to_metadata_dict(self, root: Path) -> Dict[str, Any]:
        """For manifest and adapter payload: id, kind, version, status, complexity, tags, path (relative)."""
        rel_path = self.path.relative_to(root) if root in self.path.parents or self.path == root else self.path
        return {
            "id": self.id,
            "kind": self.kind,
            "version": self.version,
            "status": self.status,
            "complexity": self.complexity,
            "tags": self.tags,
            "path": str(rel_path),
        }


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Extract YAML between first --- and second ---; return (frontmatter_dict, body).
    Raises ValueError if delimiters invalid or YAML invalid.
    """
    content = content.strip()
    if not content.startswith(FRONTMATTER_DELIM):
        raise ValueError("Missing opening frontmatter delimiter ---")
    rest = content[len(FRONTMATTER_DELIM) :].lstrip("\r\n")
    idx = rest.find("\n" + FRONTMATTER_DELIM)
    if idx == -1:
        idx = rest.find("\r\n" + FRONTMATTER_DELIM)
    if idx == -1:
        raise ValueError("Missing closing frontmatter delimiter ---")
    fm_str = rest[:idx].strip()
    body = rest[idx + 1 :].split(FRONTMATTER_DELIM, 1)[-1].lstrip("\r\n")
    try:
        fm = yaml.safe_load(fm_str)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}") from e
    if fm is None:
        fm = {}
    if not isinstance(fm, dict):
        raise ValueError("Frontmatter must be a YAML mapping")
    return fm, body


def normalize_tags(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def normalize_version(v: Any) -> int:
    if v is None:
        return 1
    try:
        return int(v)
    except (TypeError, ValueError):
        return 1


# Required/optional by kind (SPEC)
SPEC_REQUIRED = {"id", "kind", "status", "complexity"}
SPEC_OPTIONAL = {"version", "tags", "owner", "references"}
RULE_REQUIRED = {"id", "kind", "version"}
RULE_OPTIONAL = {"tags", "references"}
OTHER_REQUIRED = {"id", "kind"}


def parse_document(file_path: Path, content: str, root: Path) -> Document:
    """
    Parse file content into Document. Applies defaults (tags=[], version=1).
    Does not validate schema (call validate_document for that).
    """
    fm, body = parse_frontmatter(content)
    doc_id = fm.get("id")
    kind = fm.get("kind")
    if not doc_id or not kind:
        raise ValueError("Frontmatter must contain id and kind")
    version = normalize_version(fm.get("version"))
    tags = normalize_tags(fm.get("tags"))
    status = fm.get("status")
    complexity = fm.get("complexity")
    references = normalize_tags(fm.get("references"))
    owner = fm.get("owner")
    return Document(
        path=file_path,
        id=str(doc_id).strip(),
        kind=str(kind).strip(),
        version=version,
        status=str(status).strip() if status is not None else None,
        complexity=str(complexity).strip() if complexity is not None else None,
        tags=tags,
        raw_frontmatter=fm,
        body=body,
        references=references,
        owner=str(owner).strip() if owner is not None else None,
    )


class ValidationError(Exception):
    """Validation error with path and message."""

    def __init__(self, path: Path, message: str, line: Optional[int] = None):
        self.path = path
        self.message = message
        self.line = line
        super().__init__(f"{path}: {message}")


def validate_document_schema(doc: Document) -> None:
    """Check required fields and enums per kind. Raises ValidationError."""
    kind = doc.kind
    if kind == "spec":
        if not doc.id:
            raise ValidationError(doc.path, "spec requires field: id")
        if doc.status is None:
            raise ValidationError(doc.path, "spec requires field: status")
        if doc.complexity is None:
            raise ValidationError(doc.path, "spec requires field: complexity")
        if doc.status not in STATUS_VALUES:
            raise ValidationError(doc.path, f"status must be one of {sorted(STATUS_VALUES)}")
        if doc.complexity not in COMPLEXITY_VALUES:
            raise ValidationError(doc.path, f"complexity must be one of {sorted(COMPLEXITY_VALUES)}")
    elif kind == "rule":
        if not doc.id:
            raise ValidationError(doc.path, "rule requires field: id")
        # version is always set (default 1) in parse_document
    else:
        if not doc.id or not doc.kind:
            raise ValidationError(doc.path, "document must have id and kind")


def normalized_content_for_checksum(doc: Document, raw_content: str) -> bytes:
    """Deterministic representation for hashing: normalize line endings, then UTF-8 bytes."""
    normalized = raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized.encode("utf-8")
