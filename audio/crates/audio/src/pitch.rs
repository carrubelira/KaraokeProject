//! Transposition with Signalsmith Stretch (MIT), one instance per track and output.
//!
//! It always runs, even at 0 semitones, so its latency never changes under the song: the mixer
//! reads ahead by exactly that much (kp-mix), and transposing in the middle of a song does not
//! move it in time. It applies to the guide vocals as much as to the music.

use std::sync::Arc;

#[cfg(not(feature = "pitch"))]
use kp_mix::Bypass;
#[cfg(feature = "pitch")]
use kp_mix::RATE;
use kp_mix::{Pitcher, PitcherFactory};

#[cfg(feature = "pitch")]
pub struct Stretch {
    inner: signalsmith_stretch::Stretch,
    latency: usize,
}

#[cfg(feature = "pitch")]
impl Stretch {
    pub fn new() -> Self {
        let inner = signalsmith_stretch::Stretch::preset_default(2, RATE);
        let latency = inner.input_latency() + inner.output_latency();
        Self { inner, latency }
    }
}

#[cfg(feature = "pitch")]
impl Default for Stretch {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(feature = "pitch")]
impl Pitcher for Stretch {
    fn latency(&self) -> usize {
        self.latency
    }
    fn set_semitones(&mut self, semitones: f32) {
        self.inner.set_transpose_factor_semitones(semitones, None);
    }
    fn process(&mut self, input: &[f32], output: &mut [f32]) {
        self.inner.process(input, output);
    }
    fn reset(&mut self) {
        self.inner.reset();
    }
}

/// Pitch shifters for every lane; without the `pitch` feature, none.
pub fn factory() -> PitcherFactory {
    #[cfg(feature = "pitch")]
    {
        Arc::new(|| Box::new(Stretch::new()) as Box<dyn Pitcher>)
    }
    #[cfg(not(feature = "pitch"))]
    {
        Arc::new(|| Box::new(Bypass) as Box<dyn Pitcher>)
    }
}

#[cfg(all(test, feature = "pitch"))]
mod tests {
    use super::*;

    fn sine(freq: f32, frames: usize) -> Vec<f32> {
        (0..frames)
            .flat_map(|i| [(2.0 * std::f32::consts::PI * freq * i as f32 / RATE as f32).sin() * 0.5; 2])
            .collect()
    }

    fn zero_crossings(samples: &[f32]) -> usize {
        samples
            .as_chunks::<2>()
            .0
            .iter()
            .map(|f| f[0])
            .collect::<Vec<_>>()
            .windows(2)
            .filter(|w| w[0] <= 0.0 && w[1] > 0.0)
            .count()
    }

    #[test]
    fn twelve_semitones_doubles_the_pitch() {
        let mut stretch = Stretch::new();
        stretch.set_semitones(12.0);
        let input = sine(220.0, 48_000);
        let mut output = vec![0.0; input.len()];
        for (i, o) in input.chunks(960).zip(output.chunks_mut(960)) {
            stretch.process(i, o);
        }
        // Skip the shifter's latency, then count cycles over half a second.
        let tail = &output[stretch.latency() * 2 + 2_000..stretch.latency() * 2 + 2_000 + 48_000];
        let cycles = zero_crossings(tail);
        assert!((cycles as i64 - 220).abs() < 12, "{cycles} cycles in 0.5 s");
        assert!(stretch.latency() > 0);
    }
}
