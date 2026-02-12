# Cursor adapter

Export of active context for Cursor. Result is written to `.cursor` (or as configured in `context.json`).

The file contains:

- `documents`: list of document metadata (id, kind, path, version, status, complexity, tags)
- `relations`: graph of references (from, to, type)
- `active_set`: list of document ids with status `active`

Run from repo root:

```bash
aictx export cursor
```

(Ensure `.aictx/venv` is activated and `aictx` is on PATH.)
