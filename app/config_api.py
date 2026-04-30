from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path

from app.config import BASE_DIR

router = APIRouter()

CONFIG_DIR = BASE_DIR / "configs"
CONFIG_DIR.mkdir(exist_ok=True)


class ConfigItem(BaseModel):
    field: str
    cell: str
    type: str
    components: list | None = None


class ConfigRequest(BaseModel):
    template_file: str
    fields: list[ConfigItem]


@router.post("/save-config")
def save_config(req: ConfigRequest):

    config_data = {
        "template_file": req.template_file,
        "fields": [item.dict() for item in req.fields]
    }

    config_path = CONFIG_DIR / "custom.json"

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    return {"message": "配置保存成功"}


@router.get("/get-config")
def get_config():

    config_path = CONFIG_DIR / "custom.json"

    if not config_path.exists():
        return {"fields": []}

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
