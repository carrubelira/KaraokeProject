//! What the player decides, apart from how it plays (plan v4 §6).
//!
//! - [`ServerClock`] learns the offset between the server's clock and this machine's monotonic
//!   clock from `time` messages (the sample with the shortest round trip wins), so an anchor the
//!   server sets "300 ms from now" lands on the same instant here.
//! - [`Timeline`] holds the anchors in local time; the audio callback asks it the song position
//!   heard at any instant, and a change scheduled for later takes effect exactly then.
//! - [`PlayerCore`] applies the server's messages (config, playlist, orders), knows which song is
//!   on, what to download first, when a song ends, and builds the status the server shows.

use kp_clock::{Anchor, Micros};
use kp_proto::{
    CacheState, Command, ContentCache, PlaybackState, PlayerCommand, PlayerConfig, PlayerStatus, Playlist,
    PlaylistItem, ServerMessage,
};

/// Offset from local microseconds to the server's.
#[derive(Clone, Debug, Default)]
pub struct ServerClock {
    offset: Option<i64>,
    best_rtt: Option<i64>,
    samples: u32,
}

impl ServerClock {
    /// A `time` answer: the server's `now`, and when the request left and the answer came back,
    /// on the local clock. Without a request (`sent` = None) it is a rough first guess.
    pub fn observe(&mut self, server_now: i64, sent: Option<i64>, received: i64) {
        self.samples += 1;
        match sent {
            Some(sent) => {
                let rtt = (received - sent).max(0);
                // A sample with a much longer round trip says less; older best samples age out
                // slowly so a changed route is learnt.
                let aged = self
                    .best_rtt
                    .map(|best| best + 200 * i64::from(self.samples.min(50)));
                if aged.is_none_or(|best| rtt <= best) || self.best_rtt.is_none() {
                    self.best_rtt = Some(rtt);
                    self.offset = Some(server_now - (sent + rtt / 2));
                    self.samples = 0;
                }
            }
            None => {
                if self.offset.is_none() {
                    self.offset = Some(server_now - received);
                }
            }
        }
    }

    pub fn offset(&self) -> Option<i64> {
        self.offset
    }

    pub fn rtt(&self) -> Option<i64> {
        self.best_rtt
    }

    pub fn to_local(&self, server: i64) -> i64 {
        server - self.offset.unwrap_or(0)
    }

    pub fn to_server(&self, local: i64) -> i64 {
        local + self.offset.unwrap_or(0)
    }
}

/// Anchors in local time; the position at an instant follows the last one in effect.
#[derive(Clone, Debug, Default)]
pub struct Timeline {
    anchors: Vec<Anchor>,
}

impl Timeline {
    pub fn new(anchor: Anchor) -> Self {
        Self {
            anchors: vec![anchor],
        }
    }

    /// Schedules a change; anything scheduled after it is dropped (a newer order wins).
    pub fn push(&mut self, anchor: Anchor) {
        self.anchors.retain(|a| a.instant < anchor.instant);
        self.anchors.push(anchor);
    }

    pub fn clear(&mut self) {
        self.anchors.clear();
    }

    pub fn is_empty(&self) -> bool {
        self.anchors.is_empty()
    }

    /// The anchor in effect at `instant` (before the first one, the first one held paused).
    pub fn anchor_at(&self, instant: Micros) -> Option<Anchor> {
        let first = *self.anchors.first()?;
        let current = self.anchors.iter().rev().find(|a| a.instant <= instant).copied();
        Some(current.unwrap_or(Anchor::paused(first.position, first.instant)))
    }

    pub fn position_at(&self, instant: Micros) -> Option<f64> {
        self.anchor_at(instant).map(|a| a.position_at(instant).max(0.0))
    }

    pub fn rate_at(&self, instant: Micros) -> f64 {
        self.anchor_at(instant).map_or(0.0, |a| a.rate)
    }

    /// Drops anchors that no longer matter (all but the one in effect at `instant`).
    pub fn compact(&mut self, instant: Micros) {
        if let Some(index) = self.anchors.iter().rposition(|a| a.instant <= instant) {
            self.anchors.drain(..index);
        }
    }

    /// The next instant a change is scheduled at, after `instant`.
    pub fn next_change(&self, instant: Micros) -> Option<Micros> {
        self.anchors.iter().map(|a| a.instant).find(|&t| t > instant)
    }
}

/// What the player does when its song ends.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AtEnd {
    /// Loads the next item paused, so the next singer gets ready (the waiting screen shows it).
    CueNext,
    Stop,
}

/// What the engine should be playing; the core changes it, the engine follows.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Transport {
    pub item: Option<PlaylistItem>,
    pub semitones: f64,
    pub volume: f64,
}

pub struct PlayerCore {
    pub clock: ServerClock,
    pub config: PlayerConfig,
    pub playlist: Option<Playlist>,
    pub timeline: Timeline,
    pub transport: Transport,
    pub cache: Vec<ContentCache>,
    /// Length of the song on, from its manifest (once loaded).
    pub duration: Option<f64>,
    pub at_end: AtEnd,
    /// An order whose song was not ready at its instant: it starts once the song is.
    waiting_for: Option<(String, Anchor)>,
    pub last_command: Option<String>,
}

impl Default for PlayerCore {
    fn default() -> Self {
        Self {
            clock: ServerClock::default(),
            config: PlayerConfig::default(),
            playlist: None,
            timeline: Timeline::default(),
            transport: Transport {
                item: None,
                semitones: 0.0,
                volume: 1.0,
            },
            cache: Vec::new(),
            duration: None,
            at_end: AtEnd::CueNext,
            waiting_for: None,
            last_command: None,
        }
    }
}

/// What changed for the engine after a message.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Effects {
    /// A different song must be loaded (its tracks decoded).
    pub load: Option<PlaylistItem>,
    pub unload: bool,
    pub config: bool,
    pub pitch: bool,
    pub volume: bool,
    pub playlist: bool,
}

impl PlayerCore {
    pub fn new() -> Self {
        Self::default()
    }

    fn item(&self, item_id: &str) -> Option<PlaylistItem> {
        self.playlist
            .as_ref()?
            .items
            .iter()
            .find(|i| i.id == item_id)
            .cloned()
    }

    pub fn is_ready(&self, content_id: &str) -> bool {
        self.cache
            .iter()
            .any(|c| c.content_id == content_id && c.state == CacheState::Ready)
    }

    /// Applies a server message received at local instant `now`.
    pub fn handle(&mut self, message: ServerMessage, now: Micros) -> Effects {
        let mut effects = Effects::default();
        match message {
            ServerMessage::Time {
                now: server_now,
                sent,
            } => self.clock.observe(server_now, sent, now),
            ServerMessage::Config { config } => {
                self.config = config;
                effects.config = true;
            }
            ServerMessage::Playlist { playlist } => {
                if let Some(current) = &self.transport.item {
                    // The item on may have been edited (entry point, key) or removed.
                    if let Some(updated) = playlist.items.iter().find(|i| i.id == current.id) {
                        if updated.semitones != self.transport.semitones {
                            self.transport.semitones = updated.semitones;
                            effects.pitch = true;
                        }
                        self.transport.item = Some(updated.clone());
                    }
                }
                self.playlist = Some(playlist);
                effects.playlist = true;
            }
            ServerMessage::Command { command } => self.command(command, now, &mut effects),
        }
        effects
    }

    fn local(&self, anchor: Anchor) -> Anchor {
        Anchor {
            instant: self.clock.to_local(anchor.instant),
            ..anchor
        }
    }

    fn command(&mut self, command: PlayerCommand, now: Micros, effects: &mut Effects) {
        self.last_command = Some(command.id.clone());
        match command.command {
            Command::Load => {
                let Some(item) = command.item_id.as_deref().and_then(|id| self.item(id)) else {
                    log::warn!("load of an item not in the playlist");
                    return;
                };
                let anchor = command
                    .anchor
                    .map_or(Anchor::paused(item.start.unwrap_or(0.0), now), |a| self.local(a));
                let changed = self
                    .transport
                    .item
                    .as_ref()
                    .map(|i| (&i.id, &i.content_id, &i.manifest))
                    != Some((&item.id, &item.content_id, &item.manifest));
                if changed {
                    effects.load = Some(item.clone());
                    self.duration = None;
                }
                if self.transport.semitones != item.semitones {
                    effects.pitch = true;
                }
                self.transport.semitones = item.semitones;
                self.transport.item = Some(item.clone());
                self.timeline = Timeline::new(Anchor::paused(anchor.position, now.min(anchor.instant)));
                if anchor.rate > 0.0 && !self.is_ready(&item.content_id) {
                    self.waiting_for = Some((item.id.clone(), anchor));
                } else {
                    self.timeline.push(anchor);
                }
            }
            Command::Play | Command::Pause | Command::Seek => {
                if let Some(anchor) = command.anchor {
                    let anchor = self.local(anchor);
                    match &self.transport.item {
                        Some(item) if anchor.rate > 0.0 && !self.is_ready(&item.content_id) => {
                            self.waiting_for = Some((item.id.clone(), anchor));
                        }
                        _ => {
                            if anchor.rate == 0.0 {
                                self.waiting_for = None;
                            }
                            if self.timeline.is_empty() {
                                self.timeline =
                                    Timeline::new(Anchor::paused(anchor.position, now.min(anchor.instant)));
                            }
                            self.timeline.push(anchor);
                        }
                    }
                }
            }
            Command::Volume => {
                if let Some(value) = command.value {
                    self.transport.volume = value.clamp(0.0, 2.0);
                    effects.volume = true;
                }
            }
            Command::Pitch => {
                if let Some(value) = command.value {
                    self.transport.semitones = value.clamp(-12.0, 12.0);
                    effects.pitch = true;
                }
            }
            Command::Stop => {
                self.transport.item = None;
                self.timeline.clear();
                self.waiting_for = None;
                self.duration = None;
                effects.unload = true;
            }
            Command::Reload => {
                if let Some(item) = self.transport.item.clone() {
                    effects.load = Some(item);
                }
            }
            Command::Next | Command::Previous => {
                // The server turns these into `load`; nothing to do if one arrives.
            }
        }
    }

    /// A song finished downloading (or failed): updates the cache list; an order that was
    /// waiting for it starts now.
    pub fn cache_update(&mut self, update: ContentCache, now: Micros) {
        let ready = update.state == CacheState::Ready;
        let content = update.content_id.clone();
        match self.cache.iter_mut().find(|c| c.content_id == update.content_id) {
            Some(entry) => *entry = update,
            None => self.cache.push(update),
        }
        if ready && let Some((item_id, anchor)) = self.waiting_for.clone() {
            let is_it = self
                .transport
                .item
                .as_ref()
                .is_some_and(|i| i.id == item_id && i.content_id == content);
            if is_it {
                self.waiting_for = None;
                // Started late: from the anchor's position, now.
                let start = if anchor.instant > now {
                    anchor
                } else {
                    Anchor {
                        instant: now,
                        ..anchor
                    }
                };
                self.timeline.push(start);
            }
        }
    }

    /// Called often (every frame or block): ends the song at its exit point or its end.
    pub fn tick(&mut self, now: Micros) -> Effects {
        let mut effects = Effects::default();
        self.timeline.compact(now);
        let Some(item) = self.transport.item.clone() else {
            return effects;
        };
        let Some(position) = self.timeline.position_at(now) else {
            return effects;
        };
        let end = match (item.end, self.duration) {
            (Some(end), Some(duration)) => Some(end.min(duration)),
            (end, duration) => end.or(duration),
        };
        let playing = self.timeline.rate_at(now) > 0.0;
        if let Some(end) = end
            && playing
            && position >= end
        {
            self.timeline.push(Anchor::paused(end, now));
            if self.at_end == AtEnd::CueNext
                && let Some(next) = self.next_item(&item.id)
            {
                self.transport.semitones = next.semitones;
                self.transport.item = Some(next.clone());
                self.duration = None;
                self.timeline = Timeline::new(Anchor::paused(next.start.unwrap_or(0.0), now));
                effects.load = Some(next);
                effects.pitch = true;
            }
        }
        effects
    }

    pub fn next_item(&self, item_id: &str) -> Option<PlaylistItem> {
        let items = &self.playlist.as_ref()?.items;
        let index = items.iter().position(|i| i.id == item_id)?;
        items.get(index + 1).cloned()
    }

    /// Songs to have on disk, most urgent first: the one on, then the next ones.
    pub fn prefetch(&self, ahead: usize) -> Vec<PlaylistItem> {
        let Some(playlist) = &self.playlist else {
            return Vec::new();
        };
        let start = self
            .transport
            .item
            .as_ref()
            .and_then(|current| playlist.items.iter().position(|i| i.id == current.id))
            .unwrap_or(0);
        let mut order: Vec<PlaylistItem> = playlist
            .items
            .iter()
            .skip(start)
            .take(ahead + 1)
            .cloned()
            .collect();
        if let Some(current) = &self.transport.item
            && !order.iter().any(|i| i.id == current.id)
        {
            order.insert(0, current.clone());
        }
        order
    }

    pub fn state(&self, now: Micros) -> PlaybackState {
        match &self.transport.item {
            None => PlaybackState::Idle,
            Some(item) if !self.is_ready(&item.content_id) => PlaybackState::Loading,
            Some(_) if self.waiting_for.is_some() => PlaybackState::Waiting,
            Some(_) if self.timeline.rate_at(now) > 0.0 => PlaybackState::Playing,
            Some(_) => PlaybackState::Paused,
        }
    }

    pub fn status(&self, now: Micros) -> PlayerStatus {
        let mut status = PlayerStatus {
            cache: self.cache.clone(),
            item_id: self.transport.item.as_ref().map(|i| i.id.clone()),
            position: self.transport.item.as_ref().and(self.timeline.position_at(now)),
            state: self.state(now),
            semitones: self.transport.semitones,
            volume: self.transport.volume,
            ..PlayerStatus::default()
        };
        if let Some(offset) = self.clock.offset() {
            status.sync.insert("server_offset_ms".into(), offset as f64 / 1e3);
        }
        if let Some(rtt) = self.clock.rtt() {
            status.sync.insert("server_rtt_ms".into(), rtt as f64 / 1e3);
        }
        status
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use kp_proto::{CacheState, ContentCache};

    fn item(id: &str, content: &str, start: Option<f64>) -> PlaylistItem {
        PlaylistItem {
            id: id.into(),
            content_id: content.into(),
            manifest: None,
            start,
            end: None,
            semitones: 0.0,
            singer: None,
        }
    }

    fn playlist() -> Playlist {
        Playlist {
            id: "p".into(),
            name: "Noite".into(),
            version: 2,
            items: vec![item("a", "song-a", Some(2.0)), item("b", "song-b", None)],
            player_id: None,
        }
    }

    fn ready(core: &mut PlayerCore, content: &str, now: Micros) {
        core.cache_update(
            ContentCache {
                content_id: content.into(),
                manifest: "m".into(),
                state: CacheState::Ready,
                fraction: 1.0,
                error: None,
            },
            now,
        );
    }

    fn command(command: Command, item: Option<&str>, anchor: Option<Anchor>) -> ServerMessage {
        ServerMessage::Command {
            command: PlayerCommand {
                id: "c".into(),
                command,
                item_id: item.map(Into::into),
                anchor,
                value: None,
                issued_at: 0,
            },
        }
    }

    #[test]
    fn server_clock_prefers_short_round_trips() {
        let mut clock = ServerClock::default();
        clock.observe(10_000_000, None, 1_000);
        assert_eq!(clock.offset(), Some(9_999_000));
        // Local 1000 → 1600 round trip, server says 10 000 300 in the middle.
        clock.observe(10_000_300, Some(1_000), 1_600);
        assert_eq!(clock.offset(), Some(9_999_000));
        // A slower sample does not replace it.
        clock.observe(10_050_000, Some(2_000), 52_000);
        assert_eq!(clock.offset(), Some(9_999_000));
        assert_eq!(clock.to_local(10_000_000), 1_000);
    }

    #[test]
    fn timeline_changes_exactly_at_the_scheduled_instant() {
        let mut timeline = Timeline::new(Anchor::paused(0.0, 0));
        timeline.push(Anchor::playing(5.0, 1_000_000));
        assert_eq!(timeline.position_at(500_000), Some(0.0));
        assert_eq!(timeline.position_at(1_000_000), Some(5.0));
        assert!((timeline.position_at(1_500_000).unwrap() - 5.5).abs() < 1e-9);
        timeline.push(Anchor::paused(5.75, 1_750_000));
        assert_eq!(timeline.position_at(3_000_000), Some(5.75));
        assert_eq!(timeline.next_change(1_200_000), Some(1_750_000));
        // A newer order scheduled before drops the later one.
        timeline.push(Anchor::playing(9.0, 1_600_000));
        assert!((timeline.position_at(2_600_000).unwrap() - 10.0).abs() < 1e-9);
    }

    #[test]
    fn load_and_play_follow_the_server_anchor_in_local_time() {
        let mut core = PlayerCore::new();
        core.handle(
            ServerMessage::Time {
                now: 1_000_000_000,
                sent: Some(0),
            },
            0,
        );
        core.handle(ServerMessage::Playlist { playlist: playlist() }, 0);
        let load = core.handle(
            command(Command::Load, Some("a"), Some(Anchor::paused(2.0, 1_000_300_000))),
            10,
        );
        assert_eq!(load.load.unwrap().id, "a");
        assert_eq!(core.state(10), PlaybackState::Loading);
        ready(&mut core, "song-a", 20);
        assert_eq!(core.state(20), PlaybackState::Paused);
        core.handle(
            command(
                Command::Play,
                Some("a"),
                Some(Anchor::playing(2.0, 1_001_000_000)),
            ),
            30,
        );
        // Server µs 1 001 000 000 is local 1 000 000.
        assert_eq!(core.timeline.position_at(999_999), Some(2.0));
        assert!((core.timeline.position_at(2_000_000).unwrap() - 3.0).abs() < 1e-9);
        assert_eq!(core.state(1_500_000), PlaybackState::Playing);
    }

    #[test]
    fn an_order_waits_for_its_song_and_starts_late_from_its_position() {
        let mut core = PlayerCore::new();
        core.handle(ServerMessage::Playlist { playlist: playlist() }, 0);
        core.handle(
            command(Command::Load, Some("b"), Some(Anchor::playing(0.0, 1_000))),
            0,
        );
        assert_eq!(core.state(5_000), PlaybackState::Loading);
        ready(&mut core, "song-b", 3_000_000);
        assert_eq!(core.state(3_000_001), PlaybackState::Playing);
        assert_eq!(core.timeline.position_at(3_000_000), Some(0.0));
    }

    #[test]
    fn the_end_cues_the_next_singer() {
        let mut core = PlayerCore::new();
        core.handle(ServerMessage::Playlist { playlist: playlist() }, 0);
        ready(&mut core, "song-a", 0);
        core.handle(
            command(Command::Load, Some("a"), Some(Anchor::playing(2.0, 0))),
            0,
        );
        core.duration = Some(10.0);
        assert_eq!(core.tick(5_000_000), Effects::default());
        let effects = core.tick(9_000_000);
        assert_eq!(effects.load.unwrap().id, "b");
        assert_eq!(core.transport.item.as_ref().unwrap().id, "b");
        assert_eq!(core.state(9_000_001), PlaybackState::Loading);
        assert_eq!(
            core.prefetch(3).iter().map(|i| i.id.as_str()).collect::<Vec<_>>(),
            ["b"]
        );
    }

    #[test]
    fn status_reports_what_is_on() {
        let mut core = PlayerCore::new();
        core.handle(ServerMessage::Playlist { playlist: playlist() }, 0);
        assert_eq!(core.prefetch(1).len(), 2);
        ready(&mut core, "song-a", 0);
        core.handle(command(Command::Load, Some("a"), None), 0);
        let status = core.status(0);
        assert_eq!(status.item_id.as_deref(), Some("a"));
        assert_eq!(status.position, Some(2.0));
        assert_eq!(status.state, PlaybackState::Paused);
        core.handle(command(Command::Stop, None, None), 1);
        assert_eq!(core.status(1).state, PlaybackState::Idle);
    }
}
