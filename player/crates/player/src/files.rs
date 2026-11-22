//! The player's data folder: its identity (`player.json`), its cache, its diagnostics.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Identity {
    pub server: String,
    pub node_id: String,
    pub credential: String,
    pub fingerprint: String,
    pub name: String,
}

pub fn default_dir() -> PathBuf {
    if cfg!(windows)
        && let Ok(base) = std::env::var("LOCALAPPDATA")
    {
        return PathBuf::from(base).join("karaoke-player");
    }
    let home = std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));
    if cfg!(target_os = "macos") {
        return home.join("Library/Application Support/karaoke-player");
    }
    std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| home.join(".local/share"))
        .join("karaoke-player")
}

impl Identity {
    pub fn load(dir: &Path) -> std::io::Result<Self> {
        let text = std::fs::read_to_string(dir.join("player.json"))?;
        serde_json::from_str(&text).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    pub fn save(&self, dir: &Path) -> std::io::Result<PathBuf> {
        std::fs::create_dir_all(dir)?;
        let path = dir.join("player.json");
        std::fs::write(&path, serde_json::to_vec_pretty(self).expect("serialisable"))?;
        Ok(path)
    }
}

/// Where the bundled themes and fonts are: next to the binary when installed, else the repo's.
pub fn themes_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("KARAOKE_THEMES") {
        return PathBuf::from(dir);
    }
    if let Some(dir) = std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|p| p.join("themes")))
        && dir.join("clasico.json").is_file()
    {
        return dir;
    }
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../packages/engine/src/karaoke_engine/subtitles/themes")
}
