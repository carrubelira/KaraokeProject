//! Every v2 example the Python contracts validate must parse here and come back identical.

use std::path::PathBuf;

use kp_proto::*;
use serde::{Serialize, de::DeserializeOwned};
use serde_json::Value;

fn fixture(name: &str) -> Value {
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(format!("../../../fixtures/contracts-v2/{name}.json"));
    serde_json::from_str(&std::fs::read_to_string(path).expect("fixture")).expect("json")
}

fn round_trip<T: DeserializeOwned + Serialize>(name: &str) -> T {
    let value = fixture(name);
    let parsed: T = serde_json::from_value(value.clone()).unwrap_or_else(|e| panic!("{name}: {e}"));
    assert_eq!(
        serde_json::to_value(&parsed).unwrap(),
        value,
        "{name} changed on the way back"
    );
    parsed
}

#[test]
fn every_fixture_round_trips() {
    let manifest: Manifest = round_trip("manifest");
    assert!(manifest.track(TrackKind::Instrumental).is_some());
    let lyrics: Lyrics = round_trip("lyrics");
    assert!(!lyrics.lines.is_empty());
    round_trip::<Playlist>("playlist");
    let command: PlayerCommand = round_trip("player-command");
    assert_eq!(command.command, Command::Play);
    let config: PlayerConfig = round_trip("player-config");
    assert_eq!(config.routing.policy("wasapi:hdmi-1"), OutputPolicy::Pause);
    assert_eq!(config.routing.policy("wasapi:usb-2"), OutputPolicy::Continue);
    round_trip::<PlayerStatus>("player-status");
    round_trip::<Enrollment>("enrollment");
}

#[test]
fn unknown_fields_are_refused() {
    let mut value = fixture("playlist");
    value["colour"] = "red".into();
    assert!(serde_json::from_value::<Playlist>(value).is_err());
}

#[test]
fn server_messages_are_tagged() {
    let message: ServerMessage = serde_json::from_str(r#"{"type":"time","now":5}"#).unwrap();
    assert_eq!(message, ServerMessage::Time { now: 5, sent: None });
}
