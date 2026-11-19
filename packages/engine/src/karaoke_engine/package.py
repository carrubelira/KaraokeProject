"""From a package folder to a manifest of blobs (contracts v2, plan v4 §5).

`make_package` still writes a working folder (karaoke.json, the stems, the video); this step
stores each track by its hash and writes the manifest that names them. It is also the migrator
for v3 packages: their AAC stems (already levelled) are re-encoded to Opus with no gain, and
their WAV stems (the synthetic demo) too.
"""

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from karaoke_contracts import (
    AudioInfo,
    Blob,
    KaraokeDoc,
    Lyrics,
    Manifest,
    Track,
    VideoInfo,
    canonical_json,
    load_doc,
    resolve_media,
    slug,
)
from karaoke_contracts.cas import BlobStore, sha256_bytes
from karaoke_contracts.manifest import LyricsProvenance, Singer
from karaoke_engine.audio import BITRATES, encode_opus, opus_preskip, probe
from karaoke_engine.video.media import probe_video

MANIFEST_TYPE = "application/vnd.karaoke.manifest+json"
LYRICS_TYPE = "application/vnd.karaoke.lyrics+json"
OPUS_TYPE = "audio/ogg; codecs=opus"
PLAYER_CODECS = {"h264": "h264", "hevc": "hevc", "av1": "av1"}


def lyrics_of(doc: KaraokeDoc) -> Lyrics:
    provenance = doc.provenance.model_dump(mode="json")
    return Lyrics(
        language=doc.language,
        singers=[Singer.model_validate(s.model_dump(mode="json")) for s in doc.singers],
        lines=doc.lines,
        provenance=LyricsProvenance.model_validate(
            {k: provenance[k] for k in LyricsProvenance.model_fields if k in provenance}
        ),
        edited=doc.edited,
    )


def store_manifest(store: BlobStore, manifest: Manifest) -> Blob:
    return store.put_bytes(canonical_json(manifest), MANIFEST_TYPE)


def manifest_sha(manifest: Manifest) -> str:
    return sha256_bytes(canonical_json(manifest))


def build_manifest(
    package_dir: Path,
    store: BlobStore,
    *,
    content_id: str | None = None,
    previous: Manifest | None = None,
    created_at: datetime | None = None,
) -> tuple[Manifest, Blob]:
    """Stores every track of the package and its manifest; returns both."""
    doc = load_doc(package_dir / "karaoke.json")
    tracks: list[Track] = []
    with tempfile.TemporaryDirectory() as tmp:
        roles = [("instrumental", doc.audio.instrumental), ("vocals", doc.audio.vocals)]
        for role, ref in roles:
            if ref is None:
                continue
            tracks.append(
                _audio_track(role, resolve_media(package_dir, ref), doc, store, Path(tmp))
            )
        if doc.video is not None:
            seen: set[tuple[int, int, str]] = set()
            for index, ref in enumerate((doc.video.background, doc.video.master)):
                if ref is None:
                    continue
                track = _video_track(
                    resolve_media(package_dir, ref), store, Path(tmp) / f"v{index}.mp4"
                )
                assert track.video is not None
                key = (track.video.width, track.video.height, track.video.codec)
                if key not in seen:
                    seen.add(key)
                    tracks.append(track)
    lyrics = store.put_bytes(canonical_json(lyrics_of(doc)), LYRICS_TYPE)
    tracks.append(Track(kind="lyrics", blob=lyrics, duration=doc.duration))
    if doc.cover is not None:
        tracks.append(
            Track(
                kind="cover",
                blob=store.put_file(resolve_media(package_dir, doc.cover), "image/jpeg"),
            )
        )
    manifest = Manifest(
        content_id=content_id or (previous.content_id if previous else slug(doc.title)),
        version=previous.version + 1 if previous else 1,
        parent=manifest_sha(previous) if previous else None,
        created_at=created_at or datetime.now(UTC),
        title=doc.title,
        artist=doc.artist,
        language=doc.language,
        duration=doc.duration,
        tracks=tracks,
    )
    return manifest, store_manifest(store, manifest)


def with_lyrics(
    manifest: Manifest, lyrics: Lyrics, store: BlobStore, created_at: datetime | None = None
) -> tuple[Manifest, Blob]:
    """A new version of a manifest whose lyrics changed (an edit): only that blob is new."""
    blob = store.put_bytes(canonical_json(lyrics), LYRICS_TYPE)
    tracks = [
        t if t.kind != "lyrics" else t.model_copy(update={"blob": blob}) for t in manifest.tracks
    ]
    new = manifest.model_copy(
        update={
            "version": manifest.version + 1,
            "parent": manifest_sha(manifest),
            "created_at": created_at or datetime.now(UTC),
            "tracks": tracks,
        }
    )
    new = Manifest.model_validate(new.model_dump(mode="json"))
    return new, store_manifest(store, new)


def _audio_track(role: str, path: Path, doc: KaraokeDoc, store: BlobStore, tmp: Path) -> Track:
    info = probe(path)
    # A v3 m4a was levelled when encoded; a 1.3.0 package says its gain.
    gain = doc.audio.gain_db or 0.0
    if not (info.codec == "opus" and path.suffix == ".opus"):
        path = encode_opus(path, tmp / f"{role}.opus", BITRATES[role])
        info = probe(path)
    blob = store.put_file(path, OPUS_TYPE)
    return Track(
        kind=role,  # type: ignore[arg-type]
        blob=blob,
        duration=round(info.duration, 6),
        audio=AudioInfo(
            channels=min(info.channels, 2),
            preskip=opus_preskip(path),
            gain_db=gain,
            loudness_lufs=doc.audio.loudness_lufs,
        ),
    )


def _video_track(path: Path, store: BlobStore, out: Path) -> Track:
    """The video without its sound (the stems carry it), in a codec players decode."""
    info = probe_video(path)
    if info is None:
        raise ValueError(f"{path} has no video")
    codec = (
        ["-c:v", "copy"]
        if info.codec in PLAYER_CODECS
        else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(path), "-map", "0:v:0", "-an",
         *codec, "-movflags", "+faststart", str(out)],
        check=True,
    )  # fmt: skip
    info = probe_video(out)
    assert info is not None
    return Track(
        kind="video",
        blob=store.put_file(out, "video/mp4"),
        duration=round(info.duration, 6) or None,
        video=VideoInfo(
            codec=PLAYER_CODECS[info.codec],  # type: ignore[arg-type]
            width=info.width,
            height=info.height,
            fps=round(info.fps, 3),
        ),
    )
