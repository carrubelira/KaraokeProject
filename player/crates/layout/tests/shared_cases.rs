//! The layout matches the Python reference on every shared case, to 1e-6.

use std::path::{Path, PathBuf};

use kp_layout::theme::ThemeLibrary;
use kp_layout::{FontMetrics, build_layout, wrap};
use kp_proto::{Line, Singer};
use serde_json::Value;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn close(actual: &Value, expected: &Value, path: &str) {
    match (actual, expected) {
        (Value::Number(a), Value::Number(e)) => {
            let (a, e) = (a.as_f64().unwrap(), e.as_f64().unwrap());
            assert!((a - e).abs() <= 1e-6, "{path}: {a} != {e}");
        }
        (Value::Array(a), Value::Array(e)) => {
            assert_eq!(a.len(), e.len(), "{path}: length");
            for (i, (a, e)) in a.iter().zip(e).enumerate() {
                close(a, e, &format!("{path}[{i}]"));
            }
        }
        (Value::Object(a), Value::Object(e)) => {
            let mut ak: Vec<_> = a.keys().collect();
            let mut ek: Vec<_> = e.keys().collect();
            ak.sort();
            ek.sort();
            assert_eq!(ak, ek, "{path}: keys");
            for (key, value) in e {
                close(&a[key], value, &format!("{path}.{key}"));
            }
        }
        (a, e) => assert_eq!(a, e, "{path}"),
    }
}

#[test]
fn every_shared_case_matches() {
    let root = root();
    let library = ThemeLibrary::new(root.join("packages/engine/src/karaoke_engine/subtitles/themes"));
    let mut files: Vec<_> = std::fs::read_dir(root.join("fixtures/lyrics-layout"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().is_some_and(|e| e == "json"))
        .collect();
    files.sort();
    assert!(files.len() >= 10);
    for file in files {
        let case: Value = serde_json::from_str(&std::fs::read_to_string(&file).unwrap()).unwrap();
        let doc: Value = match &case["doc"] {
            Value::String(path) => {
                serde_json::from_str(&std::fs::read_to_string(root.join(path)).unwrap()).unwrap()
            }
            inline => inline.clone(),
        };
        let lines: Vec<Line> = serde_json::from_value(doc["lines"].clone()).unwrap();
        let singers: Vec<Singer> =
            serde_json::from_value(doc.get("singers").cloned().unwrap_or(Value::Array(vec![]))).unwrap();
        let theme = library.theme(case["theme"].as_str().unwrap()).unwrap();
        let metrics = library.metrics(&theme).unwrap();
        let layout = build_layout(
            &lines,
            &singers,
            &theme,
            case["width"].as_f64().unwrap(),
            case["height"].as_f64().unwrap(),
            &metrics,
        );
        close(
            &serde_json::to_value(&layout).unwrap(),
            &case["layout"],
            file.file_name().unwrap().to_str().unwrap(),
        );
    }
}

#[test]
fn wrap_breaks_and_shrinks_like_the_reference() {
    let mono: FontMetrics = serde_json::from_str(
        r#"{"upem":1000,"ascender":900,"descender":-300,"win_ascent":1000,"win_descent":250,
            "default_advance":500,"average_lowercase":500,"advances":{}}"#,
    )
    .unwrap();
    let words = |w: &[&str]| w.iter().map(|s| s.to_string()).collect::<Vec<_>>();
    assert_eq!(
        wrap(&words(&["Ola", "que", "tal"]), 75.0, 900.0, 2, &mono),
        (vec![vec![0, 1, 2]], 1.0)
    );
    let (rows, scale) = wrap(
        &words(&[
            "a".repeat(20).as_str(),
            "b".repeat(20).as_str(),
            "c".repeat(20).as_str(),
        ]),
        75.0,
        900.0,
        2,
        &mono,
    );
    assert_eq!(rows.len(), 3);
    assert!(scale <= 1.0);
}
