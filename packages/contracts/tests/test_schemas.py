import json
from pathlib import Path

from karaoke_contracts.schema_export import export_schemas

COMMITTED = Path(__file__).resolve().parents[3] / "schemas"


def test_committed_schemas_are_up_to_date(tmp_path: Path) -> None:
    written = export_schemas(tmp_path)

    assert sorted(p.name for p in written) == sorted(
        f"{name}.schema.json"
        for name in (
            "karaoke",
            "theme",
            "manifest",
            "lyrics",
            "enrollment",
            "heartbeat",
            "lease",
            "queue",
            "session",
            "screen-hello",
            "screen-status",
            "screen-config",
            "audio-status",
            "audio-config",
        )
    )
    for path in written:
        assert path.read_bytes() == (COMMITTED / path.name).read_bytes(), (
            f"{path.name} is stale: run `make contracts`"
        )


def test_karaoke_schema_marks_defaulted_fields_required(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    schema = json.loads((tmp_path / "karaoke.schema.json").read_text(encoding="utf-8"))

    assert {"schema_version", "singers", "lines", "edited"} <= set(schema["required"])
    assert schema["$id"].endswith("/schemas/karaoke.schema.json")


def test_properties_carry_no_titles(tmp_path: Path) -> None:
    # Per-field titles make json2ts emit one type alias per field (Start1, Id2...).
    export_schemas(tmp_path)
    schema = json.loads((tmp_path / "karaoke.schema.json").read_text(encoding="utf-8"))

    word = schema["$defs"]["Word"]
    assert word["title"] == "Word"
    assert all("title" not in prop for prop in word["properties"].values())


def test_schemas_do_not_spell_out_additional_properties(tmp_path: Path) -> None:
    # "additionalProperties": true is the JSON Schema default; written out, it makes json2ts
    # add an index signature to every TS interface.
    export_schemas(tmp_path)

    # The strict v2 contracts say false on purpose (unknown fields are an error).
    for path in tmp_path.glob("*.schema.json"):
        assert '"additionalProperties": true' not in path.read_text(encoding="utf-8"), path.name
