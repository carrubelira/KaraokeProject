//! Audio outputs: real devices through cpal, or simulated ones (headless runs and tests).
//!
//! Every output follows the [`Timeline`](kp_core::Timeline) on this machine's monotonic clock
//! through its own [`Follower`]: it measures its crystal against that clock and resamples by a
//! few hundred ppm at most, so all outputs play the same sample at the same instant (decision
//! 006). The master output also publishes what it is playing on the [`MasterClock`], and the
//! screens follow that: the picture follows the sound that is heard.
//!
//! The callback never blocks: the timeline is read with `try_lock` (falling back to the last
//! position), and new mixers arrive by channel already built; the old ones go back by channel to
//! be dropped off the audio thread.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{Receiver, Sender, channel};
use std::sync::{Arc, Mutex};

use kp_clock::{Follower, MasterClock, Micros, Snapshot};
use kp_core::Timeline;
use kp_mix::{OutputMixer, RATE};

#[derive(Clone, Debug, PartialEq)]
pub struct DeviceInfo {
    pub id: String,
    pub name: String,
    pub channels: u16,
    pub sample_rate: u32,
    pub latency_ms: Option<f64>,
    pub default: bool,
    pub bluetooth: bool,
}

/// Fills an interleaved buffer of `channels` channels whose first frame is heard at the instant
/// given (local µs).
pub type Render = Box<dyn FnMut(&mut [f32], u16, Micros) + Send>;

pub trait Backend: Send {
    fn devices(&self) -> Vec<DeviceInfo>;
    /// Starts an output; dropping the handle stops it. `lost` is set if the device goes away.
    fn open(&self, id: &str, render: Render, lost: Arc<AtomicBool>) -> Result<Box<dyn Send>, String>;
}

/// What the control thread sends a running output.
pub enum Update {
    Mixer(Box<OutputMixer>),
    Unload,
    Volume(f32),
    Semitones(f32),
    CalibrationUs(i64),
}

#[derive(Debug, Default)]
pub struct OutputStats {
    /// Sum of squares of everything played (for a "is it making sound" check), as f64 bits.
    pub energy: AtomicU64,
    pub frames: AtomicU64,
    /// The correction the follower applies, in ppm × 1000, as i64 bits.
    pub correction: AtomicU64,
    pub jumps: AtomicU64,
}

impl OutputStats {
    pub fn rms(&self) -> f64 {
        let frames = self.frames.load(Ordering::Relaxed).max(1) as f64;
        (f64::from_bits(self.energy.load(Ordering::Relaxed)) / (2.0 * frames)).sqrt()
    }
    pub fn correction_ppm(&self) -> f64 {
        self.correction.load(Ordering::Relaxed) as i64 as f64 / 1000.0
    }
}

/// State every output shares with the control thread.
#[derive(Default)]
pub struct Shared {
    pub timeline: Mutex<Timeline>,
    pub master: MasterClock,
}

impl Shared {
    /// The timeline's position at `at`, as a snapshot a follower can track.
    fn target(&self, at: Micros, last: &mut Option<Snapshot>) -> Option<Snapshot> {
        if let Ok(timeline) = self.timeline.try_lock() {
            *last = timeline.anchor_at(at).map(|anchor| Snapshot {
                position: anchor.position_at(at).max(0.0),
                heard_at: at,
                rate: anchor.rate,
                sequence: 0,
            });
        }
        *last
    }
}

struct OutputState {
    shared: Arc<Shared>,
    stats: Arc<OutputStats>,
    updates: Receiver<Update>,
    garbage: Sender<Box<OutputMixer>>,
    mixer: Option<Box<OutputMixer>>,
    follower: Follower,
    is_master: bool,
    device_rate: f64,
    calibration_us: i64,
    stereo: Vec<f32>,
    last_target: Option<Snapshot>,
}

impl OutputState {
    fn render(&mut self, out: &mut [f32], channels: u16, heard_at: Micros) {
        while let Ok(update) = self.updates.try_recv() {
            match update {
                Update::Mixer(mixer) => {
                    if let Some(old) = self.mixer.replace(mixer) {
                        let _ = self.garbage.send(old);
                    }
                    self.follower.reset();
                }
                Update::Unload => {
                    if let Some(old) = self.mixer.take() {
                        let _ = self.garbage.send(old);
                    }
                }
                Update::Volume(v) => {
                    if let Some(m) = self.mixer.as_mut() {
                        m.set_volume(v);
                    }
                }
                Update::Semitones(s) => {
                    if let Some(m) = self.mixer.as_mut() {
                        m.set_semitones(s);
                    }
                }
                Update::CalibrationUs(c) => self.calibration_us = c,
            }
        }
        let channels = usize::from(channels.max(1));
        let frames = out.len() / channels;
        let heard_at = heard_at + self.calibration_us;
        let target = self.shared.target(heard_at, &mut self.last_target);
        let block = self.follower.block(target, heard_at, frames as u32);
        if self.stereo.len() < frames * 2 {
            // Only when the device asks for a larger block than ever before.
            self.stereo.resize(frames * 2, 0.0);
        }
        let stereo = &mut self.stereo[..frames * 2];
        match (block, self.mixer.as_mut()) {
            (Some((position, ratio)), Some(mixer)) => {
                mixer.render(position, ratio * f64::from(RATE) / self.device_rate, stereo);
                if self.is_master {
                    self.shared.master.publish(position, heard_at, 1.0);
                }
            }
            _ => {
                stereo.fill(0.0);
                if self.is_master {
                    let position = target.map_or(0.0, |t| t.position);
                    self.shared.master.publish(position, heard_at, 0.0);
                }
            }
        }
        let mut energy = 0.0f64;
        for (frame, pair) in out.chunks_exact_mut(channels).zip(stereo.chunks_exact(2)) {
            frame.fill(0.0);
            frame[0] = pair[0];
            if channels > 1 {
                frame[1] = pair[1];
            } else {
                frame[0] = 0.5 * (pair[0] + pair[1]);
            }
            energy += f64::from(pair[0] * pair[0] + pair[1] * pair[1]);
        }
        let total = f64::from_bits(self.stats.energy.load(Ordering::Relaxed)) + energy;
        self.stats.energy.store(total.to_bits(), Ordering::Relaxed);
        self.stats.frames.fetch_add(frames as u64, Ordering::Relaxed);
        self.stats.correction.store(
            ((self.follower.correction_ppm() * 1000.0) as i64) as u64,
            Ordering::Relaxed,
        );
        self.stats
            .jumps
            .store(u64::from(self.follower.jumps), Ordering::Relaxed);
    }
}

pub struct Output {
    pub updates: Sender<Update>,
    pub stats: Arc<OutputStats>,
    pub lost: Arc<AtomicBool>,
    pub is_master: bool,
    _handle: Box<dyn Send>,
}

/// The open outputs and how to reach each one.
pub struct Outputs {
    backend: Box<dyn Backend>,
    pub shared: Arc<Shared>,
    pub open: HashMap<String, Output>,
    garbage_tx: Sender<Box<OutputMixer>>,
    garbage_rx: Receiver<Box<OutputMixer>>,
}

impl Outputs {
    pub fn new(backend: Box<dyn Backend>) -> Self {
        let (garbage_tx, garbage_rx) = channel();
        Self {
            backend,
            shared: Arc::new(Shared::default()),
            open: HashMap::new(),
            garbage_tx,
            garbage_rx,
        }
    }

    pub fn devices(&self) -> Vec<DeviceInfo> {
        self.backend.devices()
    }

    /// Opens `wanted` (closing the rest); `master` publishes the clock the screens follow.
    pub fn reconcile(&mut self, wanted: &[String], master: &str) -> Vec<String> {
        let mut failed = Vec::new();
        self.open.retain(|id, output| {
            wanted.contains(id) && output.is_master == (id == master) && !output.lost.load(Ordering::Relaxed)
        });
        let devices = self.devices();
        for id in wanted {
            if self.open.contains_key(id) {
                continue;
            }
            let Some(info) = devices.iter().find(|d| &d.id == id).cloned() else {
                failed.push(id.clone());
                continue;
            };
            let (tx, rx) = channel();
            let stats = Arc::new(OutputStats::default());
            let lost = Arc::new(AtomicBool::new(false));
            let mut state = OutputState {
                shared: self.shared.clone(),
                stats: stats.clone(),
                updates: rx,
                garbage: self.garbage_tx.clone(),
                mixer: None,
                follower: Follower::new(f64::from(info.sample_rate)),
                is_master: id == master,
                device_rate: f64::from(info.sample_rate),
                calibration_us: 0,
                stereo: vec![0.0; 8192],
                last_target: None,
            };
            let render: Render =
                Box::new(move |out, channels, heard_at| state.render(out, channels, heard_at));
            match self.backend.open(id, render, lost.clone()) {
                Ok(handle) => {
                    log::info!(
                        "audio output {} ({} Hz{})",
                        info.name,
                        info.sample_rate,
                        if id == master { ", master" } else { "" }
                    );
                    self.open.insert(
                        id.clone(),
                        Output {
                            updates: tx,
                            stats,
                            lost,
                            is_master: id == master,
                            _handle: handle,
                        },
                    );
                }
                Err(error) => {
                    log::warn!("could not open {id}: {error}");
                    failed.push(id.clone());
                }
            }
        }
        failed
    }

    pub fn send(&self, id: &str, update: Update) {
        if let Some(output) = self.open.get(id) {
            let _ = output.updates.send(update);
        }
    }

    pub fn broadcast(&self, make: impl Fn() -> Update) {
        for output in self.open.values() {
            let _ = output.updates.send(make());
        }
    }

    /// Outputs whose device went away since the last call.
    pub fn take_lost(&mut self) -> Vec<String> {
        let lost: Vec<String> = self
            .open
            .iter()
            .filter(|(_, o)| o.lost.load(Ordering::Relaxed))
            .map(|(id, _)| id.clone())
            .collect();
        for id in &lost {
            self.open.remove(id);
        }
        lost
    }

    /// Drops mixers the audio threads handed back.
    pub fn collect_garbage(&self) {
        while self.garbage_rx.try_recv().is_ok() {}
    }
}

/// Simulated devices: a thread per output calling back on schedule, with a crystal that drifts.
pub mod simulated {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[derive(Clone, Debug)]
    pub struct Device {
        pub info: DeviceInfo,
        pub ppm: f64,
        pub block: u32,
    }

    pub struct Simulated {
        pub devices: Arc<Mutex<Vec<Device>>>,
    }

    impl Simulated {
        pub fn new(count: usize) -> Self {
            let devices = (0..count)
                .map(|i| Device {
                    info: DeviceInfo {
                        id: format!(
                            "virtual:{}",
                            if i == 0 {
                                "main".to_string()
                            } else {
                                format!("out{i}")
                            }
                        ),
                        name: format!("Virtual output {}", i + 1),
                        channels: 2,
                        sample_rate: 48_000,
                        latency_ms: Some(20.0),
                        default: i == 0,
                        bluetooth: false,
                    },
                    ppm: if i == 0 { 0.0 } else { -60.0 * i as f64 },
                    block: 480,
                })
                .collect();
            Self {
                devices: Arc::new(Mutex::new(devices)),
            }
        }
    }

    impl Backend for Simulated {
        fn devices(&self) -> Vec<DeviceInfo> {
            self.devices
                .lock()
                .expect("not poisoned")
                .iter()
                .map(|d| d.info.clone())
                .collect()
        }

        fn open(&self, id: &str, mut render: Render, lost: Arc<AtomicBool>) -> Result<Box<dyn Send>, String> {
            let device = self
                .devices
                .lock()
                .expect("not poisoned")
                .iter()
                .find(|d| d.info.id == id)
                .cloned()
                .ok_or("no such device")?;
            let stop = Arc::new(AtomicBool::new(false));
            let flag = stop.clone();
            let all = self.devices.clone();
            let id = id.to_string();
            thread::Builder::new()
                .name(format!("audio {id}"))
                .spawn(move || {
                    let rate = f64::from(device.info.sample_rate) * (1.0 + device.ppm * 1e-6);
                    let period = f64::from(device.block) / rate;
                    let latency = (device.info.latency_ms.unwrap_or(0.0) * 1000.0) as i64;
                    let mut buffer = vec![0f32; device.block as usize * usize::from(device.info.channels)];
                    let start = crate::clock::now_us();
                    let mut n = 0u64;
                    while !flag.load(Ordering::Relaxed) {
                        if !all.lock().expect("not poisoned").iter().any(|d| d.info.id == id) {
                            lost.store(true, Ordering::Relaxed);
                            break;
                        }
                        let due = start + (n as f64 * period * 1e6) as i64;
                        let wait = due - crate::clock::now_us();
                        if wait > 0 {
                            thread::sleep(Duration::from_micros(wait as u64));
                        }
                        render(&mut buffer, device.info.channels, due + latency);
                        n += 1;
                    }
                })
                .map_err(|e| e.to_string())?;
            Ok(Box::new(StopOnDrop(stop)))
        }
    }

    struct StopOnDrop(Arc<AtomicBool>);

    impl Drop for StopOnDrop {
        fn drop(&mut self) {
            self.0.store(true, Ordering::Relaxed);
        }
    }
}

/// Real devices through cpal: WASAPI on Windows, CoreAudio on macOS (ALSA on Linux, for
/// development).
#[cfg(feature = "native")]
pub mod native {
    use super::*;
    use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

    pub struct Cpal {
        host: cpal::Host,
    }

    impl Cpal {
        pub fn new() -> Self {
            Self {
                host: cpal::default_host(),
            }
        }

        fn id(&self, device: &cpal::Device) -> Option<String> {
            device
                .name()
                .ok()
                .map(|name| format!("{}:{name}", self.host.id().name().to_lowercase()))
        }

        fn pick_config(device: &cpal::Device) -> Option<cpal::SupportedStreamConfig> {
            let configs: Vec<_> = device.supported_output_configs().ok()?.collect();
            let f32_48k = configs.iter().find(|c| {
                c.sample_format() == cpal::SampleFormat::F32
                    && c.min_sample_rate().0 <= RATE
                    && c.max_sample_rate().0 >= RATE
                    && c.channels() >= 2
            });
            if let Some(range) = f32_48k {
                return Some((*range).with_sample_rate(cpal::SampleRate(RATE)));
            }
            device.default_output_config().ok()
        }
    }

    impl Cpal {
        fn start(&self, id: &str, mut render: Render, lost: Arc<AtomicBool>) -> Result<cpal::Stream, String> {
            let device = self
                .host
                .output_devices()
                .map_err(|e| e.to_string())?
                .find(|d| self.id(d).as_deref() == Some(id))
                .ok_or("no such device")?;
            let supported = Self::pick_config(&device).ok_or("no usable configuration")?;
            let format = supported.sample_format();
            let config: cpal::StreamConfig = supported.into();
            let channels = config.channels;
            let on_error = move |error: cpal::StreamError| {
                log::warn!("audio device error: {error}");
                if matches!(error, cpal::StreamError::DeviceNotAvailable) {
                    lost.store(true, Ordering::Relaxed);
                }
            };
            let heard_at = |info: &cpal::OutputCallbackInfo| {
                let ts = info.timestamp();
                let delay = ts.playback.duration_since(&ts.callback).unwrap_or_default();
                crate::clock::now_us() + delay.as_micros() as i64
            };
            let stream = match format {
                cpal::SampleFormat::F32 => device.build_output_stream(
                    &config,
                    move |data: &mut [f32], info: &cpal::OutputCallbackInfo| {
                        render(data, channels, heard_at(info))
                    },
                    on_error,
                    None,
                ),
                cpal::SampleFormat::I16 => {
                    let mut scratch: Vec<f32> = vec![0.0; 16384];
                    device.build_output_stream(
                        &config,
                        move |data: &mut [i16], info: &cpal::OutputCallbackInfo| {
                            if scratch.len() < data.len() {
                                scratch.resize(data.len(), 0.0);
                            }
                            let block = &mut scratch[..data.len()];
                            render(block, channels, heard_at(info));
                            for (o, s) in data.iter_mut().zip(block.iter()) {
                                *o = (s.clamp(-1.0, 1.0) * 32767.0) as i16;
                            }
                        },
                        on_error,
                        None,
                    )
                }
                other => return Err(format!("sample format {other:?} is not supported")),
            }
            .map_err(|e| e.to_string())?;
            stream.play().map_err(|e| e.to_string())?;
            Ok(stream)
        }
    }

    impl Default for Cpal {
        fn default() -> Self {
            Self::new()
        }
    }

    /// cpal streams must be dropped on the thread that made them: each lives on its own
    /// thread until this handle is dropped.
    struct Handle(#[allow(dead_code)] std::sync::mpsc::Sender<()>);

    impl Backend for Cpal {
        fn devices(&self) -> Vec<DeviceInfo> {
            let default = self.host.default_output_device().and_then(|d| d.name().ok());
            let Ok(devices) = self.host.output_devices() else {
                return Vec::new();
            };
            devices
                .filter_map(|device| {
                    let config = Self::pick_config(&device)?;
                    let name = device.name().ok()?;
                    let lower = name.to_lowercase();
                    Some(DeviceInfo {
                        id: self.id(&device)?,
                        default: default.as_deref() == Some(name.as_str()),
                        bluetooth: lower.contains("bluetooth")
                            || lower.contains("airpods")
                            || lower.contains("hands-free"),
                        channels: config.channels(),
                        sample_rate: config.sample_rate().0,
                        latency_ms: None,
                        name,
                    })
                })
                .collect()
        }

        fn open(&self, id: &str, render: Render, lost: Arc<AtomicBool>) -> Result<Box<dyn Send>, String> {
            let id = id.to_string();
            let host_id = self.host.id();
            let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
            let (stop_tx, stop_rx) = std::sync::mpsc::channel::<()>();
            std::thread::Builder::new()
                .name(format!("audio {id}"))
                .spawn(move || {
                    let host = cpal::host_from_id(host_id).expect("the host it was listed on");
                    let cpal = Cpal { host };
                    match cpal.start(&id, render, lost) {
                        Ok(stream) => {
                            let _ = ready_tx.send(Ok(()));
                            // Until the handle is dropped.
                            let _ = stop_rx.recv();
                            drop(stream);
                        }
                        Err(error) => {
                            let _ = ready_tx.send(Err(error));
                        }
                    }
                })
                .map_err(|e| e.to_string())?;
            ready_rx.recv().map_err(|e| e.to_string())??;
            Ok(Box::new(Handle(stop_tx)))
        }
    }
}
