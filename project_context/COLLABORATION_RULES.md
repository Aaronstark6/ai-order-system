# Collaboration Rules

Roles:

- ChatGPT = brain.
- Codex / Solo = hands.

Operating style:

- PowerShell-first audit.
- Audit -> locate -> modify.
- No guessing.
- Use evidence from files, logs, commands, and runtime responses.
- Report concrete command results.

Architecture rules:

- No dual main chain.
- No compatibility-style patching.
- Do not maintain the old chain beside the new chain.
- If an old chain blocks development, it may be deleted.

Stage2 principles:

- Do not revive old Workspace.
- Do not revive `confirmed_cells`.
- Do not revive `export-confirmed-excel`.
- Keep `confirmedOrderObject` as the source of truth.
- Keep Stage2 as the only production export target.

Project principle:

```text
不破不立
破而后立
```

Practical meaning:

- Remove confusing old runtime paths before rebuilding cleanly.
- Prefer a single clear chain over compatibility layers.
- Confirm the real failure point before code changes.
