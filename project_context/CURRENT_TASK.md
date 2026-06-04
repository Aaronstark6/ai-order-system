# Current Task

Task:

`STAGE2_DOCUMENTMODEL_NODE_ID_AUDIT_01`

Status:

- Auditing DocumentModel node ID uniqueness and link completeness.

Purpose:

- Identify the real source regions behind duplicate `node_id` values.
- Identify links whose target node IDs do not exist.
- Preserve model warnings and errors for diagnosis before schema generation.

Rules:

- Keep the audit read-only.
- Do not modify DocumentModel Builder, Template Analysis, pipeline state, Workspace, or export runtime.
- Do not write configuration data.
- Do not restore old export chains.
