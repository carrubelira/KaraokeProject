//! The control thread: it ties the server's orders, the downloads, the audio outputs and the
//! screens together (plan v4 §6).

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::mpsc::{Receiver, Sender, channel};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use kp_cache::{BlobCache, Needs, Preparer};
use kp_clock::Anchor;
use kp_core::{Effects, PlayerCore, Timeline};
use kp_mix::PitcherFactory;
use kp_net::Server;
use kp_proto::{
    AudioDevice, CacheState, Display, Manifest, OutputPolicy, PlayerMessage, PlayerOutputs, PlaylistItem,
};

use crate::audio::{Outputs, Shared, Update};
use crate::link::{self, Event};
use crate::prepare::{self, Report, ServerSource};
use crate::program::{self, Program};

/// What the screens need each frame; the control thread keeps it current.
#[derive(Default)]
pub struct View {
    pub program: Option<Arc<Program>>,
    pub timeline: Timeline,
    pub config: kp_proto::PlayerConfig,
    /// The item cued next, for the waiting screen.
    pub upcoming: Option<PlaylistItem>,
    pub upcoming_title: Option<(String, Option<String>)>,
    pub state: kp_proto::PlaybackState,
    pub download: Option<(CacheState, f64)>,
    pub semitones: f64,
    pub connected: bool,
}

pub struct Options {
    pub data_dir: PathBuf,
    pub same_host: bool,
    pub diagnose: bool,
    pub needs: Needs,
}

pub struct Player {
    pub core: PlayerCore,
    pub outputs: Outputs,
    pub view: Arc<Mutex<View>>,
    /// Displays the screens report (the renderer fills it; headless: one virtual display).
    pub displays: Arc<Mutex<Vec<Display>>>,
    events: Receiver<Event>,
    to_server: Option<Sender<PlayerMessage>>,
    wants: Sender<Vec<PlaylistItem>>,
    reports: Receiver<Report>,
    loaded: Receiver<Result<Program, String>>,
    loaded_tx: Sender<Result<Program, String>>,
    manifests: HashMap<String, (String, Manifest)>,
    titles: HashMap<String, (String, Option<String>)>,
    pending: Option<PlaylistItem>,
    program: Option<Arc<Program>>,
    cache: BlobCache,
    source: Arc<ServerSource>,
    options: Options,
    factory: PitcherFactory,
    connected: bool,
    lost_master: bool,
    started: Instant,
}

impl Player {
    pub fn start(server: Server, outputs: Outputs, options: Options) -> std::io::Result<Self> {
        let cache = BlobCache::new(options.data_dir.join("blobs"))?;
        let (events_tx, events) = channel();
        let (to_server, outgoing) = channel();
        link::spawn(server.clone(), events_tx, outgoing);
        let (wants, wants_rx) = channel();
        let (reports_tx, reports) = channel();
        let source = ServerSource {
            server: server.clone(),
            same_host: options.same_host,
        };
        prepare::spawn(cache.clone(), source, options.needs.clone(), wants_rx, reports_tx);
        let (loaded_tx, loaded) = channel();
        Ok(Self {
            core: PlayerCore::new(),
            outputs,
            view: Arc::new(Mutex::new(View::default())),
            displays: Arc::new(Mutex::new(Vec::new())),
            events,
            to_server: Some(to_server),
            wants,
            reports,
            loaded,
            loaded_tx,
            manifests: HashMap::new(),
            titles: HashMap::new(),
            pending: None,
            program: None,
            cache,
            source: Arc::new(ServerSource {
                server,
                same_host: options.same_host,
            }),
            options,
            factory: crate::pitch::factory(),
            connected: false,
            lost_master: false,
            started: Instant::now(),
        })
    }

    pub fn shared(&self) -> Arc<Shared> {
        self.outputs.shared.clone()
    }

    fn send(&self, message: PlayerMessage) {
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
        let Some(master) = self.master_id() else {
            log::warn!("no audio output");
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
        }
        for (id, output) in &self.outputs.open {
            let calibration = self
                .core
                .config
                .calibration
                .audio_ms
                .get(id)
                .copied()
                .unwrap_or(0.0);
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
        let Some(master) = self.master_id() else { return };
        let routing = program::routing(&self.core.config.routing, &master);
        for id in self.outputs.open.keys() {
            let mixer = program.mixer(
                id,
                &routing,
                &self.factory,
                self.core.transport.semitones as f32,
                self.core.transport.volume as f32,
            );
            self.outputs.send(id, Update::Mixer(Box::new(mixer)));
        }
    }

    fn apply(&mut self, effects: Effects) {
        if effects.config {
            self.reconfigure();
            if let Ok(mut view) = self.view.lock() {
                view.config = self.core.config.clone();
            }
        }
        if let Some(item) = effects.load {
            self.pending = Some(item);
            self.try_load();
        }
        if effects.unload {
            self.pending = None;
            self.program = None;
            self.outputs.broadcast(|| Update::Unload);
        }
        if effects.pitch {
            let semitones = self.core.transport.semitones as f32;
            self.outputs.broadcast(|| Update::Semitones(semitones));
        }
        if effects.volume {
            let volume = self.core.transport.volume as f32;
            self.outputs.broadcast(|| Update::Volume(volume));
        }
        if effects.playlist || effects.config {
            let _ = self.wants.send(self.core.prefetch(3));
        }
    }

    /// Loads the pending song once its files are here, on a thread of its own.
    fn try_load(&mut self) {
        let Some(item) = self.pending.clone() else { return };
        let Some((_, manifest)) = self.manifests.get(&item.content_id).cloned() else {
            let _ = self.wants.send(self.core.prefetch(3));
            return;
        };
        self.pending = None;
        let cache = self.cache.clone();
        let source = self.source.clone();
        let needs = self.options.needs.clone();
        let tx = self.loaded_tx.clone();
        thread::spawn(move || {
            let preparer = Preparer {
                cache: &cache,
                source: source.as_ref(),
                needs,
            };
            let _ = tx.send(Program::load(item, manifest, &preparer));
        });
    }

    fn installed(&mut self, program: Program) {
        let current = self.core.transport.item.as_ref().map(|i| i.id.clone());
        if current.as_deref() != Some(program.item.id.as_str()) {
            return; // another song was asked for meanwhile
        }
        log::info!(
            "loaded {} ({} tracks)",
            program.manifest.title,
            program.tracks.len()
        );
        self.core.duration = Some(program.manifest.duration);
        self.program = Some(Arc::new(program));
        self.install_mixers();
    }

    fn status(&self, now: i64) -> kp_proto::PlayerStatus {
        let mut status = self.core.status(now);
        let master = self.master_id();
        status.outputs = PlayerOutputs {
            displays: self.displays.lock().map(|d| d.clone()).unwrap_or_default(),
            audio: self
                .outputs
                .devices()
                .into_iter()
                .map(|d| AudioDevice {
                    connected: true,
                    default: d.default,
                    latency_ms: d.latency_ms,
                    bluetooth: d.bluetooth,
                    channels: d.channels,
                    sample_rate: d.sample_rate,
                    name: d.name,
                    id: d.id,
                })
                .collect(),
        };
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
        if let (Some(master), Some(snapshot)) = (master, self.outputs.shared.master.snapshot()) {
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
        if self.lost_master {
            status.sync.insert("master_lost".into(), 1.0);
        }
        status
    }

    fn watch_devices(&mut self, now: i64) {
        let lost = self.outputs.take_lost();
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
            let is_master = master.as_deref() == Some(id.as_str());
            log::warn!("audio output {id} went away ({:?})", policy);
            if is_master {
                self.lost_master = true;
            }
            if policy == OutputPolicy::Pause
                && let Some(position) = self.core.timeline.position_at(now)
            {
                self.core.timeline.push(Anchor::paused(position, now));
            }
        }
        self.reconfigure();
    }

    fn publish_view(&self, now: i64) {
        let upcoming = self
            .core
            .transport
            .item
            .as_ref()
            .and_then(|i| self.core.next_item(&i.id))
            .or_else(|| self.core.playlist.as_ref().and_then(|p| p.items.first().cloned()));
        let download = self.core.transport.item.as_ref().and_then(|item| {
            self.core
                .cache
                .iter()
                .find(|c| c.content_id == item.content_id)
                .map(|c| (c.state, c.fraction))
        });
        if let Ok(mut view) = self.view.lock() {
            view.program = self.program.clone();
            view.timeline = self.core.timeline.clone();
            view.upcoming_title = upcoming
                .as_ref()
                .and_then(|i| self.titles.get(&i.content_id).cloned());
            view.upcoming = upcoming;
            view.state = self.core.state(now);
            view.download = download;
            view.semitones = self.core.transport.semitones;
            view.connected = self.connected;
        }
    }

    /// One turn of the loop; returns false once the server link is gone for good.
    pub fn step(&mut self) {
        let now = crate::clock::now_us();
        while let Ok(event) = self.events.try_recv() {
            match event {
                Event::Connected => {
                    self.connected = true;
                    log::info!("connected to {}", self.source.server.base());
                    self.send(PlayerMessage::TimeRequest {
                        sent: crate::clock::now_us(),
                    });
                }
                Event::Disconnected(reason) => {
                    if self.connected {
                        log::warn!("lost the server ({reason}); playing on");
                    }
                    self.connected = false;
                }
                Event::Message(message, received) => {
                    let effects = self.core.handle(message, received);
                    self.apply(effects);
                }
            }
        }
        while let Ok(report) = self.reports.try_recv() {
            match report {
                Report::Cache(update) => self.core.cache_update(update, now),
                Report::Ready {
                    item,
                    manifest,
                    manifest_sha,
                } => {
                    self.titles.insert(
                        item.content_id.clone(),
                        (manifest.title.clone(), manifest.artist.clone()),
                    );
                    self.manifests
                        .insert(item.content_id.clone(), (manifest_sha, *manifest));
                    if self
                        .pending
                        .as_ref()
                        .is_some_and(|p| p.content_id == item.content_id)
                    {
                        self.try_load();
                    }
                }
            }
        }
        while let Ok(loaded) = self.loaded.try_recv() {
            match loaded {
                Ok(program) => self.installed(program),
                Err(error) => log::warn!("could not load the song: {error}"),
            }
        }
        let effects = self.core.tick(now);
        if effects != Effects::default() {
            self.apply(effects);
        }
        if let Ok(mut timeline) = self.outputs.shared.timeline.lock() {
            *timeline = self.core.timeline.clone();
        }
        self.outputs.collect_garbage();
        self.publish_view(now);
    }

    /// Runs the loop until `stop` is set (or forever).
    pub fn run(&mut self, stop: Option<Arc<std::sync::atomic::AtomicBool>>) {
        self.reconfigure();
        let mut last_status = Instant::now() - Duration::from_secs(5);
        let mut last_time = Instant::now();
        let mut last_watch = Instant::now();
        let lock = self.options.data_dir.join("playing");
        while !stop
            .as_ref()
            .is_some_and(|s| s.load(std::sync::atomic::Ordering::Relaxed))
        {
            self.step();
            let now = crate::clock::now_us();
            if last_status.elapsed() >= Duration::from_secs(1) {
                last_status = Instant::now();
                self.send(PlayerMessage::Status {
                    status: self.status(now),
                });
                if self.core.state(now) == kp_proto::PlaybackState::Playing {
                    // Tells a worker on this machine to leave the GPU alone (karaoke-worker
                    // --player-lock).
                    let _ = std::fs::write(&lock, b"playing");
                }
                if self.options.diagnose {
                    self.diagnose(now);
                }
            }
            if last_time.elapsed() >= Duration::from_secs(5) {
                last_time = Instant::now();
                self.send(PlayerMessage::TimeRequest {
                    sent: crate::clock::now_us(),
                });
            }
            if last_watch.elapsed() >= Duration::from_secs(2) {
                last_watch = Instant::now();
                self.watch_devices(now);
            }
            thread::sleep(Duration::from_millis(5));
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
