# Current Task

Task:

`STAGE2_WORKSPACE_RUNTIME_PROBE_01`

Status:

- Adding a read-only Workspace Runtime Viewer to Stage2 Config.

Purpose:

- Observe the real in-memory conversion from DocumentModel to workspace fields.
- Report workspace sections, fields, warnings, and diagnostics.
- Verify WorkspaceBuilder can consume the current built DocumentModel.

Rules:

- Keep the viewer read-only.
- Do not modify WorkspaceBuilder, DocumentModel, Template Analysis, pipeline state, Workspace page, or export runtime.
- Do not write configuration data.
- Do not restore old export chains.
