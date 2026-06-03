# Current Task

Task:

`STAGE2_CONFIG_DOCUMENTMODEL_BIND_01`

Status:

- Stage2 Config is adding a Source Summary observation layer.

Purpose:

- Confirm current data sources available before binding DocumentModel into the new configuration chain.
- Observe `stage2_config_profiles`.
- Observe old `template_profiles` as a read-only audit source.
- Observe `v4_template_cache` rule summaries.

Scope:

- Read-only display.
- No old configuration bridge.
- No Workspace changes.
- No export changes.
- No old chain restoration.

New observation API:

- `/api/v4/stage2-config/source-summary`
