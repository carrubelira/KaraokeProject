//! The software sync bench (decision 002).
//!
//! There is no measuring hardware, so the bench simulates what kp-audio meets on a real
//! machine and checks its own clock code against the truth the simulation knows:
//!
//! - a **main audio output** whose crystal runs `ppm` off nominal, calling back every `block`
//!   frames with timestamps that jitter, and reporting an output latency;
//! - an optional **second output** with its own crystal, kept in step by
//!   [`kp_clock::Follower`] through the resampling ratio of its mixer.
//!
//! It reports the audio↔audio error against the true heard position of the main output
//! (target < 5 ms). The screens are web pages since decision 011: their sync is measured by
//! the web's own bench (`web/src/lib/screen/sync.test.ts`).

use kp_clock::{Follower, MasterClock, Micros, RateEstimator};
use serde::{Deserialize, Serialize};

const NOMINAL: f64 = 48_000.0;

/// A deterministic random source (xorshift64*), so every run of a scenario is identical.
#[derive(Clone, Debug)]
pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed.max(1))
    }
    pub fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    /// Uniform in [-1, 1).
    pub fn symmetric(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 52) as f64 - 1.0
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AudioDevice {
    pub name: String,
    /// Crystal error against nominal, parts per million.
    pub ppm: f64,
    /// Frames per callback.
    pub block: u32,
    /// Output latency the device reports (it is exact here: calibration covers the rest).
    pub latency_ms: f64,
    /// Peak jitter of the callback timestamps, in microseconds.
    pub jitter_us: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Scenario {
    pub name: String,
    pub seconds: f64,
    pub main: AudioDevice,
    pub second: AudioDevice,
    pub seed: u64,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct Stats {
    pub samples: u64,
    pub max_ms: f64,
    pub mean_ms: f64,
    pub p99_ms: f64,
}

impl Stats {
    fn from(mut errors: Vec<f64>) -> Self {
        if errors.is_empty() {
            return Self::default();
        }
        errors.iter_mut().for_each(|e| *e = e.abs() * 1e3);
        errors.sort_by(f64::total_cmp);
        let n = errors.len();
        Self {
            samples: n as u64,
            max_ms: errors[n - 1],
            mean_ms: errors.iter().sum::<f64>() / n as f64,
            p99_ms: errors[(n * 99 / 100).min(n - 1)],
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Report {
    pub scenario: String,
    /// Second output against the main one, after the controller settles (first 5 s left out).
    pub audio_audio: Stats,
    pub learnt_ppm: f64,
    pub jumps: u32,
    pub passed: bool,
    pub failures: Vec<String>,
}

pub const AUDIO_AUDIO_TARGET_MS: f64 = 5.0;
const SETTLE_SECONDS: f64 = 5.0;

/// Song time heard from the main output at true time `t` (seconds): the device plays frames at
/// its own rate from `t = start`.
struct MainTruth {
    rate: f64,
    start: f64,
    latency: f64,
}

impl MainTruth {
    fn heard(&self, t: f64) -> f64 {
        ((t - self.start - self.latency) * self.rate / NOMINAL).max(0.0)
    }
}

pub fn run(scenario: &Scenario) -> Report {
    let mut rng = Rng::new(scenario.seed);
    let main = &scenario.main;
    let main_rate = NOMINAL * (1.0 + main.ppm * 1e-6);
    let truth = MainTruth {
        rate: main_rate,
        start: 0.0,
        latency: main.latency_ms / 1e3,
    };
    let clock = MasterClock::new();
    let mut estimator = RateEstimator::new(1_000_000);
    let to_us = |t: f64| (t * 1e6).round() as Micros;

    // Events in time order: main callbacks and second-output callbacks.
    let main_period = f64::from(main.block) / main_rate;
    let mut next_main = 0.0;
    let mut main_frames: u64 = 0;

    let device = &scenario.second;
    let mut second = SecondState {
        rate: NOMINAL * (1.0 + device.ppm * 1e-6),
        period: f64::from(device.block) / (NOMINAL * (1.0 + device.ppm * 1e-6)),
        latency: device.latency_ms / 1e3,
        jitter: device.jitter_us,
        block: device.block,
        next: 0.5 * main_period,
        follower: Follower::new(NOMINAL),
    };

    let end = scenario.seconds;
    let mut t;
    let mut audio_audio = Vec::new();
    loop {
        // The earliest pending event.
        let main_first = next_main <= second.next;
        t = if main_first { next_main } else { second.next };
        if t > end {
            break;
        }
        if main_first {
            // The callback fills `block` frames that start to be heard at t + latency.
            let position = main_frames as f64 / NOMINAL;
            let reported = t + truth.latency + main.jitter_us * 1e-6 * rng.symmetric();
            let rate = estimator.update(position, to_us(reported));
            clock.publish(position, to_us(reported), rate);
            main_frames += u64::from(main.block);
            next_main += main_period;
        } else {
            let s = &mut second;
            let heard_true = t + s.latency;
            let reported = heard_true + s.jitter * 1e-6 * rng.symmetric();
            // The same code kp-audio runs for every output that is not the master.
            if let Some((content, ratio)) = s.follower.block(clock.snapshot(), to_us(reported), s.block)
                && heard_true > SETTLE_SECONDS
            {
                let advance = s.rate * ratio / NOMINAL;
                let mid = heard_true + 0.5 * f64::from(s.block) / s.rate;
                audio_audio.push(content + (mid - heard_true) * advance - truth.heard(mid));
            }
            s.next += s.period;
        }
    }

    let mut report = Report {
        scenario: scenario.name.clone(),
        audio_audio: Stats::from(audio_audio),
        learnt_ppm: -second.follower.correction_ppm(),
        jumps: second.follower.jumps,
        passed: true,
        failures: Vec::new(),
    };
    if report.audio_audio.max_ms >= AUDIO_AUDIO_TARGET_MS {
        let off = report.audio_audio.max_ms;
        report.failures.push(format!("audio↔audio off by {off:.2} ms"));
    }
    if report.jumps > 1 {
        let jumps = report.jumps;
        report
            .failures
            .push(format!("second output jumped {jumps} times"));
    }
    report.passed = report.failures.is_empty();
    report
}

struct SecondState {
    rate: f64,
    period: f64,
    latency: f64,
    jitter: f64,
    block: u32,
    next: f64,
    follower: Follower,
}

/// The scenarios the bench runs by default: two outputs on the backend, under ordinary and
/// hostile clocks.
pub fn default_scenarios() -> Vec<Scenario> {
    let hdmi = |ppm: f64| AudioDevice {
        name: "hdmi".into(),
        ppm,
        block: 480,
        latency_ms: 40.0,
        jitter_us: 300.0,
    };
    let usb = |ppm: f64| AudioDevice {
        name: "usb".into(),
        ppm,
        block: 256,
        latency_ms: 12.0,
        jitter_us: 500.0,
    };
    vec![
        Scenario {
            name: "two-outputs-ordinary".into(),
            seconds: 600.0,
            main: hdmi(20.0),
            second: usb(-80.0),
            seed: 2,
        },
        Scenario {
            name: "two-outputs-hostile".into(),
            seconds: 600.0,
            main: usb(200.0),
            second: AudioDevice {
                jitter_us: 1500.0,
                ..hdmi(-200.0)
            },
            seed: 3,
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn short(mut scenario: Scenario) -> Scenario {
        scenario.seconds = 60.0;
        scenario
    }

    #[test]
    fn every_default_scenario_meets_the_targets() {
        for scenario in default_scenarios() {
            let report = run(&short(scenario));
            assert!(report.passed, "{}: {:?}", report.scenario, report.failures);
        }
    }

    #[test]
    fn second_output_learns_the_drift_between_crystals() {
        let scenario = default_scenarios().remove(0);
        let report = run(&short(scenario));
        // Main +20 ppm, second −80 ppm: the second must read 100 ppm faster (learnt = −100).
        let learnt = report.learnt_ppm;
        assert!((learnt + 100.0).abs() < 25.0, "learnt {learnt}");
    }

    #[test]
    fn controller_holds_a_wide_gap_between_crystals() {
        // 300 ppm apart would be 18 ms in a minute without control.
        let mut scenario = short(default_scenarios().remove(0));
        scenario.second.ppm = -280.0;
        scenario.main.ppm = 20.0;
        let report = run(&scenario);
        assert!(
            report.audio_audio.max_ms < AUDIO_AUDIO_TARGET_MS,
            "the controller holds"
        );
    }
}
