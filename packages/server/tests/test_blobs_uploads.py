import hashlib
from pathlib import Path

from .conftest import Clients


def test_blobs_round_trip_with_range_and_hash_check(clients: Clients) -> None:
    data = bytes(range(256)) * 100
    sha = hashlib.sha256(data).hexdigest()
    _, worker = clients.enrol("worker")
    assert worker.put(f"/api/blobs/{'0' * 64}", content=data).status_code == 422
    stored = worker.put(f"/api/blobs/{sha}", content=data)
    assert stored.json() == {"sha256": sha, "size": len(data)}
    op = clients.operator()
    assert op.get(f"/api/blobs/{sha}").content == data
    part = op.get(f"/api/blobs/{sha}", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206
    assert part.content == data[100:200]
    assert op.get(f"/api/blobs/{'1' * 64}").status_code == 404
    assert clients.client().get(f"/api/blobs/{sha}").status_code == 401


def test_only_nodes_on_the_same_machine_read_by_path(clients: Clients) -> None:
    sha = clients.services.store.put_bytes(b"hello", "text/plain").sha256
    _, far = clients.enrol("worker", name="far")
    assert far.get(f"/api/blobs/{sha}/local").status_code == 403
    _, near = clients.enrol("worker", name="near", same_host_as_server=True)
    path = near.get(f"/api/blobs/{sha}/local").json()["path"]
    assert Path(path).read_bytes() == b"hello"


def test_uploads_resume_from_the_offset(clients: Clients) -> None:
    op = clients.operator()
    data = b"x" * 5000 + b"y" * 5000
    upload = op.post("/api/uploads", json={"filename": "Canción.mp3", "size": len(data)}).json()
    url = f"/api/uploads/{upload['id']}"
    assert (
        op.patch(url, content=data[:4000], headers={"Upload-Offset": "0"}).json()["offset"] == 4000
    )
    # A retry of a chunk that already arrived is refused with where to go on from.
    stale = op.patch(url, content=data[:4000], headers={"Upload-Offset": "0"})
    assert stale.status_code == 409
    assert stale.json()["offset"] == 4000
    assert op.head(url).headers["upload-offset"] == "4000"
    done = op.patch(url, content=data[4000:], headers={"Upload-Offset": "4000"}).json()
    assert done["blob"] == hashlib.sha256(data).hexdigest()
    assert clients.services.store.read_bytes(done["blob"]) == data
    too_big = op.post("/api/uploads", json={"filename": "a.mp3", "size": 10**13})
    assert too_big.status_code == 413
