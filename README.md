# AI Context Engineering Convention

**Version:** 0.0.2

**Last updated:** 2026-02-12

**Author:** denver.zp

## Background

The AI Context Engineering domain is evolving rapidly, yet almost every tool expects its own format and file set.

As a result, recurring problems appear:
- knowledge becomes tied to a specific framework or vendor;
- migration between agents becomes expensive;
- part of the context lives in prompts instead of the repository;
- automation requires additional interpretation layers.

This convention is an attempt to formalize the placement and roles of context within a project so that tools can change without losing reproducibility.

## Architectural goals

The model must guarantee:

1. context reproducibility;
2. portability across tools;
3. a single source of truth;
4. traceability from requirement to proof of completion.

The following sections describe which mechanisms deliver these properties: directory structure, document types, authorship rules, and derived indexes.

---

## Task lifecycle (axis of the model)

Any work evolves linearly:

1. a requirement appears (spec)
2. constraints are recorded (context)
3. a strategy is chosen (plan)
4. factual implementation emerges (implementation)
5. an audit is performed (review)
6. coverage evidence is produced (tests-review)

A task directory must allow reconstruction of this chain without external sources.

---

## Source of truth

Only documents inside `ai_context/` are canonical.

Any indexes, exports, or projections are derivatives and must be fully reconstructable from the file structure.

---

## Root structure

```
ai_context/
  manifests.yaml
  rules/
  tasks/
  shared/
  adapters/
  README.md
```

The structure defines the **maximum envelope** of possible elements.

The actual mandatory set for a particular task is defined by the `complexity` field in `spec.md`.

The root must be self-sufficient. Removal of external tools must not destroy access to knowledge.

---

## Grouping around the task

A task is the minimal unit of navigation and automation.

The file set inside the directory mirrors the lifecycle steps defined earlier.

Each document is either an input to the next stage or proof of completion of the previous one.

```
ai_context/tasks/<TASK-ID>/
  spec.md
  context.md
  plan.md
  implementation.md
  review.md
  tests-review.md
```

Colocation eliminates:

* divergence of assumptions;
* loss of decision motivation;
* inability to audit;
* prompt fragmentation.

---

## Scaling depth (complexity)

Not every change requires the same level of formalization. The mandatory artifact set depends on risk.

```
complexity: trivial | normal | critical
```

| level    | spec | context | plan | implementation | review | tests |
| -------- | ---- | ------- | ---- | -------------- | ------ | ----- |
| trivial  | ✓    | –       | –    | ✓              | –      | –     |
| normal   | ✓    | opt     | ✓    | ✓              | brief  | ✓     |
| critical | ✓    | ✓       | ✓    | ✓              | ✓      | ✓     |

### Invariant

Regardless of level, the following are always required:

1. linkage to a requirement;
2. explanation of the actual outcome.

---

## Authorship and responsibility

The separation is driven by distortion risk, not convenience.

### Intent (human owned)

* `spec.md`
* `context.md`
* `plan.md`

AI may prepare drafts, but activation requires engineer confirmation.

### Factual state (AI efficient)

* `implementation.md`
* `review.md`
* `tests-review.md`

Automation is acceptable; humans perform acceptance.

---

## spec.md

Primary requirement and task identity anchor.

The document is the point from which derivative systems obtain:

* identifier;
* complexity level;
* status;
* requirement origin.

Key metadata, including status and complexity, lives here.

```
kind: spec
source: jira|github|client
complexity: normal
status: active
```

Changes are allowed only as clarifications, not historical rewrites.

### Status

```
status: active | historical | obsolete
```

Modified via PR, same as code.

By default, automation operates only on `active`.

---

## context.md

Local knowledge required before making changes: modules, contracts, constraints, integrations.

```
kind: context
```

The document describes the current work, not the entire system.

---

## plan.md

Rationalization of the chosen path between the requirement and the future code.

Contains:

* strategy;
* alternatives;
* risks;
* data impact;
* completion criteria.

```
kind: plan
```

May evolve as new information appears.

---

## implementation.md

Record of the observable result.

Contains:

* actual structural decisions;
* deviations from intent;
* compromises;
* emerging technical debt.

```
kind: implementation
```

Boundary: this describes what exists, not how good it is.

Recommended generation prompt: `shared/prompts/implementation.prompt.md`.

---

## review.md

Assessment of correctness and operational consequences.

```
kind: review
```

Answers questions of quality, configuration, and readiness. Does not duplicate structural description.

Recommended generation prompt: `shared/prompts/review.prompt.md`.

---

## tests-review.md

Mechanism that enforces the global traceability invariant.

Connects:

`requirement → code → automated evidence → manual verification`

```
kind: tests-review
```

Records coverage, gaps, and risk level.

Recommended generation prompt: `shared/prompts/tests-review.prompt.md`.

---

## shared/

Common templates and assets applicable across multiple tasks.

```
ai_context/shared/
  prompts/
  templates/
  checklists/
```

---

## manifests.yaml (derived index)

The manifest is built from canonical documents, primarily metadata declared in `spec.md` and file types within task directories.

It exists because some consumers require fast, normalized access.

It appears **after** the canon is defined, not instead of it.

### Purpose

* accelerated discovery;
* integrity control;
* relevant set selection;
* reproducible runs;
* caching.

### Recoverability

Removing the manifest must not cause knowledge loss. It must be rebuildable from the directory structure.

### Typical fragment

```
documents:
  - id: TASK-123-spec
    kind: spec
    path: tasks/TASK-123/spec.md
    status: active
```

### Checksums

If the hash has not changed, the context is considered identical. This is the basis for incremental pipelines.

---

## Direct reading and adapters

Canonical files may be consumed directly without intermediate preparation stages.

### Why adapters exist

For scenarios requiring:

* bulk processing;
* dependency resolution;
* filtering;
* format transformation.

### Constraints

An adapter is not allowed to:

* modify the source;
* maintain its own truth;
* enrich knowledge outside the repository.

If something is missing, the model changes, not the projection.

### Architecture test

Removing any adapter must not break the team workflow.

---

## Minimum adoption threshold

Even partial application of the model yields benefit.

Sufficient conditions:

1. maintain `rules/`;
2. store tasks in isolated directories;
3. keep `spec` and `implementation`.

This already establishes a reproducible foundation for future agents.
