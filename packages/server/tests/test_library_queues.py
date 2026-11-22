import os
import time
from datetime import UTC, datetime, timedelta

from karaoke_server.services import Services

from .conftest import Clients


def test_versions_trash_and_restore(clients: Clients, demo_manifest: str) -> None:
    library = clients.services.library
    first = library.register(demo_manifest)
    assert (first["id"], first["version"]) == ("demo", 1)
    # The same song made again becomes version 2 of it.
    second = library.register(demo_manifest)
    assert second["version"] == 2
    assert second["manifest"] != demo_manifest
    op = clients.operator()
    assert [v["version"] for v in op.get("/api/contents/demo/versions").json()] == [2, 1]
    assert op.delete("/api/contents/demo").status_code == 204
    assert op.get("/api/contents").json() == []
    assert [c["id"] for c in op.get("/api/contents?trash=true").json()] == ["demo"]
    assert op.post("/api/contents/demo/restore").json()["deleted_at"] is None


def test_gc_keeps_what_manifests_need(
    clients: Clients, services: Services, demo_manifest: str
) -> None:
    services.library.register(demo_manifest)
    loose = services.store.put_bytes(b"nobody needs me", "text/plain").sha256
    old = time.time() - 7200
    os.utime(services.store.path(loose), (old, old))
    fresh = services.store.put_bytes(b"just uploaded", "text/plain").sha256
    report = services.library.collect()
    assert report.deleted == 1
    assert not services.store.has(loose)
    assert services.store.has(fresh)
    assert services.store.has(demo_manifest)
    # Trash older than 30 days is purged, and then its blobs go too.
    services.library.trash("demo")
    month_ago = (datetime.now(UTC) - timedelta(days=31)).isoformat(timespec="seconds")
    services.db.execute("UPDATE contents SET deleted_at = ?", (month_ago,))
    for sha in services.store.all():
        os.utime(services.store.path(sha), (old, old))
    report = services.library.collect()
    assert report.purged_contents == 1
    assert list(services.store.all()) == []


def test_lyrics_edit_makes_a_new_version(clients: Clients, demo_manifest: str) -> None:
    clients.services.library.register(demo_manifest)
    op = clients.operator()
    lyrics = op.get("/api/contents/demo/lyrics").json()
    lyrics["edited"] = True
    lyrics["lines"][0]["words"][0]["text"] = "Ola"
    saved = op.put("/api/contents/demo/lyrics", json={"base": demo_manifest, "lyrics": lyrics})
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 2
    assert op.get("/api/contents/demo/lyrics").json()["lines"][0]["words"][0]["text"] == "Ola"
    stale = op.put("/api/contents/demo/lyrics", json={"base": demo_manifest, "lyrics": lyrics})
    assert stale.status_code == 409


def test_the_queue_starts_empty_and_adding_never_conflicts(
    clients: Clients, demo_manifest: str
) -> None:
    clients.services.library.register(demo_manifest)
    op = clients.operator()
    queue = op.get("/api/stage/queue").json()
    assert (queue["version"], queue["items"]) == (0, [])
    added = op.post(
        "/api/stage/queue/items", json={"items": [{"content_id": "demo", "singer": "Uxía"}]}
    ).json()
    assert added["version"] == 1
    assert added["items"][0]["singer"] == "Uxía"
    # A second console adds at the same time from version 0: it still lands, at the end.
    both = op.post("/api/stage/queue/items", json={"items": [{"content_id": "demo"}]}).json()
    assert [i["singer"] for i in both["items"]] == ["Uxía", None]
    first = op.post(
        "/api/stage/queue/items",
        json={"items": [{"content_id": "demo", "singer": "Brais"}], "first": True},
    ).json()
    assert first["items"][0]["singer"] == "Brais"
    unknown = op.post("/api/stage/queue/items", json={"items": [{"content_id": "nope"}]})
    assert unknown.status_code == 404


def test_rewriting_the_queue_refuses_a_newer_version(clients: Clients, demo_manifest: str) -> None:
    clients.services.library.register(demo_manifest)
    op = clients.operator()
    queue = op.get("/api/stage/queue").json()
    queue["items"] = [{"id": "i1", "content_id": "demo", "manifest": None, "start": None,
                       "end": None, "semitones": 0, "singer": "Uxía"}]  # fmt: skip
    saved = op.put("/api/stage/queue", json=queue).json()
    assert saved["version"] == 1
    # Another console still holds version 0.
    conflict = op.put("/api/stage/queue", json=queue)
    assert conflict.status_code == 409
    assert conflict.json()["current"]["version"] == 1
    queue["version"] = 1
    queue["items"][0]["content_id"] = "missing"
    assert op.put("/api/stage/queue", json=queue).status_code == 422
