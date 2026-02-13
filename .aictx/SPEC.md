# aictx Processor Specification

## Mission

Create a tool that turns the `ai_context/` directory into a manageable, verifiable, and reproducible knowledge system for humans, CI, and AI agents.

The aictx processor does not own knowledge. It only:

* validates
* indexes
* computes dependencies
* builds representations for external consumers

---

## Boundaries

### In scope

* reading the structure
* convention validation
* manifest generation
* filtering by status
* export via adapters

### Out of scope

* project source code analysis
* requirement generation
* modifying documents
* business logic

---

## Source of truth

```
/ai_context/*
```

If `.aictx` is completely removed, data must remain sufficient to rebuild every derived artifact.

---

## Target layout

```
/.aictx
  config.yaml
  state/
  cache/
  plugins/
  bin/
```

---

## CLI contract

Minimum required command set.

### validate

Must verify:

* required files
* presence of frontmatter
* schema correctness
* references
* enum values
* dependency integrity

Failure → non-zero exit code.

---

### build-manifest

Creates or updates:

```
ai_context/manifests.yaml
```

Including:

* checksums
* versions
* statuses
* complexity
* tags
* relations

---

### diff

Shows knowledge changes between states.

Used in CI and review.

---

### list

Provides selections.

Examples:

```
aictx list --status active
aictx list --kind rule
```

---

### export

Executes adapter contract.

```
aictx export cursor
aictx export copilot
```

---

## Config

```
.aictx/config.yaml
```

Minimum:

```
convention_version: 0.0.1
adapters:
  - cursor
```

---

## Document model

The processor must be able to extract from every document:

* id
* kind
* version
* status
* complexity
* tags

Missing → error.

---

## Checksums

Required:

* file hash
* aggregated hash of the active set

Any change must alter the result.

---

## Status semantics

Default read mode:

```
active
```

Other statuses participate only in historical operations.

---

## Relations

Must support a graph:

```
from → to → type
```

Minimum types:

* uses
* depends
* supersedes

---

## Plugin system

The core must allow:

* registering new commands
* subscribing to lifecycle events
* adding exporters

Without modifying the core.

### Lifecycle events (minimum contract)

Plugins must be able to hook into predictable execution points.

```
before_validate
after_validate
before_build_manifest
after_build_manifest
before_export
after_export
```

The list may grow, but existing names are stable and versioned.

---

## Formal contracts

This section defines strict interfaces required for independent implementations and plugin compatibility.

---

### Document schemas by kind (minimum)

#### spec

Required:

* id
* kind
* status
* complexity

Optional:

* version
* tags
* owner

#### rule

Required:

* id
* kind
* version

Optional:

* tags

Status is not required unless explicitly declared by the convention.

#### other kinds

If a kind is unknown to the processor, it must still expose the base fields:

* id
* kind

Everything else may be extension-defined.

---

### References format

The processor validates only explicit structured references.

```
references:
  - TASK-123
  - rule-security-001
```

Inline mentions inside markdown are ignored by the core and may be handled by plugins.

---

### diff semantics

Default behavior:

```
current workspace state vs last built manifest
```

Future extensions may allow git or file-to-file comparison, but this is the baseline.

---

### list output contract

Default → human readable table.
`--json` → machine format, stable for scripting.

---

### Core ↔ adapter interface

Adapters are **declarative contracts**, not logic modules.

The source of the export set is:

```
ai_context/adapters/<name>/context.json
```

The file defines:

* `output_dir`
* explicit list of documents
* target paths
* optional relations or metadata required by the consumer

The processor must:

1. read this declaration
2. verify that referenced sources exist
3. enrich entries with data from the index if needed
4. perform the copy / materialization

If a document is not declared in the adapter contract, it must not be exported.

Adapters do not select, filter, or compute anything.
They only describe the desired result.

---

### state vs cache

```
state = affects logic and reproducibility
cache = performance only
```

Deleting cache must never change results.
Deleting state may.

---

### Aggregated checksum algorithm

Must be deterministic.

Rules:

1. include only documents eligible under current read mode (default = active)
2. sort by id
3. hash normalized content

---

### Defaults and absence handling

If optional fields are missing, processor behavior must be predictable.

Examples:

* missing tags → empty list
* missing version → assume 1

If a required field for the given kind is missing → validation error.

---

---

## Error philosophy

Fail fast.

Better to stop CI than to construct a wrong world model.

---

## Non-functional requirements

### Determinism

Same input → same manifest.

### Recoverability

Every derived artifact must be rebuildable.

### Observability

Commands must report what was included.

### Extensibility

New document kinds will appear over time.

---

## Out of scope (for now)

* UI
* web dashboards
* automatic documentation generation
* AI inference

---

## Definition of Done

It must be possible to:

1. run `validate`
2. build a manifest
3. obtain an active snapshot
4. export using an adapter contract

without manual intervention.

---

## Long term vision

This layer makes knowledge:

* computable
* comparable
* reproducible

Without it, `ai_context` degrades into a set of markdown files.
