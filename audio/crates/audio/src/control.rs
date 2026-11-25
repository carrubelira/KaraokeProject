//! The control thread: it ties the server's session, the decoding and the audio outputs
//! together (decision 011).
//!
//! The song on is decoded as soon as the server cues it, and the next one in the queue right
//! after, so the operator's next cue finds it already in memory. kp-audio reports its state on
//! every change that matters to the server (the song is ready, an output went away) without
//! waiting for the next once-a-second status.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use std::sync::mpsc::{Receiver, Sender, channel};
use std::thread;
use std::time::{Duration, Instant};

use kp_clock::Anchor;
use kp_core::{Effects, StageCore};
use kp_mix::PitcherFactory;
use kp_proto::{AudioDevice, AudioError, AudioErrorCode, AudioMessage, AudioStatus, OutputPolicy};

use crate::audio::{Outputs, Update};
use crate::link::{self, Event};
use crate::program::{self, Program, Store};

pub struct Options {
    pub diagnose: bool,
}

/// A decode that finished: the song, and whether it was for the song on or the next one.
type Loaded = (kp_proto::Program, Result<Program, String>);

pub struct Engine {
    pub core: StageCore,
    pub outputs: Outputs,
    events: Receiver<Event>,
    to_server: Option<Sender<AudioMessage>>,
    loaded: Receiver<Loaded>,
    loaded_tx: Sender<Loaded>,
    store: Arc<Store>,
    program: Option<Arc<Program>>,
    /// The next song in the queue, decoded ahead.
    ahead: Option<Arc<Program>>,
    /// Songs being decoded now (item id, manifest).
    decoding: HashSet<(String, String)>,
    options: Options,
    factory: PitcherFactory,
    connected: bool,
    lost_master: bool,
    /// What does not work right now, by device (or a name for kp-audio itself), for the server.
    errors: HashMap<String, AudioError>,
    /// Something the server should hear about before the next regular status.
    news: bool,
    started: Instant,
}

fn error(code: AudioErrorCode, device: Option<&str>, message: String) -> AudioError {
    AudioError {
        code,
        device: device.map(str::to_string),
        item_id: None,
        message,
    }
}

fn key(program: &kp_proto::Program) -> (String, String) {
    (program.item.id.clone(), program.manifest.clone())
}

impl Engine {
    pub fn start(url: String, token: String, store: Store, outputs: Outputs, options: Options) -> Self {
        let (events_tx, events) = channel();
        let (to_server, outgoing) = channel();
        link::spawn(url, token, events_tx, outgoing);
        let (loaded_tx, loaded) = channel();
        Self {
            core: StageCore::new(),
            outputs,
            events,
            to_server: Some(to_server),
            loaded,
            loaded_tx,
            store: Arc::new(store),
            program: None,
            ahead: None,
            decoding: HashSet::new(),
            options,
            factory: crate::pitch::factory(),
            connected: false,
            lost_master: false,
            errors: HashMap::new(),
            news: false,
            started: Instant::now(),
        }
    }

    fn send(&self, message: AudioMessage) {
        if let Some(tx) = &self.to_server {
            let _ = tx.send(message);
        }
    }

    fn default_device(&self) -> Option<String> {
        let devices = self.outputs.devices();
        devices
            .iter()
            .find(|d| d.default)
            .or(devices.first())
            .map(|d| d.id.clone())
    }

    fn master_id(&self) -> Option<String> {
        let devices = self.outputs.devices();
        self.core
            .config
            .routing
            .master
            .clone()
            .filter(|id| devices.iter().any(|d| &d.id == id))
            .or_else(|| self.default_device())
    }

    /// Opens the outputs the routing names (or the default one) and gives each its mixer.
    fn reconfigure(&mut self) {
        // Every output is tried again: what fails now is reported again below.
        self.errors.retain(|_, e| e.code != AudioErrorCode::OutputFailed);
        self.news = true;
        let Some(master) = self.master_id() else {
            log::warn!("no audio output");
            self.errors.insert(
                "outputs".into(),
                error(
                    AudioErrorCode::OutputFailed,
                    None,
                    "No audio output on this machine".into(),
                ),
            );
            return;
        };
        let routing = program::routing(&self.core.config.routing, &master);
        let mut wanted: Vec<String> = routing.routes.iter().map(|r| r.output.clone()).collect();
        if !wanted.contains(&master) {
            wanted.push(master.clone());
        }
        wanted.sort();
        wanted.dedup();
        for failed in self.outputs.reconcile(&wanted, &master) {
            log::warn!("audio output {failed} is not available");
            let message = format!("The audio output {failed} could not be opened");
            self.errors.insert(
                failed.clone(),
                error(AudioErrorCode::OutputFailed, Some(&failed), message),
            );
        }
        for (id, output) in &self.outputs.open {
            let calibration = self.core.config.calibration_ms.get(id).copied().unwrap_or(0.0);
            let _ = output
                .updates
                .send(Update::CalibrationUs((calibration * 1000.0) as i64));
        }
        self.install_mixers();
    }

    fn install_mixers(&self) {
        let Some(program) = &self.program else {
            self.outputs.broadcast(|| Update::Unload);
            return;
        };
        // The output already keeping time, not a fresh look at the system's devices: listing
        // them can come back empty or short for a moment (a monitor's audio coming and going).
        let master = self
            .outputs
            .open
            .iter()
            .find(|(_, output)| output.is_master)
            .map(|(id, _)| id.clone())
            .or_else(|| self.master_id());
        let Some(master) = master else {
            // Nowhere to send the new song: never let the previous one go on playing.
            log::warn!("no audio output for {}", program.title);
            self.outputs.broadcast(|| Update::Unload);
            return;
        };
        let routing = program::routing(&self.core.config.routing, &master);
        for id in self.outputs.open.keys() {
            let mixer = program.mixer(
                id,
                &routing,
                &self.factory,
                self.core.session.semitones as f32,
                self.core.session.volume as f32,
            );
            self.outputs.send(id, Update::Mixer(Box::new(mixer)));
        }
    }

    fn apply(&mut self, effects: Effects) {
        if effects.config {
            self.reconfigure();
        }
        let ahead = effects.upcoming || effects.load.is_some();
        if let Some(wanted) = effects.load {
            // Another song: the one loaded goes at once, so the new song's timeline never drives
            // the previous song while the new one decodes.
            if self.program.is_some() {
                self.program = None;
                self.outputs.broadcast(|| Update::Unload);
            }
            self.news = true;
            match self.ahead.take() {
                Some(ahead) if ahead.program.same_as(&wanted) => self.install(ahead),
                other => {
                    self.ahead = other;
                    self.decode(wanted);
                }
            }
        }
        if effects.unload {
            self.program = None;
            self.news = true;
            self.outputs.broadcast(|| Update::Unload);
        }
        if effects.pitch {
            let semitones = self.core.session.semitones as f32;
            self.outputs.broadcast(|| Update::Semitones(semitones));
        }
        if effects.volume {
            let volume = self.core.session.volume as f32;
            self.outputs.broadcast(|| Update::Volume(volume));
        }
        if ahead {
            self.decode_ahead();
        }
    }

    /// Decodes a song on a thread of its own.
    fn decode(&mut self, wanted: kp_proto::Program) {
        if !self.decoding.insert(key(&wanted)) {
            return; // already on its way
        }
        let store = self.store.clone();
        let tx = self.loaded_tx.clone();
        thread::spawn(move || {
            let result = Program::load(wanted.clone(), &store);
            let _ = tx.send((wanted, result));
        });
    }

    /// The first song after the one on, so a cue of it finds it in memory.
    fn decode_ahead(&mut self) {
        let Some(next) = self.core.session.upcoming.first().cloned() else {
            self.ahead = None;
            return;
        };
        let have = self.ahead.as_ref().is_some_and(|a| a.program.same_as(&next))
            || self.program.as_ref().is_some_and(|p| p.program.same_as(&next));
        if !have {
            self.decode(next);
        }
    }

    fn install(&mut self, program: Arc<Program>) {
        if !self.core.loaded(&program.program) {
            return;
        }
        log::info!("loaded {} ({} tracks)", program.title, program.tracks.len());
        self.errors.remove("load");
        self.program = Some(program);
        self.install_mixers();
        self.news = true;
    }

    fn decoded(&mut self, wanted: kp_proto::Program, result: Result<Program, String>) {
        self.decoding.remove(&key(&wanted));
        match result {
            Ok(program) => {
                let program = Arc::new(program);
                let on = self
                    .core
                    .session
                    .current
                    .as_ref()
                    .is_some_and(|c| c.same_as(&wanted));
                if on {
                    self.install(program);
                } else if self
                    .core
                    .session
                    .upcoming
                    .first()
                    .is_some_and(|n| n.same_as(&wanted))
                {
                    self.ahead = Some(program);
                }
            }
            Err(problem) => {
                log::warn!("could not load the song: {problem}");
                let mut failed = error(AudioErrorCode::LoadFailed, None, problem);
                failed.item_id = Some(wanted.item.id.clone());
                self.errors.insert("load".into(), failed);
                self.news = true;
            }
        }
    }

    fn status(&self, now: i64) -> AudioStatus {
        let mut status = self.core.status(now);
        let master = self.master_id();
        status.devices = self
            .outputs
            .devices()
            .into_iter()
            .map(|d| AudioDevice {
                connected: !self
                    .errors
                    .get(&d.id)
                    .is_some_and(|e| e.code == AudioErrorCode::OutputLost),
                default: d.default,
                latency_ms: d.latency_ms,
                bluetooth: d.bluetooth,
                channels: d.channels,
                sample_rate: d.sample_rate,
                name: d.name,
                id: d.id,
            })
            .collect();
        for (id, output) in &self.outputs.open {
            status
                .sync
                .insert(format!("{id}.correction_ppm"), output.stats.correction_ppm());
            status.sync.insert(
                format!("{id}.jumps"),
                output.stats.jumps.load(std::sync::atomic::Ordering::Relaxed) as f64,
            );
            if self.options.diagnose {
                status.sync.insert(format!("{id}.rms"), output.stats.rms());
            }
        }
        if let (Some(master), Some(snapshot)) = (&master, self.outputs.shared.master.snapshot()) {
            // How far the heard sound is from where the timeline says it should be.
            if let Some(expected) = self.core.timeline.position_at(snapshot.heard_at)
                && snapshot.rate > 0.0
            {
                status.sync.insert(
                    format!("{master}.offset_ms"),
                    (snapshot.position - expected) * 1e3,
                );
            }
        }
        let mut errors: Vec<AudioError> = self.errors.values().cloned().collect();
        if self.lost_master {
            errors.push(error(
                AudioErrorCode::MasterLost,
                self.core.config.routing.master.as_deref(),
                "The output that keeps time went away: playback is paused until it is back".into(),
            ));
        }
        errors.sort_by(|a, b| a.device.cmp(&b.device));
        status.errors = errors;
        status
    }

    fn watch_devices(&mut self, now: i64) {
        let lost = self.outputs.take_lost();
        let present: Vec<String> = self.outputs.devices().into_iter().map(|d| d.id).collect();
        self.errors
            .retain(|id, e| e.code != AudioErrorCode::OutputLost || present.contains(id));
        if lost.is_empty() {
            // A device that came back is opened again.
            if self.lost_master
                && self
                    .master_id()
                    .is_some_and(|m| self.outputs.devices().iter().any(|d| d.id == m))
            {
                self.lost_master = false;
                self.reconfigure();
            }
            return;
        }
        let master = self
            .core
            .config
            .routing
            .master
            .clone()
            .or_else(|| self.default_device());
        for id in lost {
            let policy = self.core.config.routing.policy(&id);
            log::warn!("audio output {id} went away ({policy:?})");
            self.errors.insert(
                id.clone(),
                error(
                    AudioErrorCode::OutputLost,
                    Some(&id),
                    format!("The audio output {id} went away"),
                ),
            );
            if master.as_deref() == Some(id.as_str()) {
                // The server hears of it at once and pauses every screen too.
                self.lost_master = true;
            }
            if policy == OutputPolicy::Pause
                && let Some(position) = self.core.timeline.position_at(now)
            {
                self.core.timeline.push(Anchor::paused(position, now));
            }
        }
        self.news = true;
        self.reconfigure();
    }

    /// One turn of the loop.
    pub fn step(&mut self) {
        let now = crate::clock::now_us();
        while let Ok(event) = self.events.try_recv() {
            match event {
                Event::Connected => {
                    self.connected = true;
                    log::info!("connected to the server");
                    // A restarted server may count from another base: learn its clock again.
                    self.core.clock = kp_core::ServerClock::default();
                    // A burst of time requests: the best of them sets the offset at once.
                    for _ in 0..4 {
                        self.send(AudioMessage::TimeRequest {
                            sent: crate::clock::now_us(),
                        });
                    }
                    self.news = true;
                }
                Event::Disconnected(reason) => {
                    if self.connected {
                        log::warn!("lost the server ({reason}); playing on");
                    }
                    self.connected = false;
                }
                Event::Message(message, received) => {
                    let effects = self.core.handle(*message, received);
                    self.apply(effects);
                }
            }
        }
        while let Ok((wanted, result)) = self.loaded.try_recv() {
            self.decoded(wanted, result);
        }
        self.core.tick(now);
        if let Ok(mut timeline) = self.outputs.shared.timeline.lock() {
            *timeline = self.core.timeline.clone();
        }
        self.outputs.collect_garbage();
    }

    /// Runs the loop until `stop` is set (or forever).
    pub fn run(&mut self, stop: Option<Arc<std::sync::atomic::AtomicBool>>) {
        self.reconfigure();
        let mut last_status = Instant::now() - Duration::from_secs(5);
        let mut last_time = Instant::now();
        let mut last_watch = Instant::now();
        while !stop
            .as_ref()
            .is_some_and(|s| s.load(std::sync::atomic::Ordering::Relaxed))
        {
            self.step();
            let now = crate::clock::now_us();
            if self.news || last_status.elapsed() >= Duration::from_secs(1) {
                self.news = false;
                last_status = Instant::now();
                self.send(AudioMessage::Status {
                    status: self.status(now),
                });
                if self.options.diagnose {
                    self.diagnose(now);
                }
            }
            if last_time.elapsed() >= Duration::from_secs(5) {
                last_time = Instant::now();
                self.send(AudioMessage::TimeRequest {
                    sent: crate::clock::now_us(),
                });
            }
            if last_watch.elapsed() >= Duration::from_secs(2) {
                last_watch = Instant::now();
                self.watch_devices(now);
            }
            thread::sleep(Duration::from_millis(2));
        }
        self.to_server = None;
    }

    fn diagnose(&self, now: i64) {
        let status = self.status(now);
        let mut line = format!(
            "t={:.1}s state={:?} pos={:.3}",
            self.started.elapsed().as_secs_f64(),
            status.state,
            status.position.unwrap_or(0.0)
        );
        for (key, value) in &status.sync {
            line.push_str(&format!(" {key}={value:.3}"));
        }
        log::info!("{line}");
    }
}
