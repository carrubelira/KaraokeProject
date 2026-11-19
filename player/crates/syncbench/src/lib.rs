//! The software sync bench (decision 002).
//!
//! There is no measuring hardware, so the bench simulates what the player meets on a real
//! machine and checks the player's own clock code against the truth the simulation knows:
//!
//! - a **main audio output** whose crystal runs `ppm` off nominal, calling back every `block`
//!   frames with timestamps that jitter, and reporting an output latency;
//! - an optional **second output** with its own crystal, kept in step by
//!   [`kp_clock::DriftController`] through the resampling ratio of its mixer;
//! - **displays** with their own refresh rate and drift: before each vsync the render loop asks
//!   the master clock for the song position at the predicted presentation time and picks the
//!   video frame and the lyrics state from it.
//!
//! It reports, against the true heard position of the main output:
//! audio↔audio error (target < 5 ms), A/V error per presented frame (target ≤ one video frame)
//! and the lyrics error (target ≤ one display frame).

use kp_clock::{Correction, DriftController, MasterClock, Micros, RateEstimator};
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
pub struct Display {
    pub name: String,
    pub refresh_hz: f64,
    pub ppm: f64,
    /// Scan-out and panel latency, already calibrated.
    pub latency_ms: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Scenario {
    pub name: String,
    pub seconds: f64,
    pub video_fps: f64,
    pub main: AudioDevice,
    pub second: Option<AudioDevice>,
    pub displays: Vec<Display>,
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
    pub audio_audio: Option<Stats>,
    pub learnt_ppm: Option<f64>,
    pub jumps: u32,
    /// Per display: video frame shown against the audio heard at presentation.
    pub av: Vec<(String, Stats)>,
    /// Per display: lyrics position against the audio heard at presentation.
    pub lyrics: Vec<(String, Stats)>,
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

    // Events in time order: main callbacks, second-output callbacks, display vsyncs.
    let main_period = f64::from(main.block) / main_rate;
    let mut next_main = 0.0;
    let mut main_frames: u64 = 0;

    let mut second = scenario.second.as_ref().map(|device| SecondState {
        rate: NOMINAL * (1.0 + device.ppm * 1e-6),
        period: f64::from(device.block) / (NOMINAL * (1.0 + device.ppm * 1e-6)),
        latency: device.latency_ms / 1e3,
        jitter: device.jitter_us,
        block: device.block,
        next: 0.5 * main_period,
        // Song position of the next frame the second output will render.
        content: None,
        ratio: 1.0,
        controller: DriftController::new(),
        estimator: RateEstimator::new(1_000_000),
        frames: 0,
        jumps: 0,
    });

    let mut displays: Vec<DisplayState> = scenario
        .displays
        .iter()
        .map(|d| DisplayState {
            period: 1.0 / (d.refresh_hz * (1.0 + d.ppm * 1e-6)),
            latency: d.latency_ms / 1e3,
            next: 0.25 / d.refresh_hz,
            av: Vec::new(),
            lyrics: Vec::new(),
        })
        .collect();

    let end = scenario.seconds;
    let mut t;
    let mut audio_audio = Vec::new();
    loop {
        // The earliest pending event.
        let mut earliest = next_main;
        let mut which = Event::Main;
        if let Some(s) = &second
            && s.next < earliest
        {
            earliest = s.next;
            which = Event::Second;
        }
        for (i, d) in displays.iter().enumerate() {
            if d.next < earliest {
                earliest = d.next;
                which = Event::Display(i);
            }
        }
        t = earliest;
        if t > end {
            break;
        }
        match which {
            Event::Main => {
                // The callback fills `block` frames that start to be heard at t + latency.
                let position = main_frames as f64 / NOMINAL;
                let reported = t + truth.latency + main.jitter_us * 1e-6 * rng.symmetric();
                let rate = estimator.update(position, to_us(reported));
                clock.publish(position, to_us(reported), rate);
                main_frames += u64::from(main.block);
                next_main += main_period;
            }
            Event::Second => {
                let s = second.as_mut().expect("second output");
                let snapshot = clock.snapshot();
                let heard_true = t + s.latency;
                let reported = heard_true + s.jitter * 1e-6 * rng.symmetric();
                if let Some(snapshot) = snapshot {
                    let target = snapshot.position_at(to_us(reported));
                    match s.content {
                        None => s.content = Some(target),
                        Some(content) => {
                            // Feed-forward from both measured rates; the controller only trims
                            // what they miss.
                            let own = s.estimator.update(s.frames as f64 / NOMINAL, to_us(reported));
                            let feed_forward = snapshot.rate / own;
                            match s.controller.update(content - target, s.period) {
                                Correction::Ratio(r) => s.ratio = feed_forward * r,
                                Correction::Jump => {
                                    s.jumps += 1;
                                    s.content = Some(target);
                                    s.ratio = 1.0;
                                }
                            }
                        }
                    }
                    let content = s.content.expect("set above");
                    // This block is heard from heard_true at the device's real rate.
                    s.content = Some(content + f64::from(s.block) * s.ratio / NOMINAL);
                    s.frames += u64::from(s.block);
                    if heard_true > SETTLE_SECONDS {
                        let advance = s.rate * s.ratio / NOMINAL;
                        // Sample the error in the middle of the block.
                        let mid = heard_true + 0.5 * f64::from(s.block) / s.rate;
                        let heard_second = content + (mid - heard_true) * advance;
                        audio_audio.push(heard_second - truth.heard(mid));
                    }
                }
                s.next += s.period;
            }
            Event::Display(i) => {
                let d = &mut displays[i];
                // Render loop wakes just before vsync and targets the presentation instant.
                let present = t + d.latency;
                if let Some(snapshot) = clock.snapshot() {
                    let predicted = snapshot.position_at(to_us(present));
                    let heard = truth.heard(present);
                    if present > 1.0 {
                        let frame = (predicted * scenario.video_fps).floor() / scenario.video_fps;
                        // A frame is right while the audio is inside its span.
                        let span = 1.0 / scenario.video_fps;
                        let av = if heard < frame {
                            heard - frame
                        } else if heard > frame + span {
                            heard - frame - span
                        } else {
                            0.0
                        };
                        d.av.push(av);
                        d.lyrics.push(predicted - heard);
                    }
                }
                d.next += d.period;
            }
        }
    }

    let audio_stats = second.as_ref().map(|_| Stats::from(audio_audio));
    let mut report = Report {
        scenario: scenario.name.clone(),
        audio_audio: audio_stats,
        learnt_ppm: second.as_ref().map(|s| (s.ratio - 1.0) * -1e6),
        jumps: second.as_ref().map_or(0, |s| s.jumps),
        av: Vec::new(),
        lyrics: Vec::new(),
        passed: true,
        failures: Vec::new(),
    };
    for (display, state) in scenario.displays.iter().zip(displays) {
        let av = Stats::from(state.av);
        let lyrics = Stats::from(state.lyrics);
        // A/V: never outside the frame being shown (0 ms past its span); lyrics: within one
        // refresh.
        if av.max_ms > 0.5 {
            report.failures.push(format!(
                "{}: A/V off by {:.2} ms past the frame",
                display.name, av.max_ms
            ));
        }
        let refresh_ms = 1e3 / display.refresh_hz;
        if lyrics.max_ms > refresh_ms {
            report.failures.push(format!(
                "{}: lyrics off by {:.2} ms (> {refresh_ms:.2})",
                display.name, lyrics.max_ms
            ));
        }
        report.av.push((display.name.clone(), av));
        report.lyrics.push((display.name.clone(), lyrics));
    }
    if let Some(stats) = &report.audio_audio {
        if stats.max_ms >= AUDIO_AUDIO_TARGET_MS {
            report
                .failures
                .push(format!("audio↔audio off by {:.2} ms", stats.max_ms));
        }
        if report.jumps > 1 {
            report
                .failures
                .push(format!("second output jumped {} times", report.jumps));
        }
    }
    report.passed = report.failures.is_empty();
    report
}

enum Event {
    Main,
    Second,
    Display(usize),
}

struct SecondState {
    rate: f64,
    period: f64,
    latency: f64,
    jitter: f64,
    block: u32,
    next: f64,
    content: Option<f64>,
    ratio: f64,
    controller: DriftController,
    estimator: RateEstimator,
    frames: u64,
    jumps: u32,
}

struct DisplayState {
    period: f64,
    latency: f64,
    next: f64,
    av: Vec<f64>,
    lyrics: Vec<f64>,
}

/// The scenarios the bench runs by default: the real case (one machine, two screens, one or two
/// outputs) under ordinary and hostile clocks.
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
    let tv = Display {
        name: "tv-60".into(),
        refresh_hz: 60.0,
        ppm: 30.0,
        latency_ms: 35.0,
    };
    let monitor = Display {
        name: "monitor-144".into(),
        refresh_hz: 144.0,
        ppm: -50.0,
        latency_ms: 8.0,
    };
    let pal = Display {
        name: "tv-50".into(),
        refresh_hz: 50.0,
        ppm: 0.0,
        latency_ms: 60.0,
    };
    vec![
        Scenario {
            name: "one-output-two-screens".into(),
            seconds: 300.0,
            video_fps: 30.0,
            main: hdmi(20.0),
            second: None,
            displays: vec![tv.clone(), monitor.clone()],
            seed: 1,
        },
        Scenario {
            name: "two-outputs-ordinary".into(),
            seconds: 600.0,
            video_fps: 25.0,
            main: hdmi(20.0),
            second: Some(usb(-80.0)),
            displays: vec![tv.clone(), monitor.clone()],
            seed: 2,
        },
        Scenario {
            name: "two-outputs-hostile".into(),
            seconds: 600.0,
            video_fps: 60.0,
            main: usb(200.0),
            second: Some(AudioDevice {
                jitter_us: 1500.0,
                ..hdmi(-200.0)
            }),
            displays: vec![pal, monitor],
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
        let scenario = default_scenarios().remove(1);
        let report = run(&short(scenario));
        // Main +20 ppm, second −80 ppm: the second must read 100 ppm faster (learnt = −100).
        let learnt = report.learnt_ppm.unwrap();
        assert!((learnt + 100.0).abs() < 25.0, "learnt {learnt}");
    }

    #[test]
    fn controller_holds_a_wide_gap_between_crystals() {
        // 300 ppm apart would be 18 ms in a minute without control.
        let mut scenario = short(default_scenarios().remove(1));
        scenario.second.as_mut().unwrap().ppm = -280.0;
        scenario.main.ppm = 20.0;
        let report = run(&scenario);
        assert!(
            report.audio_audio.unwrap().max_ms < AUDIO_AUDIO_TARGET_MS,
            "the controller holds"
        );
    }
}
