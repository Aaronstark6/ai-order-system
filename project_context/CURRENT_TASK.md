# Current Task

Task:

`STAGE2_TEMPLATE_ANALYSIS_FIELD_PRIORITY_FIX_01`

Status:

- Fixing Template Analysis field recognition priority.

Purpose:

- Prioritize labels with explicit right-side or below writable targets as `field_label`.
- Keep explicit grouping headings as `section_header`.
- Prevent obvious fields such as document number, date, and customer name from being claimed by broad section header rules.

Rules:

- Make only a minimal rule priority adjustment in `build_semantic_regions()`.
- Do not modify Stage2 Config, DocumentModel Builder, pipeline state, Workspace, or export runtime.
- Do not modify table header logic.
- Do not convert every `section_header` into a field.
- Do not restore old export chains.
