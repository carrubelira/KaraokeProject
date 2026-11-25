"""Writes the JSON Schemas in schemas/ from the pydantic models (run via `make contracts`)."""

import json
import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from karaoke_contracts.control import AudioConfig, Queue
from karaoke_contracts.doc import KaraokeDoc
from karaoke_contracts.manifest import Lyrics, Manifest
from karaoke_contracts.nodes import Enrollment, Heartbeat, Lease
from karaoke_contracts.stage import AudioStatus, ScreenConfig, ScreenHello, ScreenStatus, Session
from karaoke_contracts.theme import Theme

SCHEMA_BASE_ID = "https://github.com/gaelfernandez1/KaraokeProject/schemas/"
MODELS: dict[str, type[BaseModel]] = {
    "karaoke": KaraokeDoc,
    "theme": Theme,
    "manifest": Manifest,
    "lyrics": Lyrics,
    "enrollment": Enrollment,
    "heartbeat": Heartbeat,
    "lease": Lease,
    "queue": Queue,
    "session": Session,
    "screen-hello": ScreenHello,
    "screen-status": ScreenStatus,
    "screen-config": ScreenConfig,
    "audio-status": AudioStatus,
    "audio-config": AudioConfig,
}


class _ModelTitlesOnly(GenerateJsonSchema):
    """Keeps titles on models but not on fields, so TS generators emit clean interfaces."""

    def field_title_should_be_set(self, schema: object) -> bool:
        return False

    def model_schema(self, schema: core_schema.ModelSchema) -> JsonSchemaValue:
        # extra="allow" writes "additionalProperties": true, which is already the JSON Schema
        # default; dropping it keeps json2ts from adding index signatures.
        json_schema = super().model_schema(schema)
        if json_schema.get("additionalProperties") is True:
            del json_schema["additionalProperties"]
        return json_schema

    def dict_schema(self, schema: core_schema.DictSchema) -> JsonSchemaValue:
        # dict[str, Any] says the same default; json2ts would turn it into `[k: string]: unknown`
        # anyway, so it goes for the same reason.
        json_schema = super().dict_schema(schema)
        if json_schema.get("additionalProperties") is True:
            del json_schema["additionalProperties"]
        return json_schema


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in MODELS.items():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{SCHEMA_BASE_ID}{name}.schema.json",
            **model.model_json_schema(mode="serialization", schema_generator=_ModelTitlesOnly),
        }
        path = out_dir / f"{name}.schema.json"
        text = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")  # LF on Windows too
        written.append(path)
    return written


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("schemas")
    for path in export_schemas(out_dir):
        print(path)


if __name__ == "__main__":
    main()
