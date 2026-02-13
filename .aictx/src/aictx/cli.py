"""CLI: validate, build-manifest, list, diff, export."""

import json
import sys
from pathlib import Path

import click

from .config import find_ai_context_root, find_aictx_dir, load_config
from .indexer import build_index
from .validate import run_validate
from .manifest import (
    build_manifest,
    write_manifest,
    save_state,
    load_last_manifest,
)
from .plugins import emit, load_plugins_from_dir
from .document import Document


def get_roots(ctx: click.Context) -> tuple[Path, Path]:
    """Return (ai_context_root, aictx_dir)."""
    cwd = Path.cwd()
    aictx_dir = find_aictx_dir(cwd)
    if not aictx_dir:
        aictx_dir = cwd / ".aictx"
    root = find_ai_context_root(cwd, ctx.obj.get("root") if ctx.obj else None)
    return root, aictx_dir


@click.group()
@click.option("--root", type=click.Path(path_type=Path), default=None, help="ai_context root (default: auto-detect)")
@click.pass_context
def main(ctx: click.Context, root: Path | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["root"] = root


@main.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate convention: required files, frontmatter, schema, references."""
    root, aictx_dir = get_roots(ctx)
    config = load_config(aictx_dir)
    load_plugins_from_dir(aictx_dir / "plugins")
    emit("before_validate", root=root, config=config)
    ok, errors, index = run_validate(root)
    emit("after_validate", root=root, config=config, index=index, ok=ok)
    if errors:
        for e in errors:
            click.echo(e, err=True)
        sys.exit(1)
    click.echo(f"Validated {len(index)} document(s).")


@main.command("build-manifest")
@click.pass_context
def build_manifest_cmd(ctx: click.Context) -> None:
    """Build ai_context/manifests.yaml and save state for diff."""
    root, aictx_dir = get_roots(ctx)
    config = load_config(aictx_dir)
    load_plugins_from_dir(aictx_dir / "plugins")
    _, errors, index = run_validate(root)
    if errors:
        for e in errors:
            click.echo(e, err=True)
        sys.exit(1)
    emit("before_build_manifest", root=root, config=config, index=index)
    manifest = build_manifest(root, index, config.get("convention_version", "0.0.1"))
    write_manifest(root, manifest)
    save_state(aictx_dir, manifest)
    emit("after_build_manifest", root=root, config=config, manifest=manifest)
    click.echo(f"Built manifest: {len(manifest['documents'])} documents, active_set={len(manifest.get('active_set', []))}.")


@main.command()
@click.option("--status", default=None, help="Filter by status (e.g. active)")
@click.option("--kind", default=None, help="Filter by kind (e.g. rule, spec)")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.pass_context
def list_cmd(ctx: click.Context, status: str | None, kind: str | None, as_json: bool) -> None:
    """List documents; default table, --json for machine output."""
    root, _ = get_roots(ctx)
    index, parse_errors = build_index(root)
    if parse_errors:
        for e in parse_errors:
            click.echo(e, err=True)
        sys.exit(1)
    items = []
    for doc_id, doc in sorted(index.items()):
        if status and getattr(doc, "status", None) != status:
            continue
        if kind and doc.kind != kind:
            continue
        rel = doc.path.relative_to(root) if root in doc.path.parents or doc.path == root else doc.path
        items.append({
            "id": doc_id,
            "kind": doc.kind,
            "status": getattr(doc, "status", None),
            "path": str(rel),
            "complexity": getattr(doc, "complexity", None),
        })
    if as_json:
        click.echo(json.dumps(items, indent=2, ensure_ascii=False))
        return
    if not items:
        click.echo("No documents match.")
        return
    col = lambda k: max(len(str(row.get(k) or "")) for row in items) or 4
    w_id, w_kind, w_status, w_path = max(col("id"), 2), max(col("kind"), 4), max(col("status"), 6), max(col("path"), 4)
    click.echo(f"{'id':<{w_id}}  {'kind':<{w_kind}}  {'status':<{w_status}}  path")
    for row in items:
        click.echo(f"{str(row.get('id') or ''):<{w_id}}  {str(row.get('kind') or ''):<{w_kind}}  {str(row.get('status') or ''):<{w_status}}  {row.get('path') or ''}")


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.pass_context
def diff(ctx: click.Context, as_json: bool) -> None:
    """Show changes: current workspace vs last built manifest."""
    root, aictx_dir = get_roots(ctx)
    index, parse_errors = build_index(root)
    if parse_errors:
        for e in parse_errors:
            click.echo(e, err=True)
        sys.exit(1)
    last = load_last_manifest(aictx_dir)
    if not last:
        click.echo("No previous manifest in state. Run build-manifest first.")
        sys.exit(0)
    current_ids = set(index.keys())
    last_ids = {d["id"] for d in last.get("documents", [])}
    last_checksums = {d["id"]: d.get("checksum") for d in last.get("documents", [])}
    added = sorted(current_ids - last_ids)
    removed = sorted(last_ids - current_ids)
    changed = []
    for doc_id in sorted(current_ids & last_ids):
        doc = index.get(doc_id)
        if not doc:
            continue
        raw = doc.path.read_text(encoding="utf-8")
        from .manifest import content_checksum
        cs = content_checksum(raw)
        if last_checksums.get(doc_id) != cs:
            changed.append(doc_id)
    report = {"added": added, "removed": removed, "changed": changed}
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return
    if added:
        click.echo("Added: " + ", ".join(added))
    if removed:
        click.echo("Removed: " + ", ".join(removed))
    if changed:
        click.echo("Changed: " + ", ".join(changed))
    if not (added or removed or changed):
        click.echo("No changes.")


@main.command()
@click.argument("adapter", type=str)
@click.pass_context
def export(ctx: click.Context, adapter: str) -> None:
    """Export to adapter (e.g. cursor). Uses declaration in ai_context/adapters/<name>/context.json only."""
    root, aictx_dir = get_roots(ctx)
    config = load_config(aictx_dir)
    if adapter not in config.get("adapters", []):
        click.echo(f"Adapter '{adapter}' not in config.adapters.", err=True)
        sys.exit(1)
    load_plugins_from_dir(aictx_dir / "plugins")
    _, errors, index = run_validate(root)
    if errors:
        for e in errors:
            click.echo(e, err=True)
        sys.exit(1)
    emit("before_export", root=root, config=config, index=index, adapter=adapter)
    try:
        from .adapters.base import run_export
        run_export(root, aictx_dir, index, adapter)
    except (FileNotFoundError, ValueError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    emit("after_export", root=root, config=config, adapter=adapter)
    click.echo(f"Exported to {adapter}.")


if __name__ == "__main__":
    main()
