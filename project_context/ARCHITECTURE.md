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

Stage2 Config chain:

```text
Stage2 Config Page
-> /api/v4/stage2-config/*
-> stage2_config_profiles.json
-> semantic_workspace_schema
-> workspace_fields
-> field_bound_operations
-> Workspace / Export Pipeline
```

Configuration boundary:

- Old configuration chain is frozen.
- Stage2 Config is an independent chain.
- Stage2 Config must use `data/stage2_config_profiles.json`.
- Old configuration pages should not receive new Stage2 configuration logic.

Stage2 Config source observation:

```text
Stage2 Config Page
-> /api/v4/stage2-config/source-summary
-> stage2_config_profiles.json
-> legacy template_profiles.json read-only
-> v4_template_cache read-only
-> data source status before DocumentModel / semantic schema binding
```

Observation rule:

- Source Summary is read-only.
- It must not write old profile data.
- It must not use old profile data as the Stage2 main configuration source.
