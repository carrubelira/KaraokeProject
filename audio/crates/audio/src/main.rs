//! `kp-audio`: the backend's audio engine (decision 011).
//!
//! ```text
//! kp-audio run --server http://127.0.0.1:8765 --store DIR [--virtual-outputs N] [--diagnose]
//!               [--watch-stdin]
//! kp-audio devices
//! ```
//!
//! The server starts it (and starts it again if it stops) with the secret it connects with in
//! `KARAOKE_AUDIO_TOKEN`; `karaoke-server serve --audio external` leaves that to a person.

mod audio;
mod clock;
mod control;
mod decode;
mod link;
mod pitch;
mod program;

use std::path::PathBuf;
use std::process::ExitCode;

use crate::audio::Outputs;
use crate::control::{Engine, Options};
use crate::program::Store;

struct Args {
    rest: Vec<String>,
}

impl Args {
    fn flag(&mut self, name: &str) -> bool {
        let found = self.rest.iter().position(|a| a == name);
        if let Some(i) = found {
            self.rest.remove(i);
        }
        found.is_some()
    }

    fn value(&mut self, name: &str) -> Option<String> {
        let i = self.rest.iter().position(|a| a == name)?;
        self.rest.remove(i);
        (i < self.rest.len()).then(|| self.rest.remove(i))
    }
}

fn main() -> ExitCode {
    let level = std::env::var("KP_LOG").unwrap_or_else(|_| "info".into());
    init_logging(&level);
    let mut args = Args {
        rest: std::env::args().skip(1).collect(),
    };
    let command = if args.rest.is_empty() {
        "run".to_string()
    } else {
        args.rest.remove(0)
    };
    let result = match command.as_str() {
        "devices" => devices(&mut args),
        "run" => run(&mut args),
        "version" | "--version" => {
            println!("kp-audio {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        other => Err(format!("unknown command {other}: try run or devices")),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}

fn init_logging(level: &str) {
    struct Stderr(log::LevelFilter);
    impl log::Log for Stderr {
        fn enabled(&self, metadata: &log::Metadata<'_>) -> bool {
            metadata.level() <= self.0
        }
        fn log(&self, record: &log::Record<'_>) {
            if self.enabled(record.metadata()) && record.target().starts_with("kp") {
                eprintln!("{:>5} {}: {}", record.level(), record.target(), record.args());
            }
        }
        fn flush(&self) {}
    }
    let filter = level.parse().unwrap_or(log::LevelFilter::Info);
    let logger: &'static Stderr = Box::leak(Box::new(Stderr(filter)));
    let _ = log::set_logger(logger);
    log::set_max_level(filter);
}

fn backend(args: &mut Args) -> Box<dyn audio::Backend> {
    if let Some(count) = args.value("--virtual-outputs") {
        return Box::new(audio::simulated::Simulated::new(count.parse().unwrap_or(1)));
    }
    #[cfg(feature = "native")]
    {
        Box::new(audio::native::Cpal::new())
    }
    #[cfg(not(feature = "native"))]
    {
        Box::new(audio::simulated::Simulated::new(1))
    }
}

fn devices(args: &mut Args) -> Result<(), String> {
    let backend = backend(args);
    for device in backend.devices() {
        let mark = if device.default { " (default)" } else { "" };
        println!(
            "{}  {} ch  {} Hz  {}{mark}",
            device.id, device.channels, device.sample_rate, device.name
        );
    }
    for problem in backend.problems() {
        eprintln!("note: {problem}");
    }
    Ok(())
}

fn run(args: &mut Args) -> Result<(), String> {
    let diagnose = args.flag("--diagnose");
    if args.flag("--watch-stdin") {
        // The server keeps our stdin open; when it ends (the server stopped, even killed), so do
        // we: the sound card is never left held by an orphan.
        std::thread::spawn(|| {
            let mut sink = Vec::new();
            let _ = std::io::Read::read_to_end(&mut std::io::stdin(), &mut sink);
            log::info!("the server is gone: stopping");
            std::process::exit(0);
        });
    }
    let server = args
        .value("--server")
        .unwrap_or_else(|| "http://127.0.0.1:8765".into());
    let store = args
        .value("--store")
        .map(PathBuf::from)
        .ok_or("--store: the server's blob folder is needed")?;
    let token = std::env::var("KARAOKE_AUDIO_TOKEN")
        .map_err(|_| "KARAOKE_AUDIO_TOKEN: the secret the server gave is needed")?;
    let backend = backend(args);
    let url = link::socket_url(&server);
    let mut engine = Engine::start(
        url,
        token,
        Store::new(store),
        Outputs::new(backend),
        Options { diagnose },
    );
    engine.run(None);
    Ok(())
}
