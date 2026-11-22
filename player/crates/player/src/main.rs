//! `kp-player`: the native karaoke player (plan v4 §6).
//!
//! ```text
//! kp-player enroll https://SERVER:8765 TOKEN [--fingerprint HEX] [--name NAME]
//! kp-player run [--headless] [--virtual-outputs N] [--same-host] [--diagnose]
//! kp-player devices
//! ```

mod audio;
mod clock;
mod control;
mod files;
mod link;
mod pitch;
mod prepare;
mod program;
#[cfg(feature = "native")]
mod screens;
mod video;

use std::path::PathBuf;
use std::process::ExitCode;

use kp_cache::Needs;
use kp_proto::{Capabilities, Display, Enrollment, VideoCodec};

use crate::audio::Outputs;
use crate::control::{Options, Player};
use crate::files::Identity;

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

fn os() -> &'static str {
    if cfg!(windows) {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else {
        "linux"
    }
}

fn main() -> ExitCode {
    let level = std::env::var("KP_LOG").unwrap_or_else(|_| "info".into());
    init_logging(&level);
    let mut args = Args {
        rest: std::env::args().skip(1).collect(),
    };
    let data_dir = args
        .value("--data")
        .map(PathBuf::from)
        .unwrap_or_else(files::default_dir);
    let command = if args.rest.is_empty() {
        "run".to_string()
    } else {
        args.rest.remove(0)
    };
    let result = match command.as_str() {
        "enroll" => enroll(&mut args, &data_dir),
        "devices" => devices(&mut args),
        "run" => run(&mut args, &data_dir),
        "version" | "--version" => {
            println!("kp-player {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        other => Err(format!("unknown command {other}: try enroll, run or devices")),
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

fn enroll(args: &mut Args, data_dir: &std::path::Path) -> Result<(), String> {
    let fingerprint = args.value("--fingerprint");
    let name = args.value("--name").unwrap_or_else(|| {
        std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "player".into())
    });
    let [server, token] = args.rest.as_slice() else {
        return Err("usage: kp-player enroll SERVER TOKEN [--fingerprint HEX] [--name NAME]".into());
    };
    let request = Enrollment {
        token: token.clone(),
        kind: "player".into(),
        name: name.clone(),
        capabilities: Capabilities {
            os: os().into(),
            cpus: std::thread::available_parallelism().map_or(1, |n| n.get() as u32),
            ram_mb: 0,
            gpus: Vec::new(),
            internet: false,
            tasks: Vec::new(),
            models: Default::default(),
            decoders: vec!["h264".into(), "hevc".into(), "av1".into()],
            same_host_as_server: false,
        },
    };
    let (enrolled, seen) =
        kp_net::enrol(server, &request, fingerprint.as_deref()).map_err(|e| e.to_string())?;
    if fingerprint.is_none()
        && let Some(seen) = &seen
    {
        eprintln!("trusting the server's certificate {seen} on first use");
    }
    let identity = Identity {
        server: server.trim_end_matches('/').into(),
        node_id: enrolled.node_id.clone(),
        credential: enrolled.credential,
        fingerprint: seen.unwrap_or(enrolled.server_fingerprint),
        name,
    };
    let path = identity.save(data_dir).map_err(|e| e.to_string())?;
    println!("enrolled as {}; settings in {}", enrolled.node_id, path.display());
    Ok(())
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

fn run(args: &mut Args, data_dir: &std::path::Path) -> Result<(), String> {
    let headless = args.flag("--headless") || cfg!(not(feature = "native"));
    let diagnose = args.flag("--diagnose");
    let same_host = args.flag("--same-host");
    let backend = backend(args);
    let identity = Identity::load(data_dir).map_err(|e| format!("{e}: enrol first (kp-player enroll)"))?;
    let fingerprint = (!identity.fingerprint.is_empty()).then_some(identity.fingerprint.as_str());
    let server = kp_net::Server::new(&identity.server, Some(&identity.credential), fingerprint);
    let needs = Needs {
        screen_height: 1080,
        decoders: vec![VideoCodec::H264, VideoCodec::Hevc, VideoCodec::Av1],
        video: !headless,
    };
    let options = Options {
        data_dir: data_dir.to_path_buf(),
        same_host,
        diagnose,
        needs,
    };
    let mut player = Player::start(server, Outputs::new(backend), options).map_err(|e| e.to_string())?;
    if headless {
        if let Ok(mut displays) = player.displays.lock() {
            displays.push(Display {
                id: "headless".into(),
                name: "No screen".into(),
                width: 1920,
                height: 1080,
                refresh_hz: 60.0,
                primary: true,
                connected: true,
            });
        }
        player.run(None);
        return Ok(());
    }
    #[cfg(feature = "native")]
    {
        let view = player.view.clone();
        let shared = player.shared();
        let displays = player.displays.clone();
        std::thread::Builder::new()
            .name("control".into())
            .spawn(move || player.run(None))
            .map_err(|e| e.to_string())?;
        screens::run(view, shared, displays, files::themes_dir()).map_err(|e| e.to_string())
    }
    #[cfg(not(feature = "native"))]
    {
        Ok(())
    }
}
