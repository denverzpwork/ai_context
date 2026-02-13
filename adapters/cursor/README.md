# Cursor adapter

Export of context for Cursor. The processor reads `context.json` in this directory (read-only). Export is **declaration-only**: only documents listed in the `documents` array are exported. Each entry must have `id`, `kind`, `source` (path relative to ai_context root), and `target` (path relative to `output_dir`). If `documents` is missing or empty, no files are copied. The processor validates that every source exists and enriches entries from the index when available.

Result: declared files are copied into `output_dir` (`.cursor`), and `output_dir/context.json` is written with `output_dir` and the document list (with enriched metadata when indexed).

Run from repo root:

```bash
aictx export cursor
```

(Ensure `.aictx/venv` is activated and `aictx` is on PATH.)

Source:
 - https://cursor.com/en-US/docs/context/rules
 - https://cursor.com/learn/context
