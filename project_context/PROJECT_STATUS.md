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

Latest observed real flow result:

- Page opens.
- Profile dropdown loads.
- AI Parse succeeds.
- Workspace displays `3 fields ready`.
- `confirmedOrderObject` is generated.
- Export request goes to `/api/v4/export-pipeline-excel`.
- Export returns `success=false`, `stage=processed_operations`.
