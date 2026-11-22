//! What every audio output plays.
//!
//! The song's tracks (voice, instrumental) are decoded once into memory ([`Track`]). Each output
//! has an [`OutputMixer`] that, from the audio callback, renders a block for a song position:
//! every route of the [`Routing`] matrix that targets this output adds its track with its gain
//! and delay, through the output's own pitch shifter ([`Pitcher`]), read at the output's
//! resampling ratio (≈ 1; [`kp_clock::DriftController`] nudges it on secondary outputs).
//!
//! Nothing here allocates once a mixer is built: buffers are sized up front, so the mixer can run
//! on a real-time audio thread.

use serde::{Deserialize, Serialize};
use std::sync::Arc;

/// The player's internal rate: every track is decoded (Opus is 48 kHz) and mixed at it.
pub const RATE: u32 = 48_000;
/// Loudness every song is played at, the same as v3 packages were levelled to.
pub const TARGET_LUFS: f64 = -14.0;

/// A decoded track: interleaved stereo at [`RATE`], starting `offset` seconds into the song.
#[derive(Clone, Debug)]
pub struct Track {
    pub name: String,
    pub samples: Arc<[f32]>,
    pub offset: f64,
    /// Linear gain that brings the track to [`TARGET_LUFS`].
    pub gain: f32,
}

impl Track {
    pub fn new(name: impl Into<String>, samples: Vec<f32>, offset: f64, loudness_lufs: Option<f64>) -> Self {
        Self {
            name: name.into(),
            samples: samples.into(),
            offset,
            gain: loudness_lufs.map_or(1.0, loudness_gain),
        }
    }

    pub fn frames(&self) -> usize {
        self.samples.len() / 2
    }

    pub fn duration(&self) -> f64 {
        self.frames() as f64 / f64::from(RATE)
    }

    /// The stereo frame at a fractional index (cubic Hermite interpolation; silence outside).
    #[inline]
    pub fn frame_at(&self, index: f64) -> [f32; 2] {
        let base = index.floor();
        let t = (index - base) as f32;
        let i = base as i64;
        let get = |k: i64, ch: usize| -> f32 {
            if k < 0 || k as usize >= self.frames() {
                0.0
            } else {
                self.samples[k as usize * 2 + ch]
            }
        };
        let mut out = [0.0; 2];
        for (ch, value) in out.iter_mut().enumerate() {
            let (y0, y1, y2, y3) = (get(i - 1, ch), get(i, ch), get(i + 1, ch), get(i + 2, ch));
            let c1 = 0.5 * (y2 - y0);
            let c2 = y0 - 2.5 * y1 + 2.0 * y2 - 0.5 * y3;
            let c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2);
            *value = ((c3 * t + c2) * t + c1) * t + y1;
        }
        out
    }
}

/// Linear gain that takes a track measured at `lufs` to [`TARGET_LUFS`], never boosting by more
/// than 12 dB (a quiet stem is often mostly silence).
pub fn loudness_gain(lufs: f64) -> f32 {
    let db = (TARGET_LUFS - lufs).min(12.0);
    10f64.powf(db / 20.0) as f32
}

pub fn db_to_gain(db: f64) -> f32 {
    10f64.powf(db / 20.0) as f32
}

/// One cell of the routing matrix: a track sent to an output.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Route {
    pub track: String,
    pub output: String,
    /// Decibels; `None` mutes the route.
    pub gain_db: Option<f64>,
    /// Seconds this output plays the track late (to line up with a slow display, for instance).
    #[serde(default)]
    pub delay: f64,
}

/// The routing matrix: which tracks every output plays.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Routing {
    pub routes: Vec<Route>,
}

impl Routing {
    /// Both tracks, at unity gain, to one output: the default for a single output.
    pub fn everything_to(output: &str, tracks: &[&str]) -> Self {
        Self {
            routes: tracks
                .iter()
                .map(|track| Route {
                    track: (*track).into(),
                    output: output.into(),
                    gain_db: Some(0.0),
                    delay: 0.0,
                })
                .collect(),
        }
    }

    pub fn for_output<'a>(&'a self, output: &'a str) -> impl Iterator<Item = &'a Route> + 'a {
        self.routes.iter().filter(move |route| route.output == output)
    }
}

/// A pitch shifter that runs inside an output, one per track.
pub trait Pitcher: Send {
    /// Frames between input and output: the mixer reads this much ahead to compensate.
    fn latency(&self) -> usize;
    /// Transposition in semitones (0 = none).
    fn set_semitones(&mut self, semitones: f32);
    /// Processes `input` (interleaved stereo) into `output` of the same length.
    fn process(&mut self, input: &[f32], output: &mut [f32]);
    /// Forgets its history (after a seek).
    fn reset(&mut self);
}

/// The pitch shifter that does nothing, used when no transposition is asked and in tests.
#[derive(Debug, Default)]
pub struct Bypass;

impl Pitcher for Bypass {
    fn latency(&self) -> usize {
        0
    }
    fn set_semitones(&mut self, _semitones: f32) {}
    fn process(&mut self, input: &[f32], output: &mut [f32]) {
        output.copy_from_slice(input);
    }
    fn reset(&mut self) {}
}

/// Makes a fresh [`Pitcher`] for each track an output plays.
pub type PitcherFactory = Arc<dyn Fn() -> Box<dyn Pitcher> + Send + Sync>;

pub fn bypass_factory() -> PitcherFactory {
    Arc::new(|| Box::new(Bypass) as Box<dyn Pitcher>)
}

struct Lane {
    track: Arc<Track>,
    gain: f32,
    delay: f64,
    pitcher: Box<dyn Pitcher>,
    input: Vec<f32>,
    output: Vec<f32>,
}

/// Renders the blocks of one output.
pub struct OutputMixer {
    name: String,
    lanes: Vec<Lane>,
    volume: f32,
    semitones: f32,
    next_position: Option<f64>,
    max_block: usize,
}

impl OutputMixer {
    pub fn new(
        name: &str,
        tracks: &[Arc<Track>],
        routing: &Routing,
        factory: &PitcherFactory,
        max_block: usize,
    ) -> Self {
        let lanes = routing
            .for_output(name)
            .filter_map(|route| {
                let track = tracks.iter().find(|track| track.name == route.track)?;
                let gain = route.gain_db.map_or(0.0, db_to_gain);
                Some(Lane {
                    track: track.clone(),
                    gain,
                    delay: route.delay,
                    pitcher: factory(),
                    input: vec![0.0; max_block * 2],
                    output: vec![0.0; max_block * 2],
                })
            })
            .collect();
        Self {
            name: name.into(),
            lanes,
            volume: 1.0,
            semitones: 0.0,
            next_position: None,
            max_block,
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn set_volume(&mut self, volume: f32) {
        self.volume = volume.clamp(0.0, 2.0);
    }

    pub fn set_semitones(&mut self, semitones: f32) {
        self.semitones = semitones.clamp(-12.0, 12.0);
        for lane in &mut self.lanes {
            lane.pitcher.set_semitones(self.semitones);
        }
    }

    pub fn semitones(&self) -> f32 {
        self.semitones
    }

    /// The largest pitch latency of its lanes, in seconds.
    pub fn latency(&self) -> f64 {
        self.lanes
            .iter()
            .map(|lane| lane.pitcher.latency())
            .max()
            .unwrap_or(0) as f64
            / f64::from(RATE)
    }

    /// Renders `out.len() / 2` frames whose first one is heard at song `position`, reading the
    /// tracks `ratio` source frames per output frame. A position that does not continue the
    /// previous block (a seek, a jump) resets the pitch shifters.
    pub fn render(&mut self, position: f64, ratio: f64, out: &mut [f32]) {
        let frames = out.len() / 2;
        assert!(
            frames <= self.max_block,
            "block larger than the mixer was built for"
        );
        out.fill(0.0);
        let continuous = self
            .next_position
            .is_some_and(|expected| (expected - position).abs() < 0.002);
        if !continuous {
            for lane in &mut self.lanes {
                lane.pitcher.reset();
            }
        }
        self.next_position = Some(position + frames as f64 * ratio / f64::from(RATE));
        for lane in &mut self.lanes {
            let latency = lane.pitcher.latency() as f64;
            let start = (position - lane.delay - lane.track.offset) * f64::from(RATE) + latency;
            let input = &mut lane.input[..frames * 2];
            for (i, frame) in input.chunks_exact_mut(2).enumerate() {
                let value = lane.track.frame_at(start + i as f64 * ratio);
                frame.copy_from_slice(&value);
            }
            let output = &mut lane.output[..frames * 2];
            lane.pitcher.process(input, output);
            let gain = lane.gain * lane.track.gain * self.volume;
            for (sample, value) in out.iter_mut().zip(output.iter()) {
                *sample += value * gain;
            }
        }
        for sample in out.iter_mut() {
            *sample = soft_clip(*sample);
        }
    }
}

/// Transparent below −1 dBFS, then a smooth knee so overs never wrap.
#[inline]
fn soft_clip(x: f32) -> f32 {
    const KNEE: f32 = 0.89;
    let magnitude = x.abs();
    if magnitude <= KNEE {
        x
    } else {
        let over = (magnitude - KNEE) / (1.0 - KNEE);
        x.signum() * (KNEE + (1.0 - KNEE) * over.tanh())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ramp(frames: usize) -> Vec<f32> {
        (0..frames)
            .flat_map(|i| [i as f32 / frames as f32 * 0.5; 2])
            .collect()
    }

    #[test]
    fn interpolation_hits_samples_exactly() {
        let track = Track::new("t", ramp(100), 0.0, None);
        assert_eq!(track.frame_at(10.0), [0.05, 0.05]);
        assert!((track.frame_at(10.5)[0] - 0.0525).abs() < 1e-6);
        assert_eq!(track.frame_at(-5.0), [0.0, 0.0]);
    }

    #[test]
    fn loudness_brings_tracks_to_target() {
        assert!((loudness_gain(-20.0) - 1.995).abs() < 0.01);
        assert!((loudness_gain(-40.0) - 3.98).abs() < 0.01, "capped at +12 dB");
    }

    #[test]
    fn routes_mix_tracks_with_gain_and_delay() {
        let a = Arc::new(Track::new("vocals", vec![0.1; 2000], 0.0, None));
        let b = Arc::new(Track::new("instrumental", vec![0.2; 2000], 0.0, None));
        let mut routing = Routing::everything_to("main", &["vocals", "instrumental"]);
        routing.routes.push(Route {
            track: "vocals".into(),
            output: "monitor".into(),
            gain_db: Some(-6.0206),
            delay: 0.0,
        });
        let factory = bypass_factory();
        let mut main = OutputMixer::new("main", &[a.clone(), b.clone()], &routing, &factory, 64);
        let mut out = vec![0.0; 128];
        main.render(0.001, 1.0, &mut out);
        assert!((out[0] - 0.3).abs() < 1e-6);
        let mut monitor = OutputMixer::new("monitor", &[a, b], &routing, &factory, 64);
        monitor.render(0.001, 1.0, &mut out);
        assert!((out[0] - 0.05).abs() < 1e-4);
    }

    #[test]
    fn muted_route_and_track_offset() {
        let a = Arc::new(Track::new("vocals", vec![0.5; 96_000], 1.0, None));
        let mut routing = Routing::everything_to("main", &["vocals"]);
        let factory = bypass_factory();
        let mut mixer = OutputMixer::new("main", std::slice::from_ref(&a), &routing, &factory, 64);
        let mut out = vec![0.0; 128];
        mixer.render(0.5, 1.0, &mut out);
        assert!(out.iter().all(|s| *s == 0.0), "the track starts at 1 s");
        mixer.render(1.5, 1.0, &mut out);
        assert!(out[0] > 0.4);
        routing.routes[0].gain_db = None;
        let mut muted = OutputMixer::new("main", &[a], &routing, &factory, 64);
        muted.render(1.5, 1.0, &mut out);
        assert!(out.iter().all(|s| *s == 0.0));
    }

    struct Delay(usize, Vec<f32>);
    impl Pitcher for Delay {
        fn latency(&self) -> usize {
            self.0
        }
        fn set_semitones(&mut self, _: f32) {}
        fn process(&mut self, input: &[f32], output: &mut [f32]) {
            self.1.extend_from_slice(input);
            output.copy_from_slice(&self.1[..input.len()]);
            self.1.drain(..input.len());
        }
        fn reset(&mut self) {
            self.1 = vec![0.0; self.0 * 2];
        }
    }

    #[test]
    fn pitch_latency_is_compensated() {
        // Frame k of the track holds k * 1e-4; with a 100-frame shifter the output must still be
        // in time: the mixer reads ahead by the shifter's latency.
        let routing = Routing::everything_to("main", &["t"]);
        let factory: PitcherFactory = Arc::new(|| Box::new(Delay(100, vec![0.0; 200])) as Box<dyn Pitcher>);
        let mut out = vec![0.0; 512];
        let mut plain = OutputMixer::new(
            "main",
            &[Arc::new(Track::new(
                "t",
                (0..10_000).flat_map(|k| [k as f32 * 1e-4; 2]).collect(),
                0.0,
                None,
            ))],
            &routing,
            &factory,
            256,
        );
        let mut position = 0.0;
        for _ in 0..4 {
            plain.render(position, 1.0, &mut out);
            position += 256.0 / f64::from(RATE);
        }
        assert!((out[0] - 0.0768).abs() < 1e-4, "{}", out[0]);
    }
}
