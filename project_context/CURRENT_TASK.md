# Current Task

Task:

`STAGE2_CONFIG_DOCUMENTMODEL_RUNTIME_BIND_01`

Status:

- Stage2 Config is adding a read-only DocumentModel Runtime build endpoint.

Purpose:

- Try to reuse the existing `build_document_intelligence_model(template_analysis)` path.
- Return a formal DocumentModel summary when real `template_analysis.semantic_regions` exists.
- Return diagnostics when the required template analysis input is missing.

Rules:

- Do not generate `semantic_workspace_schema`.
- Do not write old configuration data.
- Do not modify Workspace, Pipeline, Validator, export runtime, or `app/routes/v4.py`.
- Do not treat cache `rules.json` as a formal DocumentModel.
- Do not fake `template_analysis` or `semantic_regions`.

New observation API:

- `/api/v4/stage2-config/documentmodel-runtime`

Expected next decision:

- If the runtime cannot find real template analysis, build a Stage2-specific Template Analysis Runtime before semantic schema generation.
