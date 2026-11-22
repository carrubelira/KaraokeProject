//! Downloads songs ahead, on its own thread: the one on first, then the next ones.

use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::mpsc::{Receiver, Sender};
use std::thread;

use kp_cache::{BlobCache, Needs, Preparer, Source};
use kp_net::Server;
use kp_proto::{ContentCache, Manifest, QueueItem};

/// Blobs from the server: its disk when it shares this machine's, else HTTP with `Range`.
pub struct ServerSource {
    pub server: Server,
    pub same_host: bool,
}

impl Source for ServerSource {
    fn fetch(
        &self,
        sha256: &str,
        offset: u64,
        sink: &mut dyn FnMut(&[u8]) -> std::io::Result<()>,
    ) -> Result<bool, String> {
        self.server
            .get_blob(sha256, offset, sink)
            .map(|(_, partial)| partial || offset == 0)
            .map_err(|e| e.to_string())
    }

    fn local(&self, sha256: &str) -> Option<PathBuf> {
        if !self.same_host {
            return None;
        }
        self.server.local_path(sha256).map(PathBuf::from)
    }
}

pub enum Report {
    Cache(ContentCache),
    Ready {
        item: QueueItem,
        manifest: Box<Manifest>,
        manifest_sha: String,
    },
}

/// The manifest a queue item plays: the pinned one, else the song's current version.
fn manifest_of(server: &Server, item: &QueueItem) -> Result<String, String> {
    if let Some(sha) = &item.manifest {
        return Ok(sha.clone());
    }
    let content: serde_json::Value = server
        .get_json(&format!("/api/contents/{}", item.content_id))
        .map_err(|e| e.to_string())?;
    content["manifest"]
        .as_str()
        .map(str::to_string)
        .ok_or_else(|| "the song has no manifest".into())
}

pub fn spawn(
    cache: BlobCache,
    source: ServerSource,
    needs: Needs,
    wants: Receiver<Vec<QueueItem>>,
    reports: Sender<Report>,
) -> thread::JoinHandle<()> {
    thread::Builder::new()
        .name("downloads".into())
        .spawn(move || {
            let mut done: HashSet<(String, String)> = HashSet::new();
            while let Ok(mut list) = wants.recv() {
                // Only the latest wish counts.
                while let Ok(newer) = wants.try_recv() {
                    list = newer;
                }
                let server = source.server.clone();
                let preparer = Preparer {
                    cache: &cache,
                    source: &source,
                    needs: needs.clone(),
                };
                for item in list {
                    let sha = match manifest_of(&server, &item) {
                        Ok(sha) => sha,
                        Err(error) => {
                            log::warn!("{}: {error}", item.content_id);
                            continue;
                        }
                    };
                    let key = (item.content_id.clone(), sha.clone());
                    if done.contains(&key) {
                        continue;
                    }
                    let mut report = |update: ContentCache| {
                        let _ = reports.send(Report::Cache(update));
                    };
                    match preparer.prepare(&item.content_id, &sha, &mut report) {
                        Ok(manifest) => {
                            done.insert(key);
                            let _ = reports.send(Report::Ready {
                                item,
                                manifest: Box::new(manifest),
                                manifest_sha: sha,
                            });
                        }
                        Err(error) => log::warn!("{}: {error}", item.content_id),
                    }
                }
            }
        })
        .expect("the download thread starts")
}
