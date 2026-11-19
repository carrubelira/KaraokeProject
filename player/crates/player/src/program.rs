//! A song ready to play: its stems decoded, its lyrics, its video file.

use std::path::PathBuf;
use std::sync::Arc;

use kp_cache::Preparer;
use kp_mix::{OutputMixer, PitcherFactory, Route, Routing, Track};
use kp_proto::{Lyrics, Manifest, PlaylistItem, TrackKind};

pub struct Program {
    pub item: PlaylistItem,
    pub manifest: Manifest,
    pub lyrics: Lyrics,
    pub tracks: Vec<Arc<Track>>,
    pub video: Option<PathBuf>,
}

impl Program {
    /// Decodes the stems (a few hundred ms for a song) and reads the lyrics.
    pub fn load(item: PlaylistItem, manifest: Manifest, preparer: &Preparer<'_>) -> Result<Self, String> {
        let mut tracks = Vec::new();
        for track in &manifest.tracks {
            if !matches!(track.kind, TrackKind::Vocals | TrackKind::Instrumental) {
                continue;
            }
            let path = preparer.path(&track.blob.sha256);
            let samples = kp_media::decode_audio(&path).map_err(|e| e.to_string())?;
            let gain = track.audio.as_ref().map_or(0.0, |a| a.gain_db);
            let mut decoded = Track::new(track.kind.as_str(), samples, track.offset, None);
            decoded.gain = kp_mix::db_to_gain(gain);
            tracks.push(Arc::new(decoded));
        }
        let lyrics_track = manifest
            .track(TrackKind::Lyrics)
            .ok_or("the manifest has no lyrics")?;
        let bytes = std::fs::read(preparer.path(&lyrics_track.blob.sha256)).map_err(|e| e.to_string())?;
        let lyrics: Lyrics = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
        let video = kp_cache::needed(&manifest, &preparer.needs)
            .into_iter()
            .find(|sha| {
                manifest
                    .tracks
                    .iter()
                    .any(|t| t.kind == TrackKind::Video && &t.blob.sha256 == sha)
            })
            .map(|sha| preparer.path(&sha));
        Ok(Self {
            item,
            manifest,
            lyrics,
            tracks,
            video,
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

/// The routing the server set, as the mixer reads it; with none, both stems to `default`.
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
