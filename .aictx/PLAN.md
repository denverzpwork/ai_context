# aictx Implementation Plan (Python)

Sources: README (convention), SPEC (processor contract). Language: Python. Dependencies: venv; external packages only when needed.

---

## 1. Environment and project layout

**Principle:** Convention documents (ai_context) and the aictx processor are kept separate. Everything that belongs to aictx **MUST** live **inside** `.aictx/`.

* **Content root (ai_context):** repository root or a directory set via `--root` / search upward from cwd. It contains `manifests.yaml`, `rules/`, `tasks/`, `shared/`, `adapters/` — convention data only, no processor code.
* **Everything related to the processor — inside `.aictx/`:**

  * **venv:** `.aictx/venv/` (or `.aictx/.venv/`). Create with `python3 -m venv .aictx/venv`; install deps from `.aictx/` with `pip install -e .aictx/`.
  * **Processor code:** package under `.aictx/` with CLI entry point providing `validate`, `build-manifest`, `list`, `diff`, `export`.
  * **pyproject.toml** at `.aictx/pyproject.toml`.
  * **config.yaml, state/, cache/, plugins/, bin/** — all under `.aictx/`.
* CLI execution: activate venv and run `aictx`, or wrapper `.aictx/bin/aictx`.
* External packages: YAML, frontmatter, CLI helpers; install only into local venv.

---

## 2. Configuration and paths

* Read `.aictx/config.yaml`: at least `convention_version`, `adapters`.
* Resolve ai_context root from cwd or explicit flag.
* Use a single resolver across all commands.

---

## 3. Document model and frontmatter parsing

* Extract YAML between `---`.
* Validate encoding and structure.
* Apply schemas per kind.
* Defaults: `tags=[]`, `version=1`.
* Validate explicit `references` against index.

---

## 4. Discovery and indexing

* Walk ai_context recursively.
* Identify rules, tasks, shared artifacts.
* Build index: id → path/kind/metadata.

This index supports validate, manifest, list, export enrichment.

---

## 5. `validate`

Fail on:

* missing required files
* invalid frontmatter
* schema violations
* bad enums
* broken references

Return non‑zero on error.

---

## 6. `build-manifest`

* Hash each document.
* Build aggregated hash of active set.
* Produce `ai_context/manifests.yaml`.
* Persist last result in `.aictx/state/`.

---

## 7. State and cache

* state → affects reproducibility.
* cache → speed only.

---

## 8. `list`

Read from index or manifest.
Provide table or stable JSON.

---

## 9. `diff`

Compare current index vs last state snapshot.
Report added / removed / changed.

---

## 10. Export and adapters

Adapters are **pure declarations** of what the final exported tree must look like.

They do not compute the document set.
They do not receive a ready snapshot.
They do not filter.

Single source of truth for export composition:

```
ai_context/adapters/<name>/context.json
```

If something is not declared there → it must not be exported.

### Minimal contract

```json
{
  "output_dir": ".cursor",
  "documents": [
    {
      "id": "rule-security-001",
      "kind": "rule",
      "source": "rules/security.rule.md",
      "target": "rules/security.rule.md"
    }
  ]
}
```

### Invariants

* `source` relative to `ai_context`
* `target` relative to `output_dir`

### Core algorithm

```
load declaration
→ validate existence of every source
→ enrich metadata from index/manifest if required
→ copy exactly declared set
```

No implicit expansion.
No auto inclusion of active documents.

`output_dir` alone = zero files.

### Command

```
aictx export <name>
```

means execute this pipeline, nothing else.

Any future adapter (cursor, copilot, etc.) differs only by the declaration file.

---

## 11. Plugins (minimal)

Support lifecycle hooks around validate / manifest / export.
No change to export ownership.

---

## 12. Implementation order and DoD

Suggested sequence:

1. project skeleton
2. config + root resolver
3. parser + index
4. validate
5. manifest + state
6. list
7. diff
8. export via declaration execution
9. hooks

Done when pipeline runs without manual intervention.

---

## Data flow

```
ai_context → index → manifest/state
adapter declaration → export plan
core → executes plan
```
