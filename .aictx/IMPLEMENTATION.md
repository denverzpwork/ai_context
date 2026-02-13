# aictx Implementation Summary

This document describes what was actually delivered: structural decisions, deviations from the plan, trade-offs, and follow-up work. It is based on [SPEC.md](SPEC.md) and the current codebase.

---

## Delivered scope

- **CLI:** `validate`, `build-manifest`, `list`, `diff`, `export <adapter>`
- **Layout:** All processor code and runtime under `.aictx/` (venv, `src/aictx/`, config, state, cache, plugins, bin)
- **Document model:** Frontmatter parsing, schemas for `spec` and `rule`, defaults (tags → `[]`, version → 1)
- **Indexing:** Rules from `rules/*.md`, tasks from `tasks/<TASK-ID>/` with `spec.md` and optional context, plan, implementation, review, tests-review
- **Validation:** Required files by complexity, frontmatter, schema, enums, references
- **Manifest:** `ai_context/manifests.yaml` with documents, active_set, relations, root_checksum; state saved in `.aictx/state/` for diff
- **Adapter:** Cursor (and copilot); export is **declaration-only**: the document set is defined solely in `ai_context/adapters/<name>/context.json` (`output_dir` + explicit `documents` list with id, kind, source, target). The processor validates that each source exists, enriches from the index when a document is indexed, and copies only the declared set. If `documents` is missing or empty, zero files are exported. Writes `output_dir/context.json` with output_dir and documents only.
- **Plugins:** Lifecycle hooks (before/after validate, build_manifest, export); load from `.aictx/plugins/*.py`, fail soft

---

## Structural decisions

### Index key scheme

- **Rules:** Index key = `doc.id` from frontmatter (e.g. `rule-security-001`).
- **Task spec:** Index key = `{task_dir.name}-spec` (e.g. `TASK-123-spec`), not the raw `doc.id`, so manifest document ids align with README (e.g. `TASK-123-spec`).
- **Other task docs:** Index key = `{task_dir.name}-{stem}` (e.g. `TASK-123-context`, `TASK-123-plan`).

This keeps manifest ids unique and stable. Reference validation accepts either the index key or the task id (e.g. `TASK-123` resolves via `TASK-123-spec`).

### Root resolution

- **Context root (ai_context):** No environment variable. Resolution is: explicit `--context-root` (validated: must contain `.aictx` or `rules/`), or walk up from cwd until `manifests.yaml`, `rules/`, or `tasks/` is found; else cwd.
- **Project root:** Optional. Used as base for adapter `output_dir`. Resolution: explicit `--project-root` (validated: must exist, be a directory, writable), or config `project_root` (path relative to `.aictx` or absolute); if neither set, adapters use context root.
- **.aictx dir:** Walk up from cwd until a directory containing `.aictx` is found; then `.aictx` is that path. If not found, `aictx_dir` falls back to `cwd/.aictx` so config/state paths still work when run from inside the repo.

### build-manifest always runs validate

- There is no “build without validate” flag. `build-manifest` always runs validation first and exits on error. This avoids writing a manifest from an invalid tree and matches the SPEC “fail fast” approach.

### Relations from references only

- Relations are built only from frontmatter `references: [id, ...]`. Every reference becomes a relation with **type `uses`**. There is no support (yet) for explicit relation types (e.g. `depends`, `supersedes`) in frontmatter or a dedicated `relations` block in documents.

### Aggregated checksum eligibility

- **Rules:** Always included in the aggregated checksum (no status filter).
- **Task docs:** Only documents whose task spec has `status: active` are included (plus the spec itself if active). So the root_checksum reflects the “active” snapshot only.

### Adapter contract (declaration-only)

- Adapter contract is in the repo: `ai_context/adapters/<name>/context.json` (read-only). It must contain `output_dir`; the exported document set is **only** the explicit `documents` array in that file (each entry: id, kind, source, target). The processor does not select or filter from the index: if a document is not listed in the declaration, it is not exported. If `documents` is missing or empty, only the output directory is ensured and `output_dir/context.json` is written with an empty documents list (zero file copies). The processor validates that every declared source exists under the context root (fail fast), enriches entries from the index when the document is indexed (version, checksum, status, tags), copies exactly the declared set. Output is written under project root (from config or `--project-root`) or context root; writes `output_dir/context.json` with `output_dir` and `documents` only (no relations/active_set).

### Plugin loading

- Only top-level `.py` files in `.aictx/plugins/` are loaded. No package subdirs or entry points. Each module is loaded with a unique name; any function whose name matches a known hook is registered. Exceptions in hooks are caught and ignored (fail soft).

---

## Deviations from the plan

1. **Relation types**  
   Plan/SPEC mention relation types `uses`, `depends`, `supersedes`. Only `uses` is implemented; all references are emitted as `type: uses`. No frontmatter or document field for other types.

2. **Normal task required files**  
   Plan defers to README for normal/critical. Implemented set for *normal* is `spec.md`, `plan.md`, `implementation.md`, `tests-review.md`. README allows “review short” for normal; we do not require a separate `review.md` for normal (only for critical). So “review” for normal is not enforced as a file.

3. **Copilot adapter**  
   Implemented: same pattern as cursor (contract in `ai_context/adapters/copilot/context.json`, export_copilot in processor).

4. **Adapter spec missing**  
   Plan: “If spec is missing — error.” Implemented: missing `ai_context/adapters/<name>/context.json` raises `FileNotFoundError` and export fails (no fallback).

5. **Cache**  
   `cache/` exists and is documented (state vs cache). No code uses it; no index or parsed-doc cache is written. Deleting cache has no effect today.

6. **list source**  
   Plan says “Source — index (or built manifest if preferred).” Implementation always uses the **index** (fresh walk), not the built manifest. So list reflects current files, not the last manifest.

7. **Environment variable for root**  
   Plan suggested “env var or walk up from cwd.” Only walk and `--context-root` / `--project-root` were implemented; no env var for context or project root.

---

## Important trade-offs

1. **In-memory index only**  
   Every command that needs the document set builds the index from disk. There is no persistent index or cache. Trade-off: simple and always consistent with the tree; cost is repeated I/O and parsing on large repos.

2. **Plugins fail soft**  
   Hook exceptions are caught and not re-raised. A broken plugin cannot break validate/build-manifest/export, but failures are invisible unless plugins log or the hook contract is extended (e.g. return value or logging).

3. **Single relation type from references**  
   Using only `uses` keeps the model simple and avoids defining how `depends`/`supersedes` would be expressed in frontmatter. Richer relation typing is left to follow-up.

4. **No manifest sensitivity**  
   README and convention mention a `sensitivity` section in the manifest for export/leak prevention. Not implemented: manifest has no sensitivity data, and adapters do not filter by it.

5. **task meta.yaml**  
   Convention allows optional `tasks/<TASK-ID>/meta.yaml` for stricter automation. The processor does not read it; task metadata is taken only from `spec.md` frontmatter.

6. **shared/ not indexed**  
   The convention has `shared/` (prompts, templates, checklists). The processor does not discover or index anything under `shared/`. Only `rules/` and `tasks/` are used for the document index and manifest.

---

## Follow-up work / technical debt

1. **Relation types**  
   - Support explicit relation type per reference (e.g. in frontmatter or a structured `relations` list with `from`, `to`, `type`).  
   - Validate that `type` is one of `uses`, `depends`, `supersedes` (and any future SPEC types).

2. **Copilot adapter**  
   - Done: `ai_context/adapters/copilot/context.json` and `export_copilot()` use the same protocol (context.json read-only, payload with source/target, file copies, context.json in output_dir).

3. **Sensitivity**  
   - Add optional `sensitivity` in manifest (e.g. per document or task) and document the semantics.  
   - Consider adapter behavior: exclude or redact sensitive items when exporting, if specified.

4. **Cache**  
   - Optionally cache parsed documents or the index in `.aictx/cache/` with invalidation by mtime or content hash, so validate/list/build-manifest can reuse it when the tree is unchanged.

5. **Optional meta.yaml**  
   - If present, read `tasks/<TASK-ID>/meta.yaml` for status/complexity/owner and merge with or override spec frontmatter for manifest and validation.

6. **shared/ and other kinds**  
   - Define whether `shared/` (or other top-level doc dirs) should be indexed and under which `kind`. If yes, extend discovery and schema handling.

7. **Plugin API and observability**  
   - Document the exact keyword arguments passed to each hook and their types.  
   - Consider a minimal plugin API (e.g. version, required context keys).  
   - Optionally log or report plugin failures (e.g. stderr or a `--verbose` flag) instead of failing completely silent.

8. **Build without validate**  
   - If needed for recovery or scripting, add a flag (e.g. `--no-validate`) to `build-manifest` that skips validation and builds from current index at caller’s risk.

9. **Normal “review”**  
   - Align with convention: either require a `review.md` (or equivalent) for normal complexity or explicitly document that “review short” can be satisfied by a section in another file and not enforce a separate file.

10. **Tests**  
    - No automated tests in the repo. Add unit tests for frontmatter parsing, schema validation, index building, checksum determinism, and CLI commands (e.g. with a fixture tree).
