# Current Task

Task:

`STAGE2_SEMANTIC_REGION_TYPE_SUMMARY_01`

Status:

- Adding a read-only Semantic Region Type Summary to Stage2 Config.

Purpose:

- Read the current `pipeline_state.template_analysis.semantic_regions`.
- Report the real semantic region type, key, and selected value distributions.
- Use the results to diagnose why `field_node_count` is low.

Rules:

- Keep the diagnostic read-only.
- Do not modify old routes, old pages, old data, Workspace, or export runtime.
- Do not modify `analyze_template()`.
- Do not call DocumentModel Builder.
- Do not restore old export chains.
