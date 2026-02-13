# aictx Processor

aictx turns the `ai_context/` directory into a manageable, verifiable, and reproducible knowledge system. It does **not** own or modify your content; it only validates, indexes, builds manifests, and exports via adapters.

See [SPEC.md](SPEC.md) for the full contract and [PLAN.md](PLAN.md) for the implementation plan.

---

## Directory layout

```
.aictx/
  config.yaml      # Convention version and enabled adapters
  state/           # Last built manifest (for diff); affects reproducibility
  cache/           # Optional performance cache; safe to delete
  plugins/         # Optional Python plugins (lifecycle hooks)
  bin/             # Wrapper script to run aictx without activating venv
  venv/            # Python virtual environment
  pyproject.toml   # Package definition and dependencies
  src/aictx/       # Processor source code
  README.md        # This file
  SPEC.md
  PLAN.md
```

**Source of truth** is always `ai_context/` (repo root). If `.aictx` is removed, all derived artifacts can be rebuilt from that content.

---

## Requirements

- **Python 3.9+**
- Commands are run from the **context root** (the ai_context directory) or with `--context-root` pointing to it.

---

## First-time setup

Create the virtual environment and install the processor (run once per clone):

```bash
cd .aictx
python3 -m venv venv
./venv/bin/pip install -e .
```

You can run aictx in either of these ways:

1. **Activate venv, then run `aictx`:**
   ```bash
   source .aictx/venv/bin/activate
   aictx validate
   ```

2. **Use the wrapper** (no activation; run from repo root):
   ```bash
   ./.aictx/bin/aictx validate
   ```
   Or add `.aictx/bin` to your `PATH`.

---

## Global options: `--context-root` and `--project-root`

- **`--context-root`** — Context root (ai_context directory: rules, tasks, adapters, sources). If omitted, detected by walking up from the current directory until `manifests.yaml`, `rules/`, or `tasks/` is found; otherwise the current directory. When provided (absolute or relative to cwd), must contain `.aictx` or `rules/`.

- **`--project-root`** — Project root (base for adapter `output_dir`; e.g. where `.cursor` or `.github` is written). If omitted, taken from config `project_root` when set; otherwise adapters write under the context root. When provided, must be an existing writable directory.

```bash
aictx --context-root /path/to/ai_context validate
aictx build-manifest --context-root /path/to/ai_context
aictx export cursor --project-root /path/to/repo
```

---

## Configuration: `config.yaml`

`.aictx/config.yaml` supports at least:

```yaml
convention_version: "0.0.1"
adapters:
  - cursor
  # - copilot
# Optional: project root (base for adapter output_dir). Relative to .aictx; absolute path also supported.
# project_root: "../.."
```

- **convention_version** — Matches the ai_context convention (see repo `README.md`).
- **adapters** — List of adapter names allowed for `aictx export <name>`.
- **project_root** — Optional. Path to project root (where adapters write output, e.g. `.cursor`). Relative to `.aictx` (e.g. `"../.."` for layout `project_root/ai_context/.aictx`); absolute path allowed. If missing and `--project-root` is not set, adapters use the context root.

If `config.yaml` is missing, defaults are used (e.g. `adapters: [cursor]`).

---

## Commands

### `validate`

Checks the ai_context tree: required files per task complexity, frontmatter presence and YAML validity, document schema per `kind`, enum values (`status`, `complexity`), and reference targets. Fails fast with a non-zero exit code and a list of errors.

```bash
aictx validate
```

**Checks performed:**

- Required files (e.g. `spec.md` + `implementation.md` for trivial tasks).
- Frontmatter delimiters `---` and valid YAML.
- Schema by kind: e.g. `spec` requires `id`, `kind`, `status`, `complexity`; `rule` requires `id`, `kind`, `version`.
- `status` in `active | historical | obsolete`; `complexity` in `trivial | normal | critical`.
- Each `references` entry points to an existing document id (or task id).

On success, prints the number of documents validated.

---

### `build-manifest`

Runs validation, then builds or updates `ai_context/manifests.yaml` with:

- **convention_version**, **generated_at**, **generator**, **root_checksum**
- **documents** — id, kind, path, version, status, complexity, checksum, tags
- **active_set** — document ids with status `active`
- **relations** — from / to / type (from frontmatter `references`, default type `uses`)

Also saves the built manifest into `.aictx/state/` for use by `diff`.

```bash
aictx build-manifest
```

Prints document count and active_set size.

---

### `list`

Lists documents from the index. Optional filters and output format.

```bash
aictx list
aictx list --status active
aictx list --kind rule
aictx list --kind spec --status active
aictx list --json
```

- **--status** — Filter by status (e.g. `active`).
- **--kind** — Filter by kind (e.g. `rule`, `spec`).
- **--json** — Machine-readable JSON (list of objects with `id`, `kind`, `status`, `path`, `complexity`).

Default output is a human-readable table.

---

### `diff`

Compares the **current workspace** (index built from disk) with the **last built manifest** stored in `.aictx/state/`. Reports added, removed, and changed document ids (by checksum). Useful in CI and reviews.

```bash
aictx diff
aictx diff --json
```

If no previous manifest exists, exits with a message and exit code 0. **--json** outputs `{"added": [], "removed": [], "changed": []}`.

---

### `export <adapter>`

Builds the payload (documents with source/target, relations, active_set) and delegates to the named adapter. The adapter reads its contract from `ai_context/adapters/<name>/context.json` (read-only), copies files to output_dir, and writes `output_dir/context.json`.

```bash
aictx export cursor
aictx export copilot   # if listed in config.adapters
```

The adapter name must appear in `config.yaml` under `adapters`. Validation is run before export; on failure, export is not performed.

**Cursor adapter:** Reads `ai_context/adapters/cursor/context.json` for `output_dir`, copies each document from context root/source to project root (or context root if not set)/output_dir/target, writes `output_dir/context.json` with documents.

---

## State and cache

- **state/** — Holds the last built manifest. Used by `diff`. Deleting it may change the result of `diff`.
- **cache/** — Reserved for optional performance caches. Deleting it must **not** change any command result.

---

## Adapters

Adapters live in the processor (e.g. `.aictx/src/aictx/adapters/`) but their **contract** is defined in the repo under `ai_context/adapters/<name>/`:

- **context.json** — Machine-readable; minimum field `output_dir` (relative to project root or context root). Read-only; the processor builds the document list from the index, copies files from context root/source to (project root or context root)/output_dir/target, and writes `output_dir/context.json`.
- **README.md** (optional) — Human-readable description of the adapter and output format.

Example: `ai_context/adapters/cursor/` contains `context.json` (e.g. `{"output_dir": ".cursor"}`) and `README.md`.

---

## Plugins

Optional Python files in `.aictx/plugins/` can register lifecycle hooks. Supported events:

- `before_validate`, `after_validate`
- `before_build_manifest`, `after_build_manifest`
- `before_export`, `after_export`

A plugin module can define functions with these names; they receive keyword arguments such as `root`, `config`, `index`, `manifest`, `adapter`. Hook failures are ignored (fail soft) so the main command still runs.

---

## Typical workflow (Definition of Done)

Run without manual steps:

1. **Validate** the tree:
   ```bash
   aictx validate
   ```

2. **Build the manifest** (and update state for diff):
   ```bash
   aictx build-manifest
   ```

3. **Get an active snapshot** (optional):
   ```bash
   aictx list --status active
   aictx list --status active --json
   ```

4. **Export** to an adapter (e.g. Cursor):
   ```bash
   aictx export cursor
   ```

All commands report what was included (observability). For CI, use `aictx validate`, `aictx build-manifest`, and optionally `aictx diff` to detect knowledge changes.
