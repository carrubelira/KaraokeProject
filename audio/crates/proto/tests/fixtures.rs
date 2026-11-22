//! Every v2 example kp-audio reads or writes must parse here and come back identical.

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
    round_trip::<Queue>("queue");
    let session: Session = round_trip("session");
    assert_eq!(session.state, SessionState::Playing);
    let current = session.current.expect("a song on");
    assert_eq!(current.end(), 214.5);
    let config: AudioConfig = round_trip("audio-config");
    assert_eq!(config.routing.policy("wasapi:hdmi-1"), OutputPolicy::Pause);
    assert_eq!(config.routing.policy("wasapi:usb-2"), OutputPolicy::Continue);
    let status: AudioStatus = round_trip("audio-status");
    assert!(status.ready);
}

#[test]
fn unknown_fields_are_refused() {
    let mut value = fixture("queue");
    value["colour"] = "red".into();
    assert!(serde_json::from_value::<Queue>(value).is_err());
}

#[test]
fn server_messages_are_tagged() {
    let message: ServerMessage = serde_json::from_str(r#"{"type":"time","now":5}"#).unwrap();
    assert_eq!(message, ServerMessage::Time { now: 5, sent: None });
    let session = format!(r#"{{"type":"session","session":{}}}"#, fixture("session"));
    assert!(matches!(
        serde_json::from_str::<ServerMessage>(&session).unwrap(),
        ServerMessage::Session { .. }
    ));
}
