# Project Status

Current branch: `v4-stage2-middle-layer-replace`

Current phase: `Stage2`

Current state:

- Old Workspace has been deleted.
- Old export chain has been retired.
- New Workspace has been established.
- The real page flow is wired through the Stage2 chain.

Current real page flow:

```text
Profile
-> AI Parse
-> confirmedOrderObject
-> export-pipeline-excel
```

Active Stage2 endpoint path:

- `GET /api/v4/template-profiles`
- `POST /api/v4/parse-chat-run-pipeline`
- `POST /api/v4/export-pipeline-excel`

Retired old runtime paths:

- `confirmed_cells`
- `export-confirmed-excel`
- `parse-chat-export-excel`
- `core-pipeline/export-excel`

Known blocker:

- `processed_operations` is empty during export.

Stage2 config rebuild:

- Stage2 configuration page rebuild has started.
- Old configuration chain is no longer the main configuration source for the new middle layer.
- Stage2 configuration will be stored independently in `data/stage2_config_profiles.json`.
- New config page entry: `/v4-stage2-config`.
- New config API: `/api/v4/stage2-config/*`.
- Stage2 Config has completed its independent skeleton.
- Current focus is data source observation.
- Old configuration chain remains frozen and is only a read-only audit object.
- Old configuration chain is not the new configuration main chain.

Latest observed real flow result:

- Page opens.
- Profile dropdown loads.
- AI Parse succeeds.
- Workspace displays `3 fields ready`.
- `confirmedOrderObject` is generated.
- Export request goes to `/api/v4/export-pipeline-excel`.
- Export returns `success=false`, `stage=processed_operations`.
