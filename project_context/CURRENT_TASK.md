# Current Task

Task:

`STAGE2_DOCUMENTMODEL_BUILDER_SIGNATURE_FIX_01`

Status:

- Fixing the DocumentModel Builder visual node call signature mismatch.

Purpose:

- Stage2 Config has already produced real `semantic_regions`.
- DocumentModel Runtime failed because the builder passed visual location parameters that the imported visual node builder did not accept.
- Add a minimal builder-local compatibility wrapper so `cell`, `row`, `col`, `page`, and `bbox` are preserved through `coordinates`.

Rules:

- Do not modify Stage2 Config routes or frontend.
- Do not modify old routes, old pages, old data, Workspace, or export runtime.
- Do not modify `analyze_template()`.
- Do not rewrite the DocumentModel structure.
- Do not restore old export chains.
