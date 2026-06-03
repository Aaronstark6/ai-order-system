# Current Task

Task:

`STAGE2_CONFIG_TEMPLATE_LIBRARY_01`

Status:

- Building an independent Template Library inside Stage2 Config.

Purpose:

- Let Stage2 Config read templates directly from `data/v4_template_uploads`.
- Let the user select a template without using the old configuration page.
- Run `analyze_template(template_path)` from the Stage2 Config page.
- Save the result through `set_template_analysis()` so `pipeline_state.template_analysis` contains real Template Analysis data.
- Feed Stage2 Config DocumentModel Runtime with real `semantic_regions`.

Rules:

- Do not modify old configuration pages.
- Do not modify Workspace.
- Do not modify `template_profiles.json`.
- Do not modify `stage2_config_profiles.json`.
- Do not modify `analyze_template()` or DocumentModel Builder.
- Do not restore old export chains.
