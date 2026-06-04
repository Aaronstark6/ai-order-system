# Current Task

Task:

`STAGE2_DOCUMENTMODEL_NODE_ID_FIX_01`

Status:

- Fixing DocumentModel node ID generation for repeated labels.

Purpose:

- Make same-label nodes at different source cells produce different stable node IDs.
- Include `source_cell` in field, section, table, and visual node identity seeds.
- Let runtime policy IDs inherit uniqueness from their source node IDs.

Rules:

- Modify only the Builder-local seed passed to `make_node_id()`.
- Do not modify `make_node_id()`, Template Analysis, Stage2 Config, pipeline state, Workspace, or export runtime.
- Do not fix missing cell links in this task.
- Do not restore old export chains.
