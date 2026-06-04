from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


STAGE2_CONFIG_SCHEMA_VERSION = "stage2_config_v1"


@dataclass
class Stage2ConfigField:
    field_key: str
    field_label: str
    field_type: str = "text"
    intent_type: str = ""
    write_mode: str = ""
    source_node_id: str = ""
    semantic_summary: dict[str, Any] = field(default_factory=dict)
    visual_logic: dict[str, Any] = field(default_factory=dict)
    condition_logic: dict[str, Any] = field(default_factory=dict)
    choice_logic: dict[str, Any] = field(default_factory=dict)
    table_logic: dict[str, Any] = field(default_factory=dict)
    runtime_policy: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    display_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage2ConfigProfile:
    profile_id: str
    profile_name: str
    schema_version: str = STAGE2_CONFIG_SCHEMA_VERSION
    document_model_source: dict[str, Any] = field(default_factory=dict)
    semantic_workspace_schema: dict[str, Any] = field(default_factory=dict)
    workspace_fields: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_empty_stage2_config_profile(profile_id: str, profile_name: str) -> dict[str, Any]:
    return Stage2ConfigProfile(
        profile_id=str(profile_id or "").strip(),
        profile_name=str(profile_name or "").strip(),
        metadata={
            "created_by": "stage2_config",
            "status": "empty",
        },
    ).to_dict()
