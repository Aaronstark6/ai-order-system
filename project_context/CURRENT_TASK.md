# Current Task

Task:

`STAGE2_TEMPLATE_ANALYSIS_STATE_PRESERVE_01`

Status:

- Fixing the Template Analysis state preservation breakpoint.

Purpose:

- Preserve `semantic_regions` and `semantic_summary` when `set_template_analysis()` writes `pipeline_state.template_analysis`.
- Provide real Template Analysis input for Stage2 Config DocumentModel Runtime.
- Allow `build_document_intelligence_model(template_analysis)` to build from genuine `semantic_regions` after template analysis is rerun.

Rules:

- Do not modify `analyze_template()`.
- Do not modify DocumentModel Builder.
- Do not modify Workspace, old routes, old config pages, or export runtime.
- Do not write old profile data.
- Do not fake `semantic_regions`.
- Do not treat cache `rules.json` as `semantic_regions`.

Expected next test:

- Rerun template analysis so `set_template_analysis()` stores the newly preserved fields.
- Then verify `/api/v4/stage2-config/documentmodel-runtime` reports `semantic_regions_count > 0`.
