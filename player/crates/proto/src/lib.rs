//! Contracts v2, as the player reads and writes them.
//!
//! The source of truth is `packages/contracts` (pydantic → `schemas/*.schema.json`). These types
//! are written by hand to match, and `tests/fixtures.rs` keeps them honest: every example in
//! `fixtures/contracts-v2/` must parse and serialise back to the same JSON (decision 003).
//! Unknown fields are an error, as in Python, except inside lyrics lines, words and parts (v1
//! allowed extras there and they are kept).

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

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

    /// The video track that best fits a screen: the smallest one at least as tall, among the
    /// codecs the machine decodes; else the tallest it can decode.
    pub fn video_for(&self, height: u32, decoders: &[VideoCodec]) -> Option<&Track> {
        let mut videos: Vec<&Track> = self
            .tracks
            .iter()
            .filter(|t| t.video.as_ref().is_some_and(|v| decoders.contains(&v.codec)))
            .collect();
        videos.sort_by_key(|t| t.video.as_ref().map_or(0, |v| v.height));
        videos
            .iter()
            .find(|t| t.video.as_ref().is_some_and(|v| v.height >= height))
            .or(videos.last())
            .copied()
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Part {
    pub text: String,
    pub start: f64,
    pub end: f64,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Word {
    pub text: String,
    pub start: f64,
    pub end: f64,
    #[serde(default)]
    pub confidence: Option<f64>,
    #[serde(default)]
    pub parts: Vec<Part>,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    #[default]
    Lead,
    Backing,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Line {
    pub id: String,
    pub start: f64,
    pub end: f64,
    #[serde(default)]
    pub singer: Option<String>,
    #[serde(default)]
    pub role: Role,
    pub words: Vec<Word>,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Singer {
    pub id: String,
    pub name: Option<String>,
    pub color: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LyricsProvenance {
    pub lyrics_source: String,
    pub separation_model: Option<String>,
    pub asr_model: Option<String>,
    pub align_model: Option<String>,
    pub engine_version: String,
    pub language_fallbacks: Vec<Value>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Lyrics {
    pub schema_version: String,
    pub language: String,
    pub singers: Vec<Singer>,
    pub lines: Vec<Line>,
    pub provenance: LyricsProvenance,
    pub edited: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlaylistItem {
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
pub struct Playlist {
    pub id: String,
    pub name: String,
    pub version: u64,
    pub items: Vec<PlaylistItem>,
    pub player_id: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Command {
    Load,
    Play,
    Pause,
    Seek,
    Next,
    Previous,
    Stop,
    Volume,
    Pitch,
    Reload,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlayerCommand {
    pub id: String,
    pub command: Command,
    pub item_id: Option<String>,
    pub anchor: Option<Anchor>,
    pub value: Option<f64>,
    pub issued_at: i64,
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
#[serde(rename_all = "kebab-case")]
pub enum ScreenLayout {
    VideoLyrics,
    Lyrics,
    Video,
    Off,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Screen {
    pub display: String,
    pub layout: ScreenLayout,
    pub theme: String,
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
    pub screens: Vec<Screen>,
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

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Calibration {
    pub audio_ms: BTreeMap<String, f64>,
    pub display_ms: BTreeMap<String, f64>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlayerConfig {
    pub routing: Routing,
    pub calibration: Calibration,
    pub playlist_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Display {
    pub id: String,
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub refresh_hz: f64,
    pub primary: bool,
    pub connected: bool,
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

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlayerOutputs {
    pub displays: Vec<Display>,
    pub audio: Vec<AudioDevice>,
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
pub enum PlaybackState {
    #[default]
    Idle,
    Loading,
    Playing,
    Paused,
    Waiting,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlayerStatus {
    pub outputs: PlayerOutputs,
    pub cache: Vec<ContentCache>,
    pub item_id: Option<String>,
    pub position: Option<f64>,
    pub state: PlaybackState,
    pub semitones: f64,
    pub volume: f64,
    pub sync: BTreeMap<String, f64>,
}

impl Default for PlayerStatus {
    fn default() -> Self {
        Self {
            outputs: PlayerOutputs::default(),
            cache: Vec::new(),
            item_id: None,
            position: None,
            state: PlaybackState::Idle,
            semitones: 0.0,
            volume: 1.0,
            sync: BTreeMap::new(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gpu {
    pub name: String,
    pub vram_total_mb: u64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Capabilities {
    pub os: String,
    pub cpus: u32,
    pub ram_mb: u64,
    pub gpus: Vec<Gpu>,
    pub internet: bool,
    pub tasks: Vec<String>,
    pub models: BTreeMap<String, String>,
    pub decoders: Vec<String>,
    pub same_host_as_server: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Enrollment {
    pub token: String,
    pub kind: String,
    pub name: String,
    pub capabilities: Capabilities,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Enrolled {
    pub node_id: String,
    pub credential: String,
    pub server_fingerprint: String,
}

/// Messages the server pushes to a player over its WebSocket.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum ServerMessage {
    Config {
        config: PlayerConfig,
    },
    Playlist {
        playlist: Playlist,
    },
    Command {
        command: PlayerCommand,
    },
    /// The server's clock now (µs), for the player to learn the offset to its own.
    Time {
        now: i64,
        sent: Option<i64>,
    },
}

/// Messages a player sends.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum PlayerMessage {
    Status {
        status: PlayerStatus,
    },
    /// Asks for the server's time; `sent` is the player's clock (µs) for the round trip.
    TimeRequest {
        sent: i64,
    },
}
