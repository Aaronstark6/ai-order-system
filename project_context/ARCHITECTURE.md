# Architecture

Current target architecture:

```text
DocumentModel
-> WorkspaceBuilder
-> confirmedOrderObject
-> ExportStrategy
-> export_operations
-> Pipeline
-> processed_operations
-> Excel
```

Stage2 source of truth:

- `confirmedOrderObject`

Stage2 runtime goals:

- Use DocumentModel-derived workspace fields.
- Let the user confirm editable workspace fields.
- Convert confirmed values into `confirmedOrderObject`.
- Export through the Stage2 pipeline only.

Active runtime routes:

- `GET /api/v4/template-profiles`
- `POST /api/v4/parse-chat-run-pipeline`
- `POST /api/v4/core-pipeline/run`
- `POST /api/v4/export-pipeline-excel`

Retired paths:

- `confirmed_cells` is deprecated.
- `export-confirmed-excel` is deprecated.
- `parse-chat-export-excel` is deprecated.
- `core-pipeline/export-excel` is deprecated.

Architecture rule:

- Do not keep two production export chains.
- Do not patch the retired chain for compatibility.
- New work should follow `confirmedOrderObject` through Stage2 export.

Stage2 Config chain:

```text
Stage2 Config Page
-> /api/v4/stage2-config/*
-> stage2_config_profiles.json
-> semantic_workspace_schema
-> workspace_fields
-> field_bound_operations
-> Workspace / Export Pipeline
```

Configuration boundary:

- Old configuration chain is frozen.
- Stage2 Config is an independent chain.
- Stage2 Config must use `data/stage2_config_profiles.json`.
- Old configuration pages should not receive new Stage2 configuration logic.

Stage2 Config source observation:

```text
Stage2 Config Page
-> /api/v4/stage2-config/source-summary
-> stage2_config_profiles.json
-> legacy template_profiles.json read-only
-> v4_template_cache read-only
-> data source status before DocumentModel / semantic schema binding
```

Observation rule:

- Source Summary is read-only.
- It must not write old profile data.
- It must not use old profile data as the Stage2 main configuration source.

Stage2 Config template analysis observation:

```text
Stage2 Config Page
-> /api/v4/stage2-config/template-analysis-summary
-> legacy template_profiles.json read-only summary
-> v4_template_cache read-only summary
-> determine whether semantic_workspace_schema / workspace_fields / field_bound_operations exist
```

Template analysis observation rule:

- This is not a configuration bridge.
- This does not promote old profile data into the Stage2 main chain.
- This only reports whether the existing analysis data can support a future DocumentModel binding.

Stage2 Config DocumentModel Viewer:

```text
Stage2 Config Page
-> /api/v4/stage2-config/documentmodel-viewer
-> read-only find DocumentModel / nodes / cache rules diagnostic
-> output node stats and diagnostics
-> decide next step formal DocumentModel Builder or rebuild Template Analysis -> DocumentModel chain
```

DocumentModel Viewer rule:

- It is read-only.
- It must not generate semantic schema, workspace fields, or field bound operations.
- It must not write old configuration data.
- Cache `rules.json` can appear only as `cache_rules_diagnostic_only`.
- Cache rules are not a formal DocumentModel.

Stage2 Config DocumentModel Runtime:

```text
Stage2 Config Page
-> /api/v4/stage2-config/documentmodel-runtime
-> try to read real template_analysis
-> build_document_intelligence_model(template_analysis)
-> return formal DocumentModel summary or diagnostics
-> decide whether Stage2 needs a Template Analysis Runtime
```

DocumentModel Runtime rule:

- It is read-only.
- It can report a built DocumentModel only after calling `build_document_intelligence_model`.
- It must not synthesize `semantic_regions`.
- It must not promote cache rules into formal DocumentModel input.
- It must not generate semantic schema or workspace fields.

Template Analysis state preservation:

```text
analyze_template()
-> semantic_regions / semantic_summary
-> set_template_analysis()
-> pipeline_state.template_analysis
-> Stage2 Config DocumentModel Runtime
-> build_document_intelligence_model(template_analysis)
```

State preservation rule:

- `set_template_analysis()` must preserve real `semantic_regions`.
- `set_template_analysis()` must preserve real `semantic_summary`.
- Missing `semantic_regions` should become an empty list.
- Missing `semantic_summary` should become an empty dict.

Stage2 Config Template Library:

```text
Stage2 Config
-> Template Library
-> Select Template
-> analyze_template()
-> set_template_analysis()
-> pipeline_state.template_analysis
-> DocumentModel Runtime
```

Template Library rule:

- It reads `data/v4_template_uploads` directly.
- It does not write `template_profiles.json`.
- It does not depend on the old configuration page.
- It only uses the selected template to run Template Analysis and refresh runtime state.

DocumentModel Builder signature fix:

```text
Template Analysis
-> semantic_regions
-> build_document_intelligence_model
-> DocumentModel Runtime
```

Current fix:

- The builder accepts visual node `cell` / row / col / page / bbox call arguments.
- These values are preserved through `coordinates`.
- This keeps DocumentModel Runtime moving without changing Stage2 Config or old routes.

Semantic Region Type Summary:

```text
Stage2 Config
↓
Run Template Analysis
↓
pipeline_state.template_analysis.semantic_regions
↓
Semantic Region Type Summary
↓
判断 Template Analysis 分类与 DocumentModel Builder 字段识别是否一致
```

Field Candidate Audit:

```text
Stage2 Config
-> Run Template Analysis
-> pipeline_state.template_analysis.semantic_regions
-> group section_header / table_header / inline_field / unknown without reclassification
-> Field Candidate Audit
```

Field Candidate Audit rule:

- It is read-only.
- It preserves each original semantic region.
- It does not convert `section_header` into a field.
- It does not call or modify Template Analysis or DocumentModel Builder.

Template Analysis 字段优先级调整：

```text
label
-> image/note/title 排除
-> explicit section keyword 保留为 section
-> right_target / below_target 优先 field_label
-> section_header
-> option / inline / unknown
```

DocumentModel 质量门槛：

DocumentModel built 后，必须先通过 node_id 唯一性与 link 完整性审计，再进入 semantic_workspace_schema / workspace_fields 生成。

DocumentModel Node Identity 规则：

- `node_id` 必须稳定、唯一、可追溯。
- 同 label 不同 `source_cell` 必须生成不同 `node_id`。
- `node_id` 生成优先使用 label + source_cell，不使用随机数。
