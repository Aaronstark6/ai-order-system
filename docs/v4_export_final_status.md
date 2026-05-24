# V4 Export Final Status Audit

Audit ID: V4-EXPORT-FIX109A / V4-EXPORT-FIX109B

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
| Confirmed Cells: workspace image fields | Supported | FIX109B materializes workspace `image.data_url` to a temporary `image_path`, then emits `write_image` for executor image insertion. |
| Operations Pipeline | Supported | Pipeline normalizes/finalizes op types and preserves supported ops. |
| Executor | Supported for all declared op types | `SUPPORTED_OP_TYPES = {"write_text", "write_number", "write_multiline", "write_table_cell", "write_block", "write_image"}`. |
| Real API Export | Supported | `/api/v4/export-confirmed-excel` uses override + executor; workspace image payload now becomes executable `write_image`. |

## 2. Link Status Table

| Link | Expected path | Status | Notes |
| --- | --- | --- | --- |
| Normal field export | `confirmed_cells(text)` -> `_override_operations_with_confirmed_cells` -> `_confirmed_operation_from_item` -> `write_text` / existing op override -> `execute_processed_operations_to_excel` -> Excel | PASS | Confirmed text values override matching operations or add new `write_text` operations. |
| Dynamic table export | dynamic table confirmed cells -> `write_table_cell` -> `row_offset` / `col_offset` -> executor -> Excel | PASS | Direct executor verification wrote `target_cell=A4,row_offset=1,col_offset=2` to `C5`. |
| Image field export | workspace image field -> `confirmed_cells(image)` -> override -> `_confirmed_operation_from_item` -> `write_image` -> executor -> Excel image insertion | PASS | FIX109B converts workspace `image.data_url` to a temp `image_path`, so executor can insert the image. |
| Real API export | `/api/v4/export-confirmed-excel` -> profile -> feature flags -> override -> executor -> output file | PASS | API calls override with all `confirmed_cells` and executes the resulting operations. Legacy image fallback remains disabled by `use_operation_image_export = True`. |

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
| `write_image` | Yes | Requires `image_path`, then inserts image at `image_anchor_cell` / `target_cell`. | Reachable from workspace `image.data_url` after FIX109B temp `image_path` materialization, and executable with explicit `image_path`. |

Verification run:
- Direct executor test wrote `write_text`, `write_number`, `write_multiline`, `write_table_cell`, `write_block`, and `write_image` successfully.
- Direct executor output had `operations_written = 6`, table cell value at `C5`, and `image_count = 1`.
- FIX109B workspace-style image confirmed cell generated `write_image` with a temp `image_path`; executor inserted 1 image.

# FIX109B Workspace 图片 data_url 链路修复

## 结果

PASS

## 验证项

data_url_materialized: True
generated_image_path_exists: True
write_image_generated: True
write_text_generated: True
export_success: True
images_count: 1
text_cell_value: FIX109B客户
old_image_insert_skipped: True

## 最终图片链路

workspace image.data_url
→ _materialize_image_data_url_to_temp_file()
→ image_path
→ write_image operation
→ execute_processed_operations_to_excel()
→ Excel image insertion

PASS

## 5. Legacy / New Path Status

| Function / path | Current state | Default behavior |
| --- | --- | --- |
| `_split_confirmed_cells_for_excel_export` | Still present and still called by `/api/v4/export-confirmed-excel`. | Active for splitting text/image lists, but not used to exclude images from override. |
| `_insert_confirmed_images_into_excel` | Still present. | Default off in the real API because `use_operation_image_export = True`; only runs if that variable becomes false. |
| New confirmed override path | Active. | API passes all `confirmed_cells` into `_override_operations_with_confirmed_cells`. |
| New image operation path | Active. | FIX109B materializes `image.data_url` to a temporary `image_path`, then generates executable `write_image`. |
| Duplicate image insertion risk | Low by default. | Since legacy fallback is disabled, current default does not insert both legacy and operation images. Risk returns if `use_operation_image_export` is flipped false while image operations remain in the operation list. |

## 6. Known Risks

1. Temporary image cleanup strategy can be optimized later.
   - FIX109B writes materialized workspace images to a temporary `image_path` under the output temp image area.
   - Verification cleaned its temporary image, but production lifecycle cleanup can be made more explicit in a future housekeeping pass.

2. Legacy image helpers are conditionally retained.
   - They are not dead code, but they are currently default-off in the real API.
   - `_insert_confirmed_images_into_excel` is the only current code that knows how to decode `image.data_url`.

3. `image_export_summary` remains legacy-path oriented.
   - With operation image export enabled, the API returns a zeroed legacy image summary even though images are handled by `write_image`.

4. `export_readback_check` audits only `text_confirmed_cells`.
   - Current readback does not verify operation-based image insertion.

5. `default_profile` cannot complete real API export unless an active current profile with a bound template is present.
   - The default profile has no `template_file_path`; non-default profiles have bound templates.

## 7. Recommended Next Phase

Recommended next phase: V4 Export housekeeping.

Scope should be narrow:
- Document or automate production cleanup for materialized temporary image files.
- Add image readback/audit summary for operation-based image export.
- Keep legacy fallback disabled by default unless explicitly used as a compatibility mode.

## Export Total Result

PASS

Reason:
- Normal fields: PASS.
- Dynamic table fields: PASS.
- Executor support matrix: PASS.
- Real API route uses the new override/executor path: PASS.
- Workspace image field export through current confirmed cell payload: PASS after FIX109B.

# FIX110A Real Business E2E Regression

## Result

PASS

## Real API Path

`/api/v4/export-confirmed-excel` was exercised through the real route handler with:

- profile_id: `软胶囊`
- template_id: `v4/system_templates/软胶囊_软胶囊爆珠模板_20260523_181128_191d0554.xlsx`
- confirmed_cells_count: 9
- image payload shape: `image.data_url`
- feature flags: `image_fields=True`, `dynamic_tables=True`, `advanced_write_modes=True`, `option_write_enhancement=True`, `format_protection=True`, `formula_protection=True`, `export_readback_check=True`

## Verified Output

```text
normal_fields: PASS
dynamic_tables: PASS
image_export: PASS
real_api_export: PASS

images_count: 1
text_cells_verified: {"C4": "DOC-FIX110A", "F4": "20260524", "C5": "FIX110A客户", "F5": "品牌客户", "C6": "8888", "F6": "Alice"}
table_cells_verified: {"B10": "其他可选包装：动态表-R1", "B11": "其他可选包装：动态表-R2"}

result: PASS
```

## Blocker Closed

FIX110A found and minimally fixed a real API blocker in export readback: `_build_export_readback_audit()` now uses the existing `_confirmed_config_lookup_from_profile(profile)` helper. No legacy image insertion default was restored.
