# Current Task

Task:

`STAGE2_CONFIG_DOCUMENTMODEL_VIEWER_01`

Status:

- Stage2 Config is adding a read-only DocumentModel Viewer observation layer.

Purpose:

- Confirm whether a real DocumentModel / document_model / nodes source already exists.
- Show node statistics and node summaries before building semantic schema generation.
- Return diagnostics when no formal DocumentModel is available.
- If only cache `rules.json` exists, display it only as diagnostic nodes.

Rules:

- Do not fake cache rules as a formal DocumentModel.
- Do not write old configuration data.
- Do not modify Workspace, Pipeline, Validator, or export runtime.
- Do not call old Workspace or export endpoints.

New observation API:

- `/api/v4/stage2-config/documentmodel-viewer`

Known diagnostic state:

- Cache rules may be shown with `source_type=cache_rules_diagnostic_only`.
- Diagnostics must include `rules_json_is_not_document_model` when cache rules are used this way.
