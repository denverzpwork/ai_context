# Copilot adapter

Export of context for GitHub Copilot. The processor reads `context.json` in this directory (read-only). Export is **declaration-only**: only documents listed in the `documents` array are exported. Each entry must have `id`, `kind`, `source` (path relative to ai_context root), and `target` (path relative to `output_dir`). If `documents` is missing or empty, no files are copied. The processor validates that every source exists and enriches entries from the index when available.

Result: declared files are copied into `output_dir` (`.github`), and `output_dir/context.json` is written with `output_dir` and the document list (with enriched metadata when indexed).

Run from repo root:

```bash
aictx export copilot
```

(Ensure `.aictx/venv` is activated and `aictx` is on PATH.)

Source:
 - https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions
 - https://code.visualstudio.com/docs/copilot/guides/context-engineering-guide
 