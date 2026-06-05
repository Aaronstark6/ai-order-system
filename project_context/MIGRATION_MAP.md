# MIGRATION_MAP.md

## Purpose

This file is the migration control map for rebuilding AI Order System into:

D:\CursorFilses\ai-order-system-new

The new system must migrate product capabilities, not old files.

## Highest migration criteria

1. Product goal
2. Capability value
3. Contract value
4. Architecture layer
5. Code implementation
6. Old file location

## Product main chain

Template
-> TemplateAnalysisResult
-> DocumentModel
-> WorkspaceContract
-> ConfirmationResult
-> ExportStrategy
-> WriteResult

## Target layers

- app/core
- app/middle_layer
- app/application
- app/routes
- app/schemas
- app/config
- static
- data
- tests
- project_context

## P0 migration assets

| Old asset | Capability | Target layer | Status | Rule |
|---|---|---|---|---|
| app/v4_template_analysis.py | Template Analysis | app/core/template_analysis | pending | Extract capability, do not copy blindly |
| app/v4_document_intelligence.py | Document intelligence structures | app/middle_layer/document_model | pending | Extract contract and model only |
| app/v4_document_intelligence_builder.py | DocumentModel Builder | app/middle_layer/document_model | pending | Extract after TemplateAnalysisResult contract |
| app/v4_workspace_builder.py | Workspace Builder | app/middle_layer/workspace | pending | Extract after DocumentModel |
| app/v4_export_strategy_builder.py | Export Strategy Builder | app/middle_layer/export_strategy | pending | Extract after WorkspaceContract |

## P1 migration assets

| Old asset | Capability | Target layer | Status | Rule |
|---|---|---|---|---|
| app/v4_template_profiles.py | Template profile management | app/application or data/profiles | pending | Must separate config, state, and storage |
| app/excel_writer.py | Excel writing | app/core/writers | pending | Must not depend on old mapping or pipeline_state |
| app/excel_generator.py | Excel generation helpers | app/core/writers | pending | Reference only until dependency audited |
| static/v4_order_workspace.html | Workspace UI | static/workspace | pending | Rebuild against new API only |
| static/v4_stage2_config.html | Config UI | static/config | pending | Rebuild against new API only |

## Forbidden migration assets

| Old asset / concept | Reason |
|---|---|
| app/v4_pipeline_state.py | Old global state center |
| confirmed_cells as main chain | Old export source |
| processed_operations as main chain | Old export source |
| routes/v4.py as copied file | Mixed route, service, core, middle layer, state |
| source_cell as FieldIdentity | Coordinate must not define identity |
| target_cell as FieldIdentity | Write location must not define identity |
| legacy / compat / demo logic | Historical compatibility residue |
| old core-pipeline API | Old chain |
| old export-confirmed API | Old chain |
| old parse-chat-export API | Old chain |

## Identity and coordinate rules

FieldIdentity answers:
Who is this field?

TemplateCoordinate answers:
Where was it found in the source template?

VisualCoordinate answers:
Where should it be displayed?

WriteCoordinate answers:
Where should the value be written?

Coordinates may be metadata.
Coordinates must not be the main field identity.

## Migration rule

Each migrated capability must have:

1. clear input
2. clear output
3. clear layer
4. no hidden global state
5. no old route dependency
6. no old pipeline_state dependency
7. independent validation script
8. JSON output for inspection
9. Git commit after validation
