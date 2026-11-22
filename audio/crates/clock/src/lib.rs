//! The player's sense of time.
//!
//! Everything the player shows or plays follows one clock: the hardware clock of the main audio
//! output. The audio callback publishes how many frames it has handed to the device and when the
//! first of them will be heard ([`MasterClock::publish`]); the render threads read that snapshot
//! without locks ([`MasterClock::snapshot`]) and extrapolate the song position to the instant a
//! frame will be presented ([`Snapshot::position_at`]).
//!
//! Orders from the server carry an [`Anchor`]: a song position, the instant it holds and the
//! playback rate, so a pause, a seek or a start at a given time are all one value.
//!
//! A second output runs on its own crystal and drifts from the main one by tens or hundreds of
//! parts per million. [`DriftController`] turns the measured offset between both into the
//! resampling ratio that keeps the second output locked to the first.

use std::sync::atomic::{AtomicU64, Ordering};

use serde::{Deserialize, Serialize};

/// Microseconds on the player's monotonic timeline.
pub type Micros = i64;

/// A song position that holds at an instant and advances at a rate (0 = paused).
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct Anchor {
    /// Seconds into the song.
    pub position: f64,
    /// When `position` holds, in microseconds on the shared timeline.
    pub instant: Micros,
    /// Song seconds per real second: 1 playing, 0 paused.
    pub rate: f64,
}

impl Anchor {
    pub const fn paused(position: f64, instant: Micros) -> Self {
        Self {
            position,
            instant,
            rate: 0.0,
        }
    }

    pub const fn playing(position: f64, instant: Micros) -> Self {
        Self {
            position,
            instant,
            rate: 1.0,
        }
    }

    /// The song position at `instant`.
    pub fn position_at(&self, instant: Micros) -> f64 {
        self.position + self.rate * (instant - self.instant) as f64 / 1e6
    }

    /// The instant the song reaches `position`, or `None` while paused.
    pub fn instant_of(&self, position: f64) -> Option<Micros> {
        (self.rate > 0.0)
            .then(|| self.instant + ((position - self.position) / self.rate * 1e6).round() as i64)
    }

    /// The same playback, re-anchored at `instant` (with a new rate).
    pub fn rebase(&self, instant: Micros, rate: f64) -> Self {
        Self {
            position: self.position_at(instant),
            instant,
            rate,
        }
    }
}

/// What the audio callback last published.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Snapshot {
    /// Song position of the first frame of the last buffer handed to the device.
    pub position: f64,
    /// When that frame leaves the speaker (callback time + output latency + calibration).
    pub heard_at: Micros,
    /// Song seconds per real second, as the device clock measures them.
    pub rate: f64,
    /// Count of publications, to tell a stalled device from a paused one.
    pub sequence: u64,
}

impl Snapshot {
    /// Song position heard at `instant`, extrapolated from the last publication.
    pub fn position_at(&self, instant: Micros) -> f64 {
        self.position + self.rate * (instant - self.heard_at) as f64 / 1e6
    }

    pub fn anchor(&self) -> Anchor {
        Anchor {
            position: self.position,
            instant: self.heard_at,
            rate: self.rate,
        }
    }
}

/// A lock-free single-writer, many-reader slot for the master clock (a seqlock on atomics: the
/// audio thread never blocks and never allocates).
#[derive(Debug, Default)]
pub struct MasterClock {
    sequence: AtomicU64,
    position: AtomicU64,
    heard_at: AtomicU64,
    rate: AtomicU64,
}

impl MasterClock {
    pub fn new() -> Self {
        Self::default()
    }

    /// Called from the audio callback only.
    pub fn publish(&self, position: f64, heard_at: Micros, rate: f64) {
        let sequence = self.sequence.load(Ordering::Relaxed);
        // Odd while writing: readers retry.
        self.sequence.store(sequence.wrapping_add(1), Ordering::Release);
        std::sync::atomic::fence(Ordering::Release);
        self.position.store(position.to_bits(), Ordering::Relaxed);
        self.heard_at.store(heard_at as u64, Ordering::Relaxed);
        self.rate.store(rate.to_bits(), Ordering::Relaxed);
        self.sequence.store(sequence.wrapping_add(2), Ordering::Release);
    }

    /// The latest consistent snapshot, or `None` before the first publication.
    pub fn snapshot(&self) -> Option<Snapshot> {
        loop {
            let before = self.sequence.load(Ordering::Acquire);
            if before == 0 {
                return None;
            }
            if before % 2 == 1 {
                std::hint::spin_loop();
                continue;
            }
            let position = f64::from_bits(self.position.load(Ordering::Relaxed));
            let heard_at = self.heard_at.load(Ordering::Relaxed) as i64;
            let rate = f64::from_bits(self.rate.load(Ordering::Relaxed));
            std::sync::atomic::fence(Ordering::Acquire);
            if self.sequence.load(Ordering::Relaxed) == before {
                return Some(Snapshot {
                    position,
                    heard_at,
                    rate,
                    sequence: before / 2,
                });
            }
        }
    }
}

/// Keeps a secondary output locked to the master by nudging its resampling ratio.
///
/// A PI controller on the offset (secondary position minus master position, in seconds, as
/// heard at the same instant): the proportional term pulls the offset back within a second or
/// two, the integral term learns the crystals' constant drift. The correction is clamped to
/// ±`max_ppm` so it is never audible as a pitch change; offsets larger than `resync_after` are
/// fixed by a jump instead (see [`Correction::Jump`]).
#[derive(Clone, Debug)]
pub struct DriftController {
    kp: f64,
    ki: f64,
    max_ppm: f64,
    resync_after: f64,
    integral: f64,
    filtered: Option<f64>,
    smoothing: f64,
}

/// What the secondary output should do next.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Correction {
    /// Read the source this many frames per output frame (≈ 1).
    Ratio(f64),
    /// Too far off: drop the buffer and restart reading at the master's position.
    Jump,
}

impl Default for DriftController {
    fn default() -> Self {
        Self {
            kp: 0.05,
            ki: 0.002,
            max_ppm: 1000.0,
            resync_after: 0.050,
            integral: 0.0,
            filtered: None,
            smoothing: 0.2,
        }
    }
}

impl DriftController {
    pub fn new() -> Self {
        Self::default()
    }

    /// Feed one offset measurement (seconds, positive = the secondary is ahead) taken every
    /// `interval` seconds; returns the correction to apply until the next one.
    pub fn update(&mut self, offset: f64, interval: f64) -> Correction {
        if offset.abs() > self.resync_after {
            self.reset();
            return Correction::Jump;
        }
        let filtered = match self.filtered {
            None => offset,
            Some(previous) => previous + self.smoothing * (offset - previous),
        };
        self.filtered = Some(filtered);
        let limit = self.max_ppm * 1e-6;
        self.integral = (self.integral + self.ki * filtered * interval.max(1e-3)).clamp(-limit, limit);
        // Ahead → read the source more slowly.
        let adjust = (self.kp * filtered + self.integral).clamp(-limit, limit);
        Correction::Ratio(1.0 - adjust)
    }

    pub fn reset(&mut self) {
        self.integral = 0.0;
        self.filtered = None;
    }

    /// The drift the controller has learnt, in parts per million.
    pub fn learnt_ppm(&self) -> f64 {
        self.integral * 1e6
    }
}

/// Measures how fast the device plays song time against the monotonic clock.
///
/// Callback timestamps jitter by a fraction of a millisecond, so the rate is a least-squares
/// slope over every publication since the last restart: its error shrinks as the song plays (a
/// few ppm after ten seconds). Until `window` has passed, the nominal rate holds.
#[derive(Clone, Debug)]
pub struct RateEstimator {
    window: Micros,
    origin: Option<(f64, Micros)>,
    n: f64,
    sx: f64,
    sy: f64,
    sxx: f64,
    sxy: f64,
    last: Micros,
    rate: f64,
}

impl RateEstimator {
    pub fn new(window: Micros) -> Self {
        Self {
            window,
            origin: None,
            n: 0.0,
            sx: 0.0,
            sy: 0.0,
            sxx: 0.0,
            sxy: 0.0,
            last: 0,
            rate: 1.0,
        }
    }

    /// Feeds a (position, heard_at) pair from a continuous playback; returns the current rate.
    pub fn update(&mut self, position: f64, heard_at: Micros) -> f64 {
        let (p0, t0) = *self.origin.get_or_insert((position, heard_at));
        let x = (heard_at - t0) as f64 / 1e6;
        let y = position - p0;
        self.n += 1.0;
        self.sx += x;
        self.sy += y;
        self.sxx += x * x;
        self.sxy += x * y;
        self.last = heard_at;
        if heard_at - t0 >= self.window {
            let denominator = self.n * self.sxx - self.sx * self.sx;
            if denominator > 0.0 {
                let slope = (self.n * self.sxy - self.sx * self.sy) / denominator;
                if (slope - 1.0).abs() < 0.01 {
                    self.rate = slope;
                }
            }
        }
        self.rate
    }

    /// After a seek or a pause: the next publication starts a new measurement (the rate learnt
    /// so far is kept meanwhile, since the crystal has not changed).
    pub fn restart(&mut self) {
        let rate = self.rate;
        *self = Self::new(self.window);
        self.rate = rate;
    }

    pub fn rate(&self) -> f64 {
        self.rate
    }
}

/// Keeps a secondary output on the master's song position, block by block.
///
/// Feed-forward from both measured rates (the crystals' ratio, learnt over the song) plus the
/// [`DriftController`] trimming what is left. The player's secondary outputs and the sync bench
/// run this same code.
#[derive(Clone, Debug)]
pub struct Follower {
    controller: DriftController,
    estimator: RateEstimator,
    content: Option<f64>,
    frames: u64,
    ratio: f64,
    nominal: f64,
    pub jumps: u32,
}

impl Follower {
    pub fn new(nominal_rate: f64) -> Self {
        Self {
            controller: DriftController::new(),
            estimator: RateEstimator::new(1_000_000),
            content: None,
            frames: 0,
            ratio: 1.0,
            nominal: nominal_rate,
            jumps: 0,
        }
    }

    /// For a block of `frames` heard from `heard_at` on: the song position of its first frame
    /// and the resampling ratio to read it at, or `None` (silence) while the master is paused or
    /// not running yet.
    pub fn block(&mut self, master: Option<Snapshot>, heard_at: Micros, frames: u32) -> Option<(f64, f64)> {
        let master = master?;
        if master.rate == 0.0 {
            self.reset();
            return None;
        }
        let target = master.position_at(heard_at);
        match self.content {
            None => {
                self.content = Some(target);
                self.ratio = 1.0;
            }
            Some(content) => {
                let own = self.estimator.update(self.frames as f64 / self.nominal, heard_at);
                let feed_forward = master.rate / own;
                let interval = f64::from(frames) / self.nominal;
                match self.controller.update(content - target, interval) {
                    Correction::Ratio(r) => self.ratio = feed_forward * r,
                    Correction::Jump => {
                        self.jumps += 1;
                        self.controller.reset();
                        self.content = Some(target);
                        self.ratio = 1.0;
                    }
                }
            }
        }
        let content = self.content.expect("set above");
        self.content = Some(content + f64::from(frames) * self.ratio / self.nominal);
        self.frames += u64::from(frames);
        Some((content, self.ratio))
    }

    /// After a seek or a pause: the next block starts again from the master's position.
    pub fn reset(&mut self) {
        self.content = None;
        self.controller.reset();
    }

    pub fn ratio(&self) -> f64 {
        self.ratio
    }

    /// How much faster than nominal this output reads, in ppm (the drift it absorbs).
    pub fn correction_ppm(&self) -> f64 {
        (self.ratio - 1.0) * 1e6
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn anchor_extrapolates_and_inverts() {
        let anchor = Anchor::playing(10.0, 1_000_000);
        assert!((anchor.position_at(3_500_000) - 12.5).abs() < 1e-12);
        assert_eq!(anchor.instant_of(12.5), Some(3_500_000));
        let paused = anchor.rebase(2_000_000, 0.0);
        assert_eq!(paused.position_at(9_000_000), 11.0);
        assert_eq!(paused.instant_of(20.0), None);
    }

    #[test]
    fn clock_publishes_consistent_snapshots() {
        let clock = MasterClock::new();
        assert!(clock.snapshot().is_none());
        clock.publish(1.5, 100, 1.0);
        let snap = clock.snapshot().unwrap();
        assert_eq!(
            (snap.position, snap.heard_at, snap.rate, snap.sequence),
            (1.5, 100, 1.0, 1)
        );
        assert!((snap.position_at(1_100) - 1.501).abs() < 1e-12);
    }

    #[test]
    fn clock_survives_concurrent_readers() {
        let clock = std::sync::Arc::new(MasterClock::new());
        let writer = {
            let clock = clock.clone();
            std::thread::spawn(move || {
                for i in 1..50_000_i64 {
                    clock.publish(i as f64, i, 1.0);
                }
            })
        };
        for _ in 0..50_000 {
            if let Some(snap) = clock.snapshot() {
                assert_eq!(snap.position as i64, snap.heard_at);
            }
        }
        writer.join().unwrap();
    }

    #[test]
    fn controller_learns_constant_drift() {
        // The secondary runs 150 ppm fast; each step the controller's ratio is applied.
        let mut controller = DriftController::new();
        let mut offset = 0.0;
        let interval = 0.01;
        let mut ratio = 1.0;
        for _ in 0..60_000 {
            offset += interval * ((1.0 + 150e-6) * ratio - 1.0);
            if let Correction::Ratio(r) = controller.update(offset, interval) {
                ratio = r;
            }
        }
        assert!(offset.abs() < 0.0005, "offset {offset}");
        assert!(
            (controller.learnt_ppm() - 150.0).abs() < 20.0,
            "{}",
            controller.learnt_ppm()
        );
    }

    #[test]
    fn rate_estimator_measures_device_speed() {
        let mut estimator = RateEstimator::new(500_000);
        let mut rate = 1.0;
        // A device 100 ppm slow: song time advances 0.9999 s per real second.
        for i in 0..2_000_i64 {
            let heard_at = i * 5_333 + (i * 7919 % 400) - 200;
            rate = estimator.update(i as f64 * 0.005_333 * 0.9999, heard_at);
        }
        assert!((rate - 0.9999).abs() < 20e-6, "{rate}");
    }

    #[test]
    fn controller_jumps_when_far_off() {
        let mut controller = DriftController::new();
        assert_eq!(controller.update(0.2, 0.01), Correction::Jump);
    }
}
