//! What kp-audio decides, apart from how it plays (decision 011).
//!
//! - [`ServerClock`] learns the offset between the server's clock and this machine's monotonic
//!   clock from `time` messages (the sample with the shortest round trip wins), so an anchor the
//!   server sets "120 ms from now" lands on the same instant here.
//! - [`Timeline`] holds the anchors in local time; the audio callback asks it the song position
//!   heard at any instant, and a change scheduled for later takes effect exactly then.
//! - [`StageCore`] follows the server's **session**: the newest version wins, and from it the
//!   engine learns which song to have decoded, where the song is and when, the key and the
//!   volume. It says when the song on is ready for the epoch the server cued, so the server can
//!   tell the operator.

use kp_clock::{Anchor, Micros};
use kp_proto::{AudioConfig, AudioState, AudioStatus, Program, ServerMessage, Session, SessionState};

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

/// What changed for the engine after a message.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Effects {
    /// A different song must be decoded (or taken from the one decoded ahead).
    pub load: Option<Program>,
    pub unload: bool,
    pub config: bool,
    pub pitch: bool,
    pub volume: bool,
    /// What comes next changed: decode the first of it ahead.
    pub upcoming: bool,
}

#[derive(Default)]
pub struct StageCore {
    pub clock: ServerClock,
    pub config: AudioConfig,
    pub session: Session,
    pub timeline: Timeline,
    /// The song decoded and in the mixers (it lags the session's while it decodes).
    pub loaded: Option<Program>,
}

impl StageCore {
    pub fn new() -> Self {
        Self::default()
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
            ServerMessage::Session { session } => self.follow(session, &mut effects),
        }
        effects
    }

    fn local(&self, anchor: Anchor) -> Anchor {
        Anchor {
            instant: self.clock.to_local(anchor.instant),
            ..anchor
        }
    }

    fn follow(&mut self, session: Session, effects: &mut Effects) {
        if session.version < self.session.version {
            return; // late: a newer one is already in effect
        }
        let before = std::mem::replace(&mut self.session, session);
        match self.session.current.clone() {
            None => {
                if before.current.is_some() || self.loaded.is_some() {
                    effects.unload = true;
                }
                self.loaded = None;
                self.timeline.clear();
            }
            Some(program) => {
                let same = before.current.as_ref().is_some_and(|old| old.same_as(&program));
                if !same {
                    effects.load = Some(program);
                }
                match self.session.anchor {
                    Some(anchor) => {
                        let anchor = self.local(anchor);
                        if !same || self.timeline.is_empty() {
                            self.timeline = Timeline::new(Anchor::paused(anchor.position, anchor.instant));
                        }
                        self.timeline.push(anchor);
                    }
                    None => self.timeline.clear(),
                }
            }
        }
        effects.pitch |= before.semitones != self.session.semitones;
        effects.volume |= before.volume != self.session.volume;
        effects.upcoming |= before.upcoming != self.session.upcoming;
    }

    /// The song finished decoding: true if it is still the one on (it goes to the mixers).
    pub fn loaded(&mut self, program: &Program) -> bool {
        let wanted = self
            .session
            .current
            .as_ref()
            .is_some_and(|current| current.same_as(program));
        if wanted {
            self.loaded = Some(program.clone());
        }
        wanted
    }

    /// Whether the song on is decoded and in the mixers.
    pub fn ready(&self) -> bool {
        match (&self.session.current, &self.loaded) {
            (Some(current), Some(loaded)) => current.same_as(loaded),
            _ => false,
        }
    }

    /// Called often: holds the song at its exit point even before the server says it ended,
    /// so it never plays on past it.
    pub fn tick(&mut self, now: Micros) {
        self.timeline.compact(now);
        let Some(current) = &self.session.current else {
            return;
        };
        let end = current.end();
        if self.timeline.rate_at(now) > 0.0
            && let Some(position) = self.timeline.position_at(now)
            && position >= end
        {
            self.timeline.push(Anchor::paused(end, now));
        }
    }

    pub fn state(&self, now: Micros) -> AudioState {
        if self.session.current.is_none() {
            AudioState::Idle
        } else if !self.ready() {
            AudioState::Loading
        } else if self.timeline.rate_at(now) > 0.0 {
            AudioState::Playing
        } else if self.session.state == SessionState::Paused {
            AudioState::Paused
        } else {
            AudioState::Ready
        }
    }

    pub fn status(&self, now: Micros) -> AudioStatus {
        let mut status = AudioStatus {
            state: self.state(now),
            epoch: Some(self.session.epoch),
            ready: self.ready(),
            item_id: self.session.current.as_ref().map(|c| c.item.id.clone()),
            position: self.session.current.as_ref().and(self.timeline.position_at(now)),
            ..AudioStatus::default()
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
    use kp_proto::QueueItem;

    fn program(id: &str, end: Option<f64>) -> Program {
        Program {
            item: QueueItem {
                id: id.into(),
                content_id: "song".into(),
                manifest: None,
                start: Some(2.0),
                end,
                semitones: 0.0,
                singer: None,
            },
            manifest: format!("{id:0>64}"),
            duration: 10.0,
        }
    }

    fn session(
        version: u64,
        epoch: u64,
        state: SessionState,
        current: Option<Program>,
        anchor: Option<Anchor>,
    ) -> Session {
        Session {
            version,
            epoch,
            state,
            current,
            anchor,
            upcoming: Vec::new(),
            semitones: 0.0,
            volume: 1.0,
        }
    }

    fn message(session: Session) -> ServerMessage {
        ServerMessage::Session { session }
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
    fn a_cue_loads_the_song_and_a_start_follows_the_anchor_in_local_time() {
        let mut core = StageCore::new();
        core.handle(
            ServerMessage::Time {
                now: 1_000_000_000,
                sent: Some(0),
            },
            0,
        );
        let cued = session(
            1,
            1,
            SessionState::Cueing,
            Some(program("a", None)),
            Some(Anchor::paused(2.0, 1_000_000_000)),
        );
        let cue = core.handle(message(cued), 10);
        assert_eq!(cue.load.as_ref().unwrap().item.id, "a");
        assert_eq!(core.state(10), AudioState::Loading);
        assert!(!core.status(10).ready);
        assert!(core.loaded(&program("a", None)));
        assert_eq!(core.state(20), AudioState::Ready);
        let status = core.status(20);
        assert!(status.ready);
        assert_eq!((status.epoch, status.position), (Some(1), Some(2.0)));
        // The operator's start at server µs 1 001 000 000 is local 1 000 000.
        let started = session(
            2,
            1,
            SessionState::Playing,
            Some(program("a", None)),
            Some(Anchor::playing(2.0, 1_001_000_000)),
        );
        let start = core.handle(message(started), 30);
        assert_eq!(start.load, None, "the same song stays decoded");
        assert_eq!(core.timeline.position_at(999_999), Some(2.0));
        assert!((core.timeline.position_at(2_000_000).unwrap() - 3.0).abs() < 1e-9);
        assert_eq!(core.state(1_500_000), AudioState::Playing);
    }

    #[test]
    fn a_late_session_is_ignored_and_a_song_decoded_too_late_is_dropped() {
        let mut core = StageCore::new();
        let newer = session(
            5,
            2,
            SessionState::Cueing,
            Some(program("b", None)),
            Some(Anchor::paused(0.0, 0)),
        );
        core.handle(message(newer), 0);
        let late = core.handle(
            message(session(
                4,
                1,
                SessionState::Cueing,
                Some(program("a", None)),
                None,
            )),
            0,
        );
        assert_eq!(late, Effects::default());
        assert!(
            !core.loaded(&program("a", None)),
            "another song was asked for meanwhile"
        );
        assert!(!core.ready());
    }

    #[test]
    fn the_exit_point_holds_the_song_before_the_server_says_so() {
        let mut core = StageCore::new();
        let playing = session(
            1,
            1,
            SessionState::Playing,
            Some(program("a", Some(4.0))),
            Some(Anchor::playing(2.0, 0)),
        );
        core.handle(message(playing), 0);
        core.tick(1_000_000);
        assert_eq!(core.timeline.rate_at(1_000_000), 1.0);
        core.tick(2_500_000);
        assert_eq!(core.timeline.position_at(9_000_000), Some(4.0));
        assert_eq!(core.timeline.rate_at(9_000_000), 0.0);
    }

    #[test]
    fn stopping_unloads_and_the_key_and_volume_are_followed() {
        let mut core = StageCore::new();
        let cued = session(
            1,
            1,
            SessionState::Cued,
            Some(program("a", None)),
            Some(Anchor::paused(2.0, 0)),
        );
        core.handle(message(cued.clone()), 0);
        core.loaded(&program("a", None));
        let louder = Session {
            version: 2,
            volume: 1.5,
            semitones: -2.0,
            ..cued
        };
        let effects = core.handle(message(louder), 0);
        assert!(effects.volume && effects.pitch && effects.load.is_none());
        let stop = core.handle(message(session(3, 2, SessionState::Idle, None, None)), 0);
        assert!(stop.unload);
        assert_eq!(core.status(0).state, AudioState::Idle);
    }
}
