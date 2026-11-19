//! Themes (`theme.json`, contracts v1) and the advance widths of their fonts.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::Deserialize;

fn d_visible() -> usize {
    2
}
fn d_position() -> String {
    "bottom".into()
}
fn d_font_size() -> f64 {
    0.06
}
fn d_spacing() -> f64 {
    1.3
}
fn d_mode() -> String {
    "pages".into()
}
fn d_margin() -> f64 {
    0.05
}
fn d_min_row_chars() -> usize {
    22
}
fn d_max_rows() -> usize {
    2
}
fn d_outline() -> f64 {
    0.06
}
fn d_shadow() -> f64 {
    0.04
}
fn d_fill() -> String {
    "wipe".into()
}
fn d_gap() -> f64 {
    5.0
}
fn d_lead_in() -> f64 {
    3.0
}
fn d_hold() -> f64 {
    0.4
}
fn d_transition() -> f64 {
    0.25
}
fn d_anticipation() -> f64 {
    0.05
}
fn d_dots() -> usize {
    3
}
fn d_step() -> f64 {
    1.0
}
fn d_bar() -> f64 {
    8.0
}
fn d_backing_scale() -> f64 {
    0.72
}
fn d_true() -> bool {
    true
}
fn d_opacity() -> f64 {
    0.85
}
fn d_weight() -> u32 {
    700
}

#[derive(Clone, Debug, Deserialize)]
pub struct ThemeFont {
    pub family: String,
    #[serde(default = "d_weight")]
    pub weight: u32,
    #[serde(default)]
    pub file: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ThemeColors {
    pub sung: String,
    pub unsung: String,
    pub outline: String,
    #[serde(default)]
    pub shadow: Option<String>,
    #[serde(default, rename = "box")]
    pub box_color: Option<String>,
    #[serde(default)]
    pub singers: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ThemeLayout {
    #[serde(default = "d_visible")]
    pub visible_lines: usize,
    #[serde(default = "d_position")]
    pub position: String,
    #[serde(default = "d_font_size")]
    pub font_size: f64,
    #[serde(default = "d_spacing")]
    pub line_spacing: f64,
    #[serde(default = "d_mode")]
    pub mode: String,
    #[serde(default = "d_margin")]
    pub margin: f64,
    #[serde(default = "d_min_row_chars")]
    pub min_row_chars: usize,
    #[serde(default = "d_max_rows")]
    pub max_rows: usize,
    #[serde(default = "d_outline")]
    pub outline_width: f64,
    #[serde(default = "d_shadow")]
    pub shadow_offset: f64,
    #[serde(default)]
    pub shadow_blur: f64,
}

impl Default for ThemeLayout {
    fn default() -> Self {
        serde_json::from_str("{}").expect("every field has a default")
    }
}

#[derive(Clone, Debug, Deserialize)]
pub struct ThemeAnimation {
    #[serde(default = "d_fill")]
    pub fill: String,
    #[serde(default = "d_gap")]
    pub countdown_min_gap: f64,
    #[serde(default = "d_lead_in")]
    pub lead_in: f64,
    #[serde(default = "d_hold")]
    pub hold: f64,
    #[serde(default = "d_transition")]
    pub transition: f64,
    #[serde(default = "d_anticipation")]
    pub anticipation: f64,
    #[serde(default = "d_dots")]
    pub countdown_dots: usize,
    #[serde(default = "d_step")]
    pub countdown_step: f64,
    #[serde(default = "d_bar")]
    pub break_bar_min: f64,
}

impl Default for ThemeAnimation {
    fn default() -> Self {
        serde_json::from_str("{}").expect("every field has a default")
    }
}

#[derive(Clone, Debug, Deserialize)]
pub struct ThemeBacking {
    #[serde(default = "d_backing_scale")]
    pub scale: f64,
    #[serde(default = "d_true")]
    pub brackets: bool,
    #[serde(default = "d_opacity")]
    pub opacity: f64,
}

impl Default for ThemeBacking {
    fn default() -> Self {
        serde_json::from_str("{}").expect("every field has a default")
    }
}

#[derive(Clone, Debug, Deserialize)]
pub struct Theme {
    pub id: String,
    pub name: String,
    pub font: ThemeFont,
    pub colors: ThemeColors,
    #[serde(default)]
    pub layout: ThemeLayout,
    #[serde(default)]
    pub animation: ThemeAnimation,
    #[serde(default)]
    pub backing: ThemeBacking,
}

impl Theme {
    pub fn load(path: &Path) -> std::io::Result<Self> {
        let text = std::fs::read_to_string(path)?;
        serde_json::from_str(&text).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }
}

/// Advance widths of a font (`*.metrics.json`, written by `scripts/build_fonts.py`).
#[derive(Clone, Debug, Deserialize)]
pub struct FontMetrics {
    pub upem: f64,
    pub ascender: f64,
    pub descender: f64,
    pub win_ascent: f64,
    pub win_descent: f64,
    pub default_advance: f64,
    pub average_lowercase: f64,
    pub advances: HashMap<char, f64>,
}

impl FontMetrics {
    pub fn load(path: &Path) -> std::io::Result<Self> {
        let text = std::fs::read_to_string(path)?;
        serde_json::from_str(&text).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Width of `text` at `px` pixels per em, summed in text order and scaled once at the end,
    /// exactly as Python and the web do (same floating-point result).
    pub fn width(&self, text: &str, px: f64) -> f64 {
        let mut total = 0.0;
        for c in text.chars() {
            total += self.advances.get(&c).copied().unwrap_or(self.default_advance);
        }
        total * px / self.upem
    }
}

/// The bundled themes and fonts (`packages/engine/.../subtitles/themes`), or a folder of the
/// same shape next to the player when installed.
#[derive(Clone, Debug)]
pub struct ThemeLibrary {
    pub dir: PathBuf,
}

impl ThemeLibrary {
    pub fn new(dir: impl Into<PathBuf>) -> Self {
        Self { dir: dir.into() }
    }

    pub fn theme(&self, id: &str) -> std::io::Result<Theme> {
        Theme::load(&self.dir.join(format!("{id}.json")))
    }

    pub fn font_path(&self, theme: &Theme) -> Option<PathBuf> {
        theme
            .font
            .file
            .as_ref()
            .map(|file| self.dir.join("fonts").join(file))
    }

    pub fn metrics(&self, theme: &Theme) -> std::io::Result<FontMetrics> {
        let font = self
            .font_path(theme)
            .unwrap_or_else(|| self.dir.join("fonts/Nunito-Black.ttf"));
        FontMetrics::load(&font.with_extension("metrics.json"))
    }
}
