//! `kp-syncbench [--json] [--seconds N]`: runs the default scenarios and fails if a target is missed.

use kp_syncbench::{default_scenarios, run};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let json = args.iter().any(|a| a == "--json");
    let seconds = args
        .iter()
        .position(|a| a == "--seconds")
        .and_then(|i| args.get(i + 1))
        .and_then(|s| s.parse::<f64>().ok());
    let mut failed = false;
    let mut reports = Vec::new();
    for mut scenario in default_scenarios() {
        if let Some(seconds) = seconds {
            scenario.seconds = seconds;
        }
        let report = run(&scenario);
        failed |= !report.passed;
        if !json {
            println!(
                "{} ({} s): {}",
                report.scenario,
                scenario.seconds,
                if report.passed { "ok" } else { "FAILED" }
            );
            let stats = &report.audio_audio;
            println!(
                "  audio↔audio max {:.3} ms, p99 {:.3} ms, mean {:.3} ms; learnt {:+.1} ppm, {} jumps",
                stats.max_ms, stats.p99_ms, stats.mean_ms, report.learnt_ppm, report.jumps
            );
            for failure in &report.failures {
                println!("  ✗ {failure}");
            }
        }
        reports.push(report);
    }
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&reports).expect("serialisable")
        );
    }
    std::process::exit(i32::from(failed));
}
