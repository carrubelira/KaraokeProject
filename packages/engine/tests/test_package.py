"""Packages become manifests of blobs (contracts v2), and v3 packages migrate."""

import json
import shutil
from pathlib import Path

import pytest

from karaoke_contracts import Lyrics, Manifest, canonical_json
from karaoke_contracts.cas import BlobStore, sha256_file
from karaoke_engine.audio import convert_package
from karaoke_engine.demo import synthesize_package_audio
from karaoke_engine.package import build_manifest, manifest_sha, with_lyrics

pytestmark = pytest.mark.usefixtures("ffmpeg")

DEMO = Path(__file__).resolve().parents[3] / "fixtures" / "packages" / "demo-sintetico"


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    package = tmp_path / "demo"
    shutil.copytree(DEMO, package)
    synthesize_package_audio(package)
    return package


def test_a_v3_package_migrates_to_a_manifest(demo: Path, tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "cas")

    manifest, blob = build_manifest(demo, store)

    assert blob.sha256 == manifest_sha(manifest)
    assert store.verify(blob.sha256)
    assert Manifest.model_validate_json(store.read_bytes(blob.sha256)) == manifest
    assert {t.kind for t in manifest.tracks} == {"instrumental", "vocals", "lyrics"}
    for track in manifest.tracks:
        assert store.verify(track.blob.sha256)
        assert track.blob.size == store.path(track.blob.sha256).stat().st_size
    vocals = manifest.track("vocals")
    assert vocals is not None
    assert vocals.audio is not None
    assert vocals.audio.preskip > 0
    assert vocals.audio.gain_db == 0.0, "the synthetic demo is not levelled"
    lyrics = Lyrics.model_validate_json(store.read_bytes(manifest.track("lyrics").blob.sha256))  # type: ignore[union-attr]
    assert lyrics.lines
    assert lyrics.language == manifest.language
    assert manifest.content_id == "demo-sintetico" or manifest.content_id


def test_an_opus_package_keeps_its_gain(demo: Path, tmp_path: Path) -> None:
    refs = convert_package(demo)
    manifest, _ = build_manifest(demo, BlobStore(tmp_path / "cas"))
    instrumental = manifest.track("instrumental")
    assert instrumental is not None
    assert instrumental.audio is not None
    assert instrumental.audio.gain_db == refs.gain_db
    # Stored as encoded: no second lossy pass.
    assert instrumental.blob.sha256 == sha256_file(demo / "instrumental.opus")


def test_a_lyrics_edit_only_adds_one_blob(demo: Path, tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "cas")
    manifest, _ = build_manifest(demo, store)
    before = set(store.all())
    lyrics = Lyrics.model_validate_json(store.read_bytes(manifest.track("lyrics").blob.sha256))  # type: ignore[union-attr]
    lyrics = lyrics.model_copy(update={"edited": True})

    edited, blob = with_lyrics(manifest, lyrics, store)

    assert edited.version == 2
    assert edited.parent == manifest_sha(manifest)
    assert set(store.all()) - before == {blob.sha256, edited.track("lyrics").blob.sha256}  # type: ignore[union-attr]
    assert edited.track("vocals") == manifest.track("vocals")


def test_canonical_json_is_stable(demo: Path, tmp_path: Path) -> None:
    manifest, _ = build_manifest(demo, BlobStore(tmp_path / "cas"))
    again = Manifest.model_validate(json.loads(canonical_json(manifest)))
    assert canonical_json(again) == canonical_json(manifest)


def test_karaoke_package_command(
    demo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from karaoke_engine.cli import main

    assert main(["package", str(demo), "--store", str(tmp_path / "cas"), "--id", "demo"]) == 0
    assert capsys.readouterr().out.startswith("demo v1: ")
