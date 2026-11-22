//! A song ready to play: its stems decoded from the server's own store.

use std::path::PathBuf;
use std::sync::Arc;

use kp_mix::{OutputMixer, PitcherFactory, Route, Routing, Track};
use kp_proto::{Manifest, TrackKind};

use crate::decode;

/// The server's content store, read in place: kp-audio runs on the server's machine.
#[derive(Clone, Debug)]
pub struct Store {
    root: PathBuf,
}

impl Store {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// The same layout as `karaoke_contracts.cas.blob_path`.
    pub fn path(&self, sha256: &str) -> PathBuf {
        self.root.join(&sha256[..2]).join(&sha256[2..])
    }

    pub fn manifest(&self, sha256: &str) -> Result<Manifest, String> {
        let bytes = std::fs::read(self.path(sha256)).map_err(|e| format!("manifest {sha256}: {e}"))?;
        serde_json::from_slice(&bytes).map_err(|e| format!("manifest {sha256}: {e}"))
    }
}

pub struct Program {
    pub program: kp_proto::Program,
    pub title: String,
    pub tracks: Vec<Arc<Track>>,
}

impl Program {
    /// Decodes both stems (a second or two for a song, on a thread of its own).
    pub fn load(program: kp_proto::Program, store: &Store) -> Result<Self, String> {
        let manifest = store.manifest(&program.manifest)?;
        let mut tracks = Vec::new();
        for track in &manifest.tracks {
            if !matches!(track.kind, TrackKind::Vocals | TrackKind::Instrumental) {
                continue;
            }
            let samples = decode::decode_audio(&store.path(&track.blob.sha256))?;
            let gain = track.audio.as_ref().map_or(0.0, |a| a.gain_db);
            let mut decoded = Track::new(track.kind.as_str(), samples, track.offset, None);
            decoded.gain = kp_mix::db_to_gain(gain);
            tracks.push(Arc::new(decoded));
        }
        if tracks.is_empty() {
            return Err(format!("{} has no audio tracks", manifest.title));
        }
        Ok(Self {
            program,
            title: manifest.title,
            tracks,
        })
    }

    /// The mixer for one output, from the routing matrix.
    pub fn mixer(
        &self,
        output: &str,
        routing: &Routing,
        factory: &PitcherFactory,
        semitones: f32,
        volume: f32,
    ) -> OutputMixer {
        let mut mixer = OutputMixer::new(output, &self.tracks, routing, factory, 8192);
        mixer.set_semitones(semitones);
        mixer.set_volume(volume);
        mixer
    }
}

/// The routing the operator set, as the mixer reads it; with none, both stems to `default`.
pub fn routing(config: &kp_proto::Routing, default: &str) -> Routing {
    if config.routes.is_empty() {
        return Routing::everything_to(default, &["vocals", "instrumental"]);
    }
    Routing {
        routes: config
            .routes
            .iter()
            .map(|r| Route {
                track: r.track.as_str().into(),
                output: r.output.clone(),
                gain_db: r.gain_db,
                delay: r.delay_ms / 1000.0,
            })
            .collect(),
    }
}
