# V4 Export Final Status Audit

Audit ID: V4-EXPORT-FIX109A

Audit date: 2026-05-24

Scope:
- Template Analysis
- Auto Mapping
- Confirmed Cells
- Operations Pipeline
- Executor
- Real API Export

## 1. Current V4 Export Capability Matrix

| Capability | Current status | Evidence |
| --- | --- | --- |
| Template Analysis | Supported | Template analysis can classify image/attachment areas and mapping candidates. |
| Auto Mapping | Supported, profile-dependent | Auto mapping can generate structured, table, and block mappings. |
| Confirmed Cells: normal fields | Supported | `confirmed_cells(text)` enter `_override_operations_with_confirmed_cells`, become `write_text`, then executor writes cells. |
| Confirmed Cells: dynamic table fields | Supported | Parsed table rows and confirmed cells carry `row_offset` / `col_offset`; executor applies offsets through `_operation_target_cell`. |
| Confirmed Cells: workspace image fields | Partial / broken for current UI payload | `_confirmed_operation_from_item` emits `write_image`, but current workspace payload carries nested `image.data_url`; executor requires `image_path`, so image operation is skipped. |
| Operations Pipeline | Supported | Pipeline normalizes/finalizes op types and preserves supported ops. |
| Executor | Supported for all declared op types | `SUPPORTED_OP_TYPES = {"write_text", "write_number", "write_multiline", "write_table_cell", "write_block", "write_image"}`. |
| Real API Export | Partial | `/api/v4/export-confirmed-excel` uses override + executor, but current workspace image payload does not become an executable image operation. |

## 2. Link Status Table

| Link | Expected path | Status | Notes |
| --- | --- | --- | --- |
| Normal field export | `confirmed_cells(text)` -> `_override_operations_with_confirmed_cells` -> `_confirmed_operation_from_item` -> `write_text` / existing op override -> `execute_processed_operations_to_excel` -> Excel | PASS | Confirmed text values override matching operations or add new `write_text` operations. |
| Dynamic table export | dynamic table confirmed cells -> `write_table_cell` -> `row_offset` / `col_offset` -> executor -> Excel | PASS | Direct executor verification wrote `target_cell=A4,row_offset=1,col_offset=2` to `C5`. |
| Image field export | workspace image field -> `confirmed_cells(image)` -> override -> `_confirmed_operation_from_item` -> `write_image` -> executor -> Excel image insertion | FAIL for current workspace payload | Frontend sends `image.data_url`; `_confirmed_operation_from_item` does not convert nested `image.data_url` into `image_path`; executor warns "缺少 image_path" and writes 0 images. |
| Real API export | `/api/v4/export-confirmed-excel` -> profile -> feature flags -> override -> executor -> output file | PARTIAL | API calls override with all `confirmed_cells` and executes the resulting operations. Legacy image fallback is disabled by `use_operation_image_export = True`, exposing the current `image_path` gap. |

## 3. Feature Flags Status

Source defaults in `app/routes/v4.py`:

| Flag | `DEFAULT_EXCEL_FEATURE_FLAGS` | Effective `default_profile` |
| --- | ---: | ---: |
| `image_fields` | `true` | `true` |
| `dynamic_tables` | `false` | `false` |
| `advanced_write_modes` | `false` | `false` |
| `option_write_enhancement` | `false` | `false` |
| `format_protection` | `true` | `true` |
| `export_readback_check` | `true` | `true` |

Notes:
- `default_profile.json` has no `excel_feature_flags`, so its effective values are exactly `DEFAULT_EXCEL_FEATURE_FLAGS`.
- Existing non-default template profiles currently set all audited flags to `true`.
- `formula_protection` also exists and defaults to `true`, although it was outside the requested flag list.

## 4. Executor Support Matrix

`SUPPORTED_OP_TYPES`:

```text
write_text
write_number
write_multiline
write_table_cell
write_block
write_image
```

| op_type | In `SUPPORTED_OP_TYPES` | Executor behavior | Real reachable status |
| --- | --- | --- | --- |
| `write_text` | Yes | Writes scalar value to target cell. | Reachable from structured ops and confirmed text cells. |
| `write_number` | Yes | Writes numeric value like other scalar cells; pipeline preserves numeric values. | Reachable when structured mapping uses `operation=write_number`. |
| `write_multiline` | Yes | Writes text and applies wrap text. | Reachable when structured mapping uses `operation=write_multiline`. |
| `write_table_cell` | Yes | Writes scalar value after applying `row_offset` / `col_offset`. | Reachable from table mappings and parsed table confirmed cells. |
| `write_block` | Yes | Writes block text and applies wrap text. | Reachable from block mappings. |
| `write_image` | Yes | Requires `image_path`, then inserts image at `image_anchor_cell` / `target_cell`. | Reachable and executable with explicit `image_path`; not executable from current workspace `image.data_url` confirmed payload. |

Verification run:
- Direct executor test wrote `write_text`, `write_number`, `write_multiline`, `write_table_cell`, `write_block`, and `write_image` successfully.
- Direct executor output had `operations_written = 6`, table cell value at `C5`, and `image_count = 1`.
- Workspace-style image confirmed cell generated `write_image` with empty `image_path`; executor returned `operations_written = 0` and warning `缺少 image_path`.

## 5. Legacy / New Path Status

| Function / path | Current state | Default behavior |
| --- | --- | --- |
| `_split_confirmed_cells_for_excel_export` | Still present and still called by `/api/v4/export-confirmed-excel`. | Active for splitting text/image lists, but not used to exclude images from override. |
| `_insert_confirmed_images_into_excel` | Still present. | Default off in the real API because `use_operation_image_export = True`; only runs if that variable becomes false. |
| New confirmed override path | Active. | API passes all `confirmed_cells` into `_override_operations_with_confirmed_cells`. |
| New image operation path | Active but incomplete for workspace payload. | Generates `write_image`, but does not materialize `image.data_url` to an `image_path`. |
| Duplicate image insertion risk | Low by default. | Since legacy fallback is disabled, current default does not insert both legacy and operation images. Risk returns if `use_operation_image_export` is flipped false while image operations remain in the operation list. |

## 6. Known Risks

1. Workspace image export is currently broken in the new operation path.
   - Frontend confirmed image item shape: `field_type: "image"` plus nested `image.data_url`.
   - `_confirmed_operation_from_item` only copies top-level `image_path`, `image_data`, and `image_base64`.
   - `v4_excel_executor` only reads `image_path`.

2. Legacy image helpers are conditionally retained.
   - They are not dead code, but they are currently default-off in the real API.
   - `_insert_confirmed_images_into_excel` is the only current code that knows how to decode `image.data_url`.

3. `image_export_summary` may under-report attempted image export.
   - With operation image export enabled, the API returns a zeroed summary even when image confirmed cells were submitted and then skipped by executor warnings.

4. `export_readback_check` audits only `text_confirmed_cells`.
   - Current readback does not verify operation-based image insertion.

5. `default_profile` cannot complete real API export unless an active current profile with a bound template is present.
   - The default profile has no `template_file_path`; non-default profiles have bound templates.

## 7. Recommended Next Phase

Recommended next phase: V4-EXPORT-FIX109B.

Scope should be narrow:
- Decide one canonical image payload for the operation path.
- Convert workspace `image.data_url` into a temporary `image_path` before executor, or extend executor to accept and materialize image data.
- Add image readback/audit summary for operation-based image export.
- Keep legacy fallback disabled by default unless explicitly used as a compatibility mode.

## FIX109A Result

PARTIAL

Reason:
- Normal fields: PASS.
- Dynamic table fields: PASS.
- Executor support matrix: PASS.
- Real API route uses the new override/executor path: PASS.
- Workspace image field export through current confirmed cell payload: FAIL.
