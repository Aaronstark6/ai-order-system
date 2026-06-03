# Current Task

Task:

`POST_STAGE2_WORKSPACE_FIELD_LOSS_AUDIT_01`

Problem:

- AI Parse succeeds.
- The new Workspace page only displays `3 fields ready`.
- Many expected workspace fields are missing.

Audit path:

```text
DocumentModel
-> WorkspaceBuilder
-> workspace_fields
-> page fields
```

Audit question:

- Why are many fields lost before they reach the page?

Expected audit style:

- PowerShell-first read-only audit.
- Locate the exact loss boundary before editing.
- Do not guess.
- Do not patch randomly.
- Do not revive old Workspace logic.
- Do not revive old export logic.

Likely evidence to gather:

- Parse response shape.
- `semantic_workspace_schema` field count.
- `workspace_fields` field count.
- `field_bound_operations` count.
- `DocumentModel` node count.
- WorkspaceBuilder output count.
- Page extraction priority result count.
