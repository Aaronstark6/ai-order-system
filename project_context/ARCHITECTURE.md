# Architecture

Current target architecture:

```text
DocumentModel
-> WorkspaceBuilder
-> confirmedOrderObject
-> ExportStrategy
-> export_operations
-> Pipeline
-> processed_operations
-> Excel
```

Stage2 source of truth:

- `confirmedOrderObject`

Stage2 runtime goals:

- Use DocumentModel-derived workspace fields.
- Let the user confirm editable workspace fields.
- Convert confirmed values into `confirmedOrderObject`.
- Export through the Stage2 pipeline only.

Active runtime routes:

- `GET /api/v4/template-profiles`
- `POST /api/v4/parse-chat-run-pipeline`
- `POST /api/v4/core-pipeline/run`
- `POST /api/v4/export-pipeline-excel`

Retired paths:

- `confirmed_cells` is deprecated.
- `export-confirmed-excel` is deprecated.
- `parse-chat-export-excel` is deprecated.
- `core-pipeline/export-excel` is deprecated.

Architecture rule:

- Do not keep two production export chains.
- Do not patch the retired chain for compatibility.
- New work should follow `confirmedOrderObject` through Stage2 export.
