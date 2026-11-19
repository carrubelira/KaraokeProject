//! The player plays only what it has on disk and has checked (plan v4 §6).
//!
//! [`BlobCache`] keeps blobs by SHA-256 like the server's store; [`Preparer`] takes a song from
//! `absent` to `ready`: its manifest, then the tracks this machine needs (both stems, the
//! lyrics, the video that fits its screens), resuming partial downloads and checking every hash.
//! Where the blobs come from is a [`Source`]: the server over HTTP, or its own disk when the
//! player runs on the server's machine.

use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};

use kp_proto::{CacheState, ContentCache, Manifest, TrackKind, VideoCodec};
use sha2::{Digest, Sha256};

#[derive(Debug, thiserror::Error)]
pub enum CacheError {
    #[error("{0}")]
    Io(#[from] io::Error),
    #[error("blob {0} does not match its hash")]
    Corrupt(String),
    #[error("could not fetch {sha}: {message}")]
    Fetch { sha: String, message: String },
    #[error("bad manifest: {0}")]
    Manifest(String),
}

/// Where blobs come from.
pub trait Source: Send + Sync {
    /// Streams the blob from byte `offset` on into `sink`; returns whether the source honoured
    /// the offset (false: it started from 0).
    fn fetch(
        &self,
        sha256: &str,
        offset: u64,
        sink: &mut dyn FnMut(&[u8]) -> io::Result<()>,
    ) -> Result<bool, String>;
    /// A path to the blob on this disk, when the source shares it.
    fn local(&self, _sha256: &str) -> Option<PathBuf> {
        None
    }
}

pub fn sha256_file(path: &Path) -> io::Result<String> {
    let mut file = File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0u8; 1 << 16];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
    }
    Ok(hex::encode(digest.finalize()))
}

#[derive(Clone, Debug)]
pub struct BlobCache {
    root: PathBuf,
}

impl BlobCache {
    pub fn new(root: impl Into<PathBuf>) -> io::Result<Self> {
        let root = root.into();
        fs::create_dir_all(root.join("tmp"))?;
        Ok(Self { root })
    }

    pub fn path(&self, sha256: &str) -> PathBuf {
        self.root.join(&sha256[..2]).join(&sha256[2..])
    }

    pub fn has(&self, sha256: &str) -> bool {
        self.path(sha256).is_file()
    }

    fn partial(&self, sha256: &str) -> PathBuf {
        self.root.join("tmp").join(format!("{sha256}.part"))
    }

    /// Brings a blob in from `source` (resuming), checks it and moves it into place.
    /// `progress` gets the bytes received so far.
    pub fn fetch(
        &self,
        source: &dyn Source,
        sha256: &str,
        progress: &mut dyn FnMut(u64),
    ) -> Result<PathBuf, CacheError> {
        let dest = self.path(sha256);
        if dest.is_file() {
            return Ok(dest);
        }
        if let Some(local) = source.local(sha256)
            && sha256_file(&local)? == sha256
        {
            return Ok(local);
        }
        let partial = self.partial(sha256);
        for _ in 0..3 {
            let have = partial.metadata().map(|m| m.len()).unwrap_or(0);
            let mut file = OpenOptions::new().create(true).append(true).open(&partial)?;
            let mut received = have;
            let honoured = source
                .fetch(sha256, have, &mut |chunk| {
                    file.write_all(chunk)?;
                    received += chunk.len() as u64;
                    progress(received);
                    Ok(())
                })
                .map_err(|message| CacheError::Fetch {
                    sha: sha256.into(),
                    message,
                })?;
            drop(file);
            if !honoured && have > 0 {
                // The source sent it from the start after what we had: keep only its bytes.
                let bytes = fs::read(&partial)?;
                fs::write(&partial, &bytes[have as usize..])?;
            }
            if sha256_file(&partial)? == sha256 {
                fs::create_dir_all(dest.parent().expect("blob paths have a parent"))?;
                fs::rename(&partial, &dest)?;
                return Ok(dest);
            }
            fs::remove_file(&partial)?;
        }
        Err(CacheError::Corrupt(sha256.into()))
    }

    pub fn read(&self, sha256: &str) -> io::Result<Vec<u8>> {
        fs::read(self.path(sha256))
    }

    /// Deletes blobs not in `keep`, oldest first, until the cache is under `limit` bytes.
    pub fn trim(&self, keep: &[String], limit: u64) -> io::Result<u64> {
        let mut blobs = Vec::new();
        let mut total = 0;
        for folder in fs::read_dir(&self.root)? {
            let folder = folder?;
            if folder.file_name().len() != 2 {
                continue;
            }
            for file in fs::read_dir(folder.path())? {
                let file = file?;
                let meta = file.metadata()?;
                total += meta.len();
                let sha = format!(
                    "{}{}",
                    folder.file_name().to_string_lossy(),
                    file.file_name().to_string_lossy()
                );
                blobs.push((meta.modified()?, meta.len(), sha, file.path()));
            }
        }
        blobs.sort();
        let mut freed = 0;
        for (_, size, sha, path) in blobs {
            if total - freed <= limit {
                break;
            }
            if keep.contains(&sha) {
                continue;
            }
            fs::remove_file(path)?;
            freed += size;
        }
        Ok(freed)
    }
}

/// What this machine needs of a song.
#[derive(Clone, Debug)]
pub struct Needs {
    /// Tallest screen the video is for.
    pub screen_height: u32,
    pub decoders: Vec<VideoCodec>,
    pub video: bool,
}

impl Default for Needs {
    fn default() -> Self {
        Self {
            screen_height: 1080,
            decoders: vec![VideoCodec::H264],
            video: true,
        }
    }
}

/// The blobs of `manifest` this machine needs.
pub fn needed(manifest: &Manifest, needs: &Needs) -> Vec<String> {
    let mut blobs: Vec<String> = manifest
        .tracks
        .iter()
        .filter(|t| {
            matches!(
                t.kind,
                TrackKind::Vocals | TrackKind::Instrumental | TrackKind::Lyrics | TrackKind::Cover
            )
        })
        .map(|t| t.blob.sha256.clone())
        .collect();
    if needs.video
        && let Some(video) = manifest.video_for(needs.screen_height, &needs.decoders)
    {
        blobs.push(video.blob.sha256.clone());
    }
    blobs
}

/// Takes songs from `absent` to `ready`, reporting each step.
pub struct Preparer<'a> {
    pub cache: &'a BlobCache,
    pub source: &'a dyn Source,
    pub needs: Needs,
}

impl Preparer<'_> {
    pub fn manifest(&self, sha256: &str) -> Result<Manifest, CacheError> {
        self.cache.fetch(self.source, sha256, &mut |_| {})?;
        let bytes = self.cache.read(sha256)?;
        serde_json::from_slice(&bytes).map_err(|e| CacheError::Manifest(e.to_string()))
    }

    /// Prepares one song; `report` sees every state change.
    pub fn prepare(
        &self,
        content_id: &str,
        manifest_sha: &str,
        report: &mut dyn FnMut(ContentCache),
    ) -> Result<Manifest, CacheError> {
        let state = |state: CacheState, fraction: f64, error: Option<String>| ContentCache {
            content_id: content_id.into(),
            manifest: manifest_sha.into(),
            state,
            fraction,
            error,
        };
        let result = (|| {
            report(state(CacheState::Downloading, 0.0, None));
            let manifest = self.manifest(manifest_sha)?;
            let blobs = needed(&manifest, &self.needs);
            let sizes: Vec<u64> = blobs
                .iter()
                .map(|sha| {
                    manifest
                        .tracks
                        .iter()
                        .find(|t| &t.blob.sha256 == sha)
                        .map_or(0, |t| t.blob.size)
                })
                .collect();
            let total = sizes.iter().sum::<u64>().max(1) as f64;
            let mut done = 0u64;
            let mut last = 0.0;
            for (sha, size) in blobs.iter().zip(&sizes) {
                if !self.cache.has(sha) {
                    self.cache.fetch(self.source, sha, &mut |received| {
                        let fraction = (done + received) as f64 / total;
                        if fraction - last >= 0.05 {
                            last = fraction;
                            report(state(CacheState::Downloading, fraction.min(0.99), None));
                        }
                    })?;
                }
                done += size;
            }
            report(state(CacheState::Verifying, 1.0, None));
            for sha in &blobs {
                let path = self
                    .source
                    .local(sha)
                    .filter(|p| p.is_file())
                    .unwrap_or_else(|| self.cache.path(sha));
                if sha256_file(&path)? != *sha {
                    let _ = fs::remove_file(self.cache.path(sha));
                    return Err(CacheError::Corrupt(sha.clone()));
                }
            }
            Ok(manifest)
        })();
        match &result {
            Ok(_) => report(state(CacheState::Ready, 1.0, None)),
            Err(error) => report(state(CacheState::Failed, 0.0, Some(error.to_string()))),
        }
        result
    }

    /// Where a blob of a prepared song is.
    pub fn path(&self, sha256: &str) -> PathBuf {
        self.source
            .local(sha256)
            .filter(|p| p.is_file())
            .unwrap_or_else(|| self.cache.path(sha256))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::Mutex;

    struct Memory {
        blobs: HashMap<String, Vec<u8>>,
        /// Fail after this many bytes on the first request (a dropped connection).
        cut_after: Mutex<Option<usize>>,
        corrupt: bool,
    }

    impl Memory {
        fn new(items: &[&[u8]]) -> Self {
            let blobs = items
                .iter()
                .map(|b| (hex::encode(Sha256::digest(b)), b.to_vec()))
                .collect();
            Self {
                blobs,
                cut_after: Mutex::new(None),
                corrupt: false,
            }
        }
    }

    impl Source for Memory {
        fn fetch(
            &self,
            sha: &str,
            offset: u64,
            sink: &mut dyn FnMut(&[u8]) -> io::Result<()>,
        ) -> Result<bool, String> {
            let data = self.blobs.get(sha).ok_or("missing")?;
            let mut data = data[offset as usize..].to_vec();
            if self.corrupt {
                data[0] ^= 1;
            }
            if let Some(cut) = self.cut_after.lock().unwrap().take() {
                sink(&data[..cut]).map_err(|e| e.to_string())?;
                return Err("connection reset".into());
            }
            sink(&data).map_err(|e| e.to_string())?;
            Ok(true)
        }
    }

    fn temp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("kp-cache-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        dir
    }

    #[test]
    fn fetch_checks_the_hash_and_resumes() {
        let blob = vec![7u8; 100_000];
        let source = Memory::new(&[&blob]);
        let sha = source.blobs.keys().next().unwrap().clone();
        let cache = BlobCache::new(temp("resume")).unwrap();
        *source.cut_after.lock().unwrap() = Some(40_000);
        assert!(cache.fetch(&source, &sha, &mut |_| {}).is_err());
        let mut seen = 0;
        let path = cache.fetch(&source, &sha, &mut |r| seen = r).unwrap();
        assert_eq!(fs::read(path).unwrap(), blob);
        assert_eq!(seen, 100_000, "resumed from 40 000");
    }

    #[test]
    fn a_corrupt_blob_is_refused() {
        let mut source = Memory::new(&[b"hello"]);
        source.corrupt = true;
        let sha = source.blobs.keys().next().unwrap().clone();
        let cache = BlobCache::new(temp("corrupt")).unwrap();
        assert!(matches!(
            cache.fetch(&source, &sha, &mut |_| {}),
            Err(CacheError::Corrupt(_))
        ));
        assert!(!cache.has(&sha));
    }

    #[test]
    fn a_song_is_prepared_with_the_video_that_fits() {
        let fixture = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../fixtures/contracts-v2/manifest.json");
        let mut manifest: Manifest = serde_json::from_str(&fs::read_to_string(fixture).unwrap()).unwrap();
        // Stand-in bytes for every track, with their real hashes.
        let mut payloads: Vec<Vec<u8>> = Vec::new();
        for (i, track) in manifest.tracks.iter_mut().enumerate() {
            let bytes = format!("track {i}").into_bytes();
            track.blob.sha256 = hex::encode(Sha256::digest(&bytes));
            track.blob.size = bytes.len() as u64;
            payloads.push(bytes);
        }
        let manifest_bytes = serde_json::to_vec(&manifest).unwrap();
        payloads.push(manifest_bytes.clone());
        let refs: Vec<&[u8]> = payloads.iter().map(Vec::as_slice).collect();
        let source = Memory::new(&refs);
        let cache = BlobCache::new(temp("prepare")).unwrap();
        let preparer = Preparer {
            cache: &cache,
            source: &source,
            needs: Needs::default(),
        };
        let manifest_sha = hex::encode(Sha256::digest(&manifest_bytes));
        let mut states = Vec::new();
        let prepared = preparer
            .prepare("demo", &manifest_sha, &mut |c| states.push(c.state))
            .unwrap();
        assert_eq!(prepared, manifest);
        assert_eq!(states.first(), Some(&CacheState::Downloading));
        assert!(states.contains(&CacheState::Verifying));
        assert_eq!(states.last(), Some(&CacheState::Ready));
        for sha in needed(&manifest, &Needs::default()) {
            assert!(cache.has(&sha));
        }
    }

    #[test]
    fn trim_keeps_what_is_needed() {
        let source = Memory::new(&[&[1u8; 1000], &[2u8; 1000], &[3u8; 1000]]);
        let cache = BlobCache::new(temp("trim")).unwrap();
        let shas: Vec<String> = source.blobs.keys().cloned().collect();
        for sha in &shas {
            cache.fetch(&source, sha, &mut |_| {}).unwrap();
        }
        let freed = cache.trim(&shas[..1], 1000).unwrap();
        assert_eq!(freed, 2000);
        assert!(cache.has(&shas[0]));
    }
}
