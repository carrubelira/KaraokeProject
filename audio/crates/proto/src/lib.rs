//! Contracts v2, as `kp-audio` reads and writes them (decision 011).
//!
//! The source of truth is `packages/contracts` (pydantic → `schemas/*.schema.json`). These types
//! are written by hand to match, and `tests/fixtures.rs` keeps them honest: every example in
//! `fixtures/contracts-v2/` that kp-audio reads or writes must parse and serialise back to the
//! same JSON (decision 003). Unknown fields are an error, as in Python.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

pub use kp_clock::Anchor;

pub type Sha256 = String;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Blob {
    pub sha256: Sha256,
    pub size: u64,
    pub media_type: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AudioInfo {
    pub codec: String,
    pub container: String,
    pub sample_rate: u32,
    pub channels: u8,
    pub preskip: u32,
    pub gain_db: f64,
    pub loudness_lufs: Option<f64>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum VideoCodec {
    H264,
    Hevc,
    Av1,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VideoInfo {
    pub codec: VideoCodec,
    pub width: u32,
    pub height: u32,
    pub fps: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TrackKind {
    Vocals,
    Instrumental,
    Video,
    Lyrics,
    Cover,
}

impl TrackKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Vocals => "vocals",
            Self::Instrumental => "instrumental",
            Self::Video => "video",
            Self::Lyrics => "lyrics",
            Self::Cover => "cover",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Track {
    pub kind: TrackKind,
    pub blob: Blob,
    pub offset: f64,
    pub duration: Option<f64>,
    pub audio: Option<AudioInfo>,
    pub video: Option<VideoInfo>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: String,
    pub content_id: String,
    pub version: u32,
    pub parent: Option<Sha256>,
    pub created_at: String,
    pub title: String,
    pub artist: Option<String>,
    pub language: String,
    pub duration: f64,
    pub tracks: Vec<Track>,
}

impl Manifest {
    pub fn track(&self, kind: TrackKind) -> Option<&Track> {
        self.tracks.iter().find(|t| t.kind == kind)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QueueItem {
    pub id: String,
    pub content_id: String,
    pub manifest: Option<Sha256>,
    pub start: Option<f64>,
    pub end: Option<f64>,
    pub semitones: f64,
    pub singer: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Queue {
    pub version: u64,
    pub items: Vec<QueueItem>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Route {
    pub track: TrackKind,
    pub output: String,
    pub gain_db: Option<f64>,
    pub delay_ms: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OutputPolicy {
    Pause,
    Continue,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Routing {
    pub master: Option<String>,
    pub routes: Vec<Route>,
    pub policies: BTreeMap<String, OutputPolicy>,
}

impl Routing {
    /// What to do when `output` disappears: its own policy, else pause for the master and
    /// continue for the rest (plan v4 §6).
    pub fn policy(&self, output: &str) -> OutputPolicy {
        self.policies
            .get(output)
            .copied()
            .unwrap_or(if self.master.as_deref() == Some(output) {
                OutputPolicy::Pause
            } else {
                OutputPolicy::Continue
            })
    }
}

/// How the stems go to the backend's sound cards, and how late each one really is.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AudioConfig {
    pub routing: Routing,
    pub calibration_ms: BTreeMap<String, f64>,
}

/// A queue item with the manifest it plays.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Program {
    pub item: QueueItem,
    pub manifest: Sha256,
    pub duration: f64,
}

impl Program {
    /// Same song, same version: what was decoded for one is good for the other.
    pub fn same_as(&self, other: &Program) -> bool {
        self.item.id == other.item.id && self.manifest == other.manifest
    }

    /// Where the song stops: its exit point, or its end.
    pub fn end(&self) -> f64 {
        self.item.end.map_or(self.duration, |end| end.min(self.duration))
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionState {
    #[default]
    Idle,
    Cueing,
    Cued,
    Playing,
    Paused,
    Ended,
    Fault,
}

/// What the server says is on: the newest version wins.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Session {
    pub version: u64,
    pub epoch: u64,
    pub state: SessionState,
    pub current: Option<Program>,
    pub anchor: Option<Anchor>,
    pub upcoming: Vec<Program>,
    pub semitones: f64,
    pub volume: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CacheState {
    Absent,
    Downloading,
    Verifying,
    Ready,
    Failed,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContentCache {
    pub content_id: String,
    pub manifest: Sha256,
    pub state: CacheState,
    pub fraction: f64,
    pub error: Option<String>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AudioState {
    #[default]
    Idle,
    Loading,
    Ready,
    Playing,
    Paused,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AudioDevice {
    pub id: String,
    pub name: String,
    pub channels: u16,
    pub sample_rate: u32,
    pub latency_ms: Option<f64>,
    pub default: bool,
    pub connected: bool,
    pub bluetooth: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AudioErrorCode {
    OutputFailed,
    OutputLost,
    LoadFailed,
    MasterLost,
}

/// Something kp-audio could not do, reported until it can again.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AudioError {
    pub code: AudioErrorCode,
    pub device: Option<String>,
    pub item_id: Option<String>,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AudioStatus {
    pub state: AudioState,
    pub epoch: Option<u64>,
    pub ready: bool,
    pub item_id: Option<String>,
    pub position: Option<f64>,
    pub errors: Vec<AudioError>,
    pub devices: Vec<AudioDevice>,
    pub cache: Vec<ContentCache>,
    pub sync: BTreeMap<String, f64>,
}

impl Default for AudioStatus {
    fn default() -> Self {
        Self {
            state: AudioState::Idle,
            epoch: None,
            ready: false,
            item_id: None,
            position: None,
            errors: Vec::new(),
            devices: Vec::new(),
            cache: Vec::new(),
            sync: BTreeMap::new(),
        }
    }
}

/// Messages the server pushes to kp-audio over its socket.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum ServerMessage {
    Config {
        config: AudioConfig,
    },
    Session {
        session: Session,
    },
    /// The server's monotonic clock now (µs), for kp-audio to learn the offset to its own.
    Time {
        now: i64,
        sent: Option<i64>,
    },
}

/// Messages kp-audio sends.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum AudioMessage {
    Status {
        status: AudioStatus,
    },
    /// Asks for the server's time; `sent` is kp-audio's clock (µs) for the round trip.
    TimeRequest {
        sent: i64,
    },
}
