//! The screens: a borderless full-screen window on every monitor the routing names (or on all
//! of them), drawn with wgpu at each monitor's own refresh (plan v4 §6).
//!
//! Each frame asks the master clock for the song position heard at the instant the frame will
//! be shown (the next vsync plus the display's calibrated latency), so the picture and the
//! lyrics follow the sound on every screen, whatever its refresh rate. One video decoder feeds
//! every screen; the lyrics are laid out per screen size with the shared layout (kp-layout).

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use glyphon::{
    Attrs, Buffer, Cache, Color, Family, FontSystem, Metrics, Resolution, Shaping, SwashCache, TextArea,
    TextAtlas, TextBounds, TextRenderer, Viewport, Weight,
};
use kp_layout::scene::{Fill, PartBox, fill_segments, fill_x, scene_at};
use kp_layout::theme::ThemeLibrary;
use kp_layout::{Layout, Theme, build_layout};
use kp_proto::{Display, PlaybackState, ScreenLayout};
use wgpu::util::DeviceExt;
use winit::application::ApplicationHandler;
use winit::event::WindowEvent;
use winit::event_loop::{ActiveEventLoop, ControlFlow, EventLoop};
use winit::monitor::MonitorHandle;
use winit::window::{Fullscreen, Window, WindowId};

use crate::audio::Shared;
use crate::control::View;
use crate::program::Program;
use crate::video::VideoFeed;

const RECTS: &str = r#"
struct Screen { size: vec2<f32>, pad: vec2<f32> };
@group(0) @binding(0) var<uniform> screen: Screen;
struct RectIn { @location(0) rect: vec4<f32>, @location(1) color: vec4<f32>, @location(2) radius: f32 };
struct VOut {
  @builtin(position) pos: vec4<f32>,
  @location(0) color: vec4<f32>,
  @location(1) local: vec2<f32>,
  @location(2) half: vec2<f32>,
  @location(3) radius: f32,
};
@vertex fn vs(@builtin(vertex_index) vi: u32, r: RectIn) -> VOut {
  var corners = array<vec2<f32>, 6>(vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 0.0), vec2(1.0, 1.0), vec2(0.0, 1.0));
  let c = corners[vi];
  let p = r.rect.xy + c * r.rect.zw;
  var o: VOut;
  o.pos = vec4(p.x / screen.size.x * 2.0 - 1.0, 1.0 - p.y / screen.size.y * 2.0, 0.0, 1.0);
  o.color = r.color;
  o.half = r.rect.zw * 0.5;
  o.local = (c - vec2(0.5)) * r.rect.zw;
  o.radius = r.radius;
  return o;
}
@fragment fn fs(i: VOut) -> @location(0) vec4<f32> {
  let q = abs(i.local) - i.half + vec2(i.radius);
  let d = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - i.radius;
  let a = clamp(0.5 - d, 0.0, 1.0);
  return vec4(i.color.rgb, i.color.a * a);
}
"#;

const PICTURE: &str = r#"
@group(0) @binding(0) var<uniform> dest: vec4<f32>;
@group(0) @binding(1) var tex: texture_2d<f32>;
@group(0) @binding(2) var samp: sampler;
struct VOut { @builtin(position) pos: vec4<f32>, @location(0) uv: vec2<f32> };
@vertex fn vs(@builtin(vertex_index) vi: u32) -> VOut {
  var corners = array<vec2<f32>, 6>(vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 0.0), vec2(1.0, 1.0), vec2(0.0, 1.0));
  let c = corners[vi];
  var o: VOut;
  o.pos = vec4(mix(dest.x, dest.z, c.x), mix(dest.y, dest.w, c.y), 0.0, 1.0);
  o.uv = c;
  return o;
}
@fragment fn fs(i: VOut) -> @location(0) vec4<f32> { return textureSample(tex, samp, i.uv); }
"#;

#[repr(C)]
#[derive(Clone, Copy)]
struct Rect {
    rect: [f32; 4],
    color: [f32; 4],
    radius: f32,
}

impl Rect {
    fn bytes(rects: &[Rect]) -> Vec<u8> {
        let mut out = Vec::with_capacity(rects.len() * 36);
        for r in rects {
            for v in r
                .rect
                .iter()
                .chain(r.color.iter())
                .chain(std::iter::once(&r.radius))
            {
                out.extend_from_slice(&v.to_le_bytes());
            }
        }
        out
    }
}

/// `#RRGGBB` or `#RRGGBBAA` as linear RGBA (the surface is sRGB), times `alpha`.
fn color(hex: &str, alpha: f32) -> [f32; 4] {
    let hex = hex.trim_start_matches('#');
    let byte = |i: usize| u8::from_str_radix(hex.get(i..i + 2).unwrap_or("ff"), 16).unwrap_or(255);
    let linear = |c: u8| {
        let c = f32::from(c) / 255.0;
        if c <= 0.04045 {
            c / 12.92
        } else {
            ((c + 0.055) / 1.055).powf(2.4)
        }
    };
    let a = if hex.len() >= 8 {
        f32::from(byte(6)) / 255.0
    } else {
        1.0
    };
    [linear(byte(0)), linear(byte(2)), linear(byte(4)), a * alpha]
}

/// The same, for glyphon (which takes sRGB bytes).
fn text_color(hex: &str, alpha: f32) -> Color {
    let hex = hex.trim_start_matches('#');
    let byte = |i: usize| u8::from_str_radix(hex.get(i..i + 2).unwrap_or("ff"), 16).unwrap_or(255);
    let a = if hex.len() >= 8 {
        f32::from(byte(6)) / 255.0
    } else {
        1.0
    };
    Color::rgba(byte(0), byte(2), byte(4), (a * alpha * 255.0).round() as u8)
}

struct Gpu {
    instance: wgpu::Instance,
    adapter: wgpu::Adapter,
    device: wgpu::Device,
    queue: wgpu::Queue,
}

/// A song's lyrics laid out for one screen size, with a shaped text buffer per row.
struct Prepared {
    layout: Layout,
    theme: Theme,
    /// Per group, per row: the shaped text and the part boxes.
    rows: Vec<Vec<(Buffer, Vec<PartBox>, f32)>>,
}

struct Screen {
    window: Arc<Window>,
    surface: wgpu::Surface<'static>,
    config: wgpu::SurfaceConfiguration,
    display: String,
    layout: ScreenLayout,
    theme: String,
    refresh: f64,
    atlas: TextAtlas,
    viewport: Viewport,
    text: TextRenderer,
    prepared: Option<(String, u32, u32, Prepared)>,
    waiting: Option<(String, Buffer)>,
}

struct Pipelines {
    rects: wgpu::RenderPipeline,
    rect_layout: wgpu::BindGroupLayout,
    picture: wgpu::RenderPipeline,
    picture_layout: wgpu::BindGroupLayout,
    sampler: wgpu::Sampler,
}

struct Picture {
    texture: wgpu::Texture,
    size: (u32, u32),
    time: f64,
}

struct App {
    view: Arc<Mutex<View>>,
    shared: Arc<Shared>,
    displays: Arc<Mutex<Vec<Display>>>,
    library: ThemeLibrary,
    gpu: Option<Gpu>,
    pipelines: Option<Pipelines>,
    screens: HashMap<WindowId, Screen>,
    fonts: FontSystem,
    swash: SwashCache,
    cache: Option<Cache>,
    feed: Option<(PathBuf, VideoFeed)>,
    picture: Option<Picture>,
    last_check: Instant,
    screen_plan: Vec<(String, ScreenLayout, String)>,
}

fn display_id(monitor: &MonitorHandle) -> String {
    let name = monitor.name().unwrap_or_else(|| "screen".into());
    let size = monitor.size();
    let position = monitor.position();
    let raw = format!(
        "{name}-{}x{}@{},{}",
        size.width, size.height, position.x, position.y
    );
    raw.chars()
        .map(|c| {
            if c.is_alphanumeric() || "-_@,x".contains(c) {
                c
            } else {
                '-'
            }
        })
        .collect()
}

pub fn run(
    view: Arc<Mutex<View>>,
    shared: Arc<Shared>,
    displays: Arc<Mutex<Vec<Display>>>,
    themes: PathBuf,
) -> Result<(), String> {
    let event_loop = EventLoop::new().map_err(|e| e.to_string())?;
    event_loop.set_control_flow(ControlFlow::Poll);
    let mut fonts = FontSystem::new();
    if let Ok(entries) = std::fs::read_dir(themes.join("fonts")) {
        for entry in entries.flatten() {
            if entry.path().extension().is_some_and(|e| e == "ttf") {
                let _ = fonts.db_mut().load_font_file(entry.path());
            }
        }
    }
    let mut app = App {
        view,
        shared,
        displays,
        library: ThemeLibrary::new(themes),
        gpu: None,
        pipelines: None,
        screens: HashMap::new(),
        fonts,
        swash: SwashCache::new(),
        cache: None,
        feed: None,
        picture: None,
        last_check: Instant::now(),
        screen_plan: Vec::new(),
    };
    event_loop.run_app(&mut app).map_err(|e| e.to_string())
}

impl App {
    fn plan(&self, monitors: &[MonitorHandle]) -> Vec<(String, ScreenLayout, String)> {
        let config = self
            .view
            .lock()
            .map(|v| v.config.routing.screens.clone())
            .unwrap_or_default();
        let ids: Vec<String> = monitors.iter().map(display_id).collect();
        if config.is_empty() {
            return ids
                .into_iter()
                .map(|id| (id, ScreenLayout::VideoLyrics, "clasico".to_string()))
                .collect();
        }
        config
            .into_iter()
            .filter(|s| s.layout != ScreenLayout::Off && ids.contains(&s.display))
            .map(|s| (s.display, s.layout, s.theme))
            .collect()
    }

    fn report_displays(&self, event_loop: &ActiveEventLoop) {
        let primary = event_loop.primary_monitor().map(|m| display_id(&m));
        let list = event_loop
            .available_monitors()
            .map(|m| {
                let size = m.size();
                Display {
                    id: display_id(&m),
                    name: m.name().unwrap_or_else(|| "Screen".into()),
                    width: size.width,
                    height: size.height,
                    refresh_hz: f64::from(m.refresh_rate_millihertz().unwrap_or(60_000)) / 1000.0,
                    primary: primary.as_deref() == Some(display_id(&m).as_str()),
                    connected: true,
                }
            })
            .collect();
        if let Ok(mut displays) = self.displays.lock() {
            *displays = list;
        }
    }

    fn ensure_gpu(&mut self, window: &Arc<Window>) -> Option<wgpu::Surface<'static>> {
        if self.gpu.is_none() {
            let instance = wgpu::Instance::new(wgpu::InstanceDescriptor::default());
            let surface = instance.create_surface(window.clone()).ok()?;
            let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            }))?;
            let (device, queue) =
                pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor::default(), None)).ok()?;
            log::info!("drawing on {}", adapter.get_info().name);
            self.cache = Some(Cache::new(&device));
            self.gpu = Some(Gpu {
                instance,
                adapter,
                device,
                queue,
            });
            return Some(surface);
        }
        self.gpu.as_ref()?.instance.create_surface(window.clone()).ok()
    }

    fn ensure_pipelines(&mut self, format: wgpu::TextureFormat) {
        if self.pipelines.is_some() {
            return;
        }
        let Some(gpu) = &self.gpu else { return };
        let device = &gpu.device;
        let blend = Some(wgpu::BlendState::ALPHA_BLENDING);
        let rect_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("screen size"),
            entries: &[wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::VERTEX,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false,
                    min_binding_size: None,
                },
                count: None,
            }],
        });
        let rect_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("rects"),
            source: wgpu::ShaderSource::Wgsl(RECTS.into()),
        });
        let rect_pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: None,
            bind_group_layouts: &[&rect_layout],
            push_constant_ranges: &[],
        });
        let rects = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("rects"),
            layout: Some(&rect_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &rect_shader,
                entry_point: "vs",
                compilation_options: Default::default(),
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: 36,
                    step_mode: wgpu::VertexStepMode::Instance,
                    attributes: &wgpu::vertex_attr_array![0 => Float32x4, 1 => Float32x4, 2 => Float32],
                }],
            },
            fragment: Some(wgpu::FragmentState {
                module: &rect_shader,
                entry_point: "fs",
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });
        let picture_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("picture"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Texture {
                        sample_type: wgpu::TextureSampleType::Float { filterable: true },
                        view_dimension: wgpu::TextureViewDimension::D2,
                        multisampled: false,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                    count: None,
                },
            ],
        });
        let picture_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("picture"),
            source: wgpu::ShaderSource::Wgsl(PICTURE.into()),
        });
        let picture_pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: None,
            bind_group_layouts: &[&picture_layout],
            push_constant_ranges: &[],
        });
        let picture = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("picture"),
            layout: Some(&picture_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &picture_shader,
                entry_point: "vs",
                compilation_options: Default::default(),
                buffers: &[],
            },
            fragment: Some(wgpu::FragmentState {
                module: &picture_shader,
                entry_point: "fs",
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend: None,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });
        let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            ..Default::default()
        });
        self.pipelines = Some(Pipelines {
            rects,
            rect_layout,
            picture,
            picture_layout,
            sampler,
        });
    }

    fn open_screens(&mut self, event_loop: &ActiveEventLoop) {
        let monitors: Vec<MonitorHandle> = event_loop.available_monitors().collect();
        let plan = self.plan(&monitors);
        if plan == self.screen_plan && !self.screens.is_empty() {
            return;
        }
        self.screens.clear();
        self.screen_plan = plan.clone();
        for (display, layout, theme) in plan {
            let Some(monitor) = monitors.iter().find(|m| display_id(m) == display).cloned() else {
                continue;
            };
            let attributes = Window::default_attributes()
                .with_title("Karaoke")
                .with_fullscreen(Some(Fullscreen::Borderless(Some(monitor.clone()))));
            let Ok(window) = event_loop.create_window(attributes) else {
                continue;
            };
            let window = Arc::new(window);
            window.set_cursor_visible(false);
            let Some(surface) = self.ensure_gpu(&window) else {
                continue;
            };
            let gpu = self.gpu.as_ref().expect("made above");
            let caps = surface.get_capabilities(&gpu.adapter);
            let format = caps
                .formats
                .iter()
                .copied()
                .find(wgpu::TextureFormat::is_srgb)
                .unwrap_or(caps.formats[0]);
            let size = window.inner_size();
            let config = wgpu::SurfaceConfiguration {
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                format,
                width: size.width.max(1),
                height: size.height.max(1),
                present_mode: wgpu::PresentMode::Fifo,
                desired_maximum_frame_latency: 1,
                alpha_mode: caps.alpha_modes[0],
                view_formats: vec![],
            };
            surface.configure(&gpu.device, &config);
            let cache = self.cache.as_ref().expect("made with the gpu");
            let mut atlas = TextAtlas::new(&gpu.device, &gpu.queue, cache, format);
            let text = TextRenderer::new(&mut atlas, &gpu.device, wgpu::MultisampleState::default(), None);
            let viewport = Viewport::new(&gpu.device, cache);
            self.ensure_pipelines(format);
            let refresh = f64::from(monitor.refresh_rate_millihertz().unwrap_or(60_000)) / 1000.0;
            log::info!(
                "screen {display}: {}x{} at {refresh} Hz, {:?}",
                config.width,
                config.height,
                layout
            );
            self.screens.insert(
                window.id(),
                Screen {
                    window,
                    surface,
                    config,
                    display,
                    layout,
                    theme,
                    refresh,
                    atlas,
                    viewport,
                    text,
                    prepared: None,
                    waiting: None,
                },
            );
        }
    }

    fn prepare(&mut self, id: WindowId, program: &Program) {
        let Some(screen) = self.screens.get_mut(&id) else {
            return;
        };
        let (w, h) = (screen.config.width, screen.config.height);
        let key = format!(
            "{}:{}:{}",
            program.item.id, program.manifest.content_id, screen.theme
        );
        if screen
            .prepared
            .as_ref()
            .is_some_and(|(k, pw, ph, _)| *k == key && *pw == w && *ph == h)
        {
            return;
        }
        let Ok(theme) = self
            .library
            .theme(&screen.theme)
            .or_else(|_| self.library.theme("clasico"))
        else {
            return;
        };
        let Ok(metrics) = self.library.metrics(&theme) else {
            return;
        };
        let layout = build_layout(
            &program.lyrics.lines,
            &program.lyrics.singers,
            &theme,
            f64::from(w),
            f64::from(h),
            &metrics,
        );
        let family = theme.font.family.clone();
        let weight = Weight(theme.font.weight as u16);
        let rows = layout
            .groups
            .iter()
            .map(|group| {
                group
                    .rows
                    .iter()
                    .map(|row| {
                        let px = (layout.font_px * row.scale) as f32;
                        let line = px * theme.layout.line_spacing as f32;
                        let mut buffer = Buffer::new(&mut self.fonts, Metrics::new(px, line));
                        buffer.set_size(&mut self.fonts, Some(row.width as f32 * 1.2 + px), Some(line));
                        buffer.set_text(
                            &mut self.fonts,
                            &row.text,
                            Attrs::new().family(Family::Name(&family)).weight(weight),
                            Shaping::Advanced,
                        );
                        buffer.shape_until_scroll(&mut self.fonts, false);
                        // Part boxes from the same advance widths the layout used.
                        let mut boxes = Vec::new();
                        let mut x = 0.0;
                        let space = metrics.width(" ", f64::from(px));
                        for (i, word) in row.words.iter().enumerate() {
                            if i > 0 {
                                x += space;
                            }
                            for part in &word.parts {
                                let width = metrics.width(&part.text, f64::from(px));
                                boxes.push(PartBox { x0: x, x1: x + width });
                                x += width;
                            }
                        }
                        (buffer, boxes, line)
                    })
                    .collect()
            })
            .collect();
        screen.prepared = Some((key, w, h, Prepared { layout, theme, rows }));
    }

    fn update_video(&mut self, program: Option<&Arc<Program>>) {
        let wanted = program.and_then(|p| p.video.clone());
        let same = match (&self.feed, &wanted) {
            (Some((path, _)), Some(w)) => path == w,
            (None, None) => true,
            _ => false,
        };
        if same {
            return;
        }
        self.picture = None;
        self.feed = wanted.and_then(|path| {
            let offset = program
                .and_then(|p| {
                    p.manifest
                        .tracks
                        .iter()
                        .find(|t| t.video.is_some())
                        .map(|t| t.offset)
                })
                .unwrap_or(0.0);
            match VideoFeed::open(path.clone(), offset, 1080) {
                Ok(feed) => {
                    log::info!("video decoding: {}", feed.hardware.unwrap_or("software"));
                    Some((path, feed))
                }
                Err(error) => {
                    log::warn!("no video: {error}");
                    None
                }
            }
        });
    }

    fn upload_frame(&mut self, t: f64) {
        let (Some((_, feed)), Some(gpu)) = (&self.feed, &self.gpu) else {
            return;
        };
        let Some(frame) = feed.frame_at(t) else { return };
        if self
            .picture
            .as_ref()
            .is_some_and(|p| p.time == frame.time && p.size == (frame.width, frame.height))
        {
            return;
        }
        let size = (frame.width, frame.height);
        if self.picture.as_ref().is_none_or(|p| p.size != size) {
            let texture = gpu.device.create_texture(&wgpu::TextureDescriptor {
                label: Some("video"),
                size: wgpu::Extent3d {
                    width: size.0,
                    height: size.1,
                    depth_or_array_layers: 1,
                },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: wgpu::TextureFormat::Rgba8UnormSrgb,
                usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                view_formats: &[],
            });
            self.picture = Some(Picture {
                texture,
                size,
                time: -1.0,
            });
        }
        let picture = self.picture.as_mut().expect("made above");
        gpu.queue.write_texture(
            wgpu::ImageCopyTexture {
                texture: &picture.texture,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            &frame.rgba,
            wgpu::ImageDataLayout {
                offset: 0,
                bytes_per_row: Some(size.0 * 4),
                rows_per_image: Some(size.1),
            },
            wgpu::Extent3d {
                width: size.0,
                height: size.1,
                depth_or_array_layers: 1,
            },
        );
        picture.time = frame.time;
    }

    fn draw(&mut self, id: WindowId) {
        let (program, timeline, state, upcoming, download, display_ms) = {
            let Ok(view) = self.view.lock() else { return };
            let display = self
                .screens
                .get(&id)
                .map(|s| s.display.clone())
                .unwrap_or_default();
            (
                view.program.clone(),
                view.timeline.clone(),
                view.state,
                view.upcoming_title
                    .clone()
                    .map(|(t, a)| (t, a, view.upcoming.as_ref().and_then(|i| i.singer.clone()))),
                view.download,
                view.config
                    .calibration
                    .display_ms
                    .get(&display)
                    .copied()
                    .unwrap_or(0.0),
            )
        };
        self.update_video(program.as_ref());
        let Some(screen) = self.screens.get(&id) else {
            return;
        };
        // The instant this frame will be seen: the next vsync, plus the panel's own latency.
        let refresh_us = (1e6 / screen.refresh.max(1.0)) as i64;
        let shown_at = crate::clock::now_us() + refresh_us + (display_ms * 1000.0) as i64;
        let position = match self.shared.master.snapshot() {
            Some(snapshot) if snapshot.rate > 0.0 => snapshot.position_at(shown_at),
            _ => timeline.position_at(shown_at).unwrap_or(0.0),
        };
        let layout_kind = screen.layout;
        if let Some(program) = &program {
            self.prepare(id, program);
        }
        if matches!(layout_kind, ScreenLayout::VideoLyrics | ScreenLayout::Video) {
            self.upload_frame(position);
        }
        let waiting = program.is_none()
            || matches!(
                state,
                PlaybackState::Loading | PlaybackState::Idle | PlaybackState::Waiting
            );
        let (Some(gpu), Some(pipelines)) = (&self.gpu, &self.pipelines) else {
            return;
        };
        let Some(screen) = self.screens.get_mut(&id) else {
            return;
        };
        let (w, h) = (screen.config.width as f32, screen.config.height as f32);
        let Ok(frame) = screen.surface.get_current_texture() else {
            screen.surface.configure(&gpu.device, &screen.config);
            return;
        };
        let target = frame.texture.create_view(&wgpu::TextureViewDescriptor::default());
        let mut rects: Vec<Rect> = Vec::new();
        let mut areas: Vec<(usize, usize, f32, f32, Color, TextBounds)> = Vec::new();
        let show_lyrics = matches!(layout_kind, ScreenLayout::VideoLyrics | ScreenLayout::Lyrics) && !waiting;
        if let (true, Some((_, _, _, prepared))) = (show_lyrics, screen.prepared.as_ref()) {
            let theme = &prepared.theme;
            let t = position + theme.animation.anticipation;
            let scene = scene_at(&prepared.layout, t, theme.animation.transition);
            let fill = if theme.animation.fill == "word" {
                Fill::Word
            } else {
                Fill::Wipe
            };
            if layout_kind == ScreenLayout::VideoLyrics && self.picture.is_some() {
                // A band under the lyrics so they read on any video.
                rects.push(Rect {
                    rect: [0.0, h * 0.62, w, h * 0.38],
                    color: color("#000000", 0.45),
                    radius: 0.0,
                });
            }
            for (index, opacity) in &scene.groups {
                let group = &prepared.layout.groups[*index];
                for (r, row) in group.rows.iter().enumerate() {
                    let (_, boxes, line) = &prepared.rows[*index][r];
                    let left = (row.x - row.width / 2.0) as f32;
                    let top = (row.y + scene.offset) as f32 - line / 2.0;
                    let alpha = *opacity as f32
                        * if row.role == kp_proto::Role::Backing {
                            theme.backing.opacity as f32
                        } else {
                            1.0
                        };
                    let px = (prepared.layout.font_px * row.scale) as f32;
                    let outline = (theme.layout.outline_width as f32 * px).max(1.0);
                    let full = TextBounds {
                        left: 0,
                        top: 0,
                        right: w as i32,
                        bottom: h as i32,
                    };
                    for (dx, dy) in [
                        (-1.0, 0.0),
                        (1.0, 0.0),
                        (0.0, -1.0),
                        (0.0, 1.0),
                        (-0.7, -0.7),
                        (0.7, -0.7),
                        (-0.7, 0.7),
                        (0.7, 0.7),
                    ] {
                        areas.push((
                            *index,
                            r,
                            left + dx * outline,
                            top + dy * outline,
                            text_color(&theme.colors.outline, alpha),
                            full,
                        ));
                    }
                    areas.push((
                        *index,
                        r,
                        left,
                        top,
                        text_color(&theme.colors.unsung, alpha),
                        full,
                    ));
                    let segments = fill_segments(row, boxes, fill);
                    let edge = fill_x(&segments, t) as f32;
                    if edge > 0.0 {
                        let sung = TextBounds {
                            left: 0,
                            top: 0,
                            right: (left + edge).ceil() as i32,
                            bottom: h as i32,
                        };
                        areas.push((*index, r, left, top, text_color(&row.color, alpha), sung));
                    }
                }
            }
            for dot in &scene.dots {
                let r = dot.r as f32;
                rects.push(Rect {
                    rect: [dot.x as f32 - r, dot.y as f32 - r, 2.0 * r, 2.0 * r],
                    color: color(&theme.colors.sung, 1.0),
                    radius: r,
                });
            }
            if let Some((bar, progress)) = &scene.bar {
                let (x, y, bw, bh) = (
                    (bar.x - bar.width / 2.0) as f32,
                    (bar.y - bar.height / 2.0) as f32,
                    bar.width as f32,
                    bar.height as f32,
                );
                rects.push(Rect {
                    rect: [x, y, bw, bh],
                    color: color(&theme.colors.unsung, 0.3),
                    radius: bh / 2.0,
                });
                rects.push(Rect {
                    rect: [x, y, bw * *progress as f32, bh],
                    color: color(&theme.colors.sung, 1.0),
                    radius: bh / 2.0,
                });
            }
        }
        // The waiting screen: who sings next, and how the download goes.
        let mut waiting_text = None;
        if waiting {
            rects.push(Rect {
                rect: [0.0, 0.0, w, h],
                color: color("#0B0F2A", 1.0),
                radius: 0.0,
            });
            let text = match &upcoming {
                Some((title, artist, singer)) => {
                    let mut text = format!("A seguir\n{title}");
                    if let Some(artist) = artist {
                        text.push_str(&format!("\n{artist}"));
                    }
                    if let Some(singer) = singer {
                        text.push_str(&format!("\n♪ {singer}"));
                    }
                    text
                }
                None => "Karaoke".to_string(),
            };
            if let Some((_, fraction)) = download.filter(|(s, _)| *s != kp_proto::CacheState::Ready) {
                let bw = w * 0.4;
                rects.push(Rect {
                    rect: [(w - bw) / 2.0, h * 0.8, bw, h * 0.012],
                    color: color("#FFFFFF", 0.2),
                    radius: h * 0.006,
                });
                rects.push(Rect {
                    rect: [(w - bw) / 2.0, h * 0.8, bw * fraction as f32, h * 0.012],
                    color: color("#FFC531", 1.0),
                    radius: h * 0.006,
                });
            }
            if screen.waiting.as_ref().is_none_or(|(t, _)| *t != text) {
                let size = h * 0.06;
                let mut buffer = Buffer::new(&mut self.fonts, Metrics::new(size, size * 1.3));
                buffer.set_size(&mut self.fonts, Some(w * 0.8), Some(h * 0.6));
                buffer.set_text(
                    &mut self.fonts,
                    &text,
                    Attrs::new()
                        .family(Family::Name("Nunito Black"))
                        .weight(Weight(900)),
                    Shaping::Advanced,
                );
                buffer.shape_until_scroll(&mut self.fonts, false);
                screen.waiting = Some((text.clone(), buffer));
            }
            waiting_text = Some(text);
        }

        screen.viewport.update(
            &gpu.queue,
            Resolution {
                width: screen.config.width,
                height: screen.config.height,
            },
        );
        let mut text_areas: Vec<TextArea<'_>> = Vec::new();
        if let Some((_, _, _, prepared)) = screen.prepared.as_ref() {
            for (g, r, left, top, color, bounds) in &areas {
                text_areas.push(TextArea {
                    buffer: &prepared.rows[*g][*r].0,
                    left: *left,
                    top: *top,
                    scale: 1.0,
                    bounds: *bounds,
                    default_color: *color,
                    custom_glyphs: &[],
                });
            }
        }
        if let (Some(_), Some((_, buffer))) = (&waiting_text, screen.waiting.as_ref()) {
            text_areas.push(TextArea {
                buffer,
                left: w * 0.1,
                top: h * 0.3,
                scale: 1.0,
                bounds: TextBounds {
                    left: 0,
                    top: 0,
                    right: w as i32,
                    bottom: h as i32,
                },
                default_color: Color::rgb(255, 255, 255),
                custom_glyphs: &[],
            });
        }
        if let Err(error) = screen.text.prepare(
            &gpu.device,
            &gpu.queue,
            &mut self.fonts,
            &mut screen.atlas,
            &screen.viewport,
            text_areas,
            &mut self.swash,
        ) {
            log::warn!("text: {error}");
        }

        let screen_size = gpu.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("screen size"),
            contents: &[
                w.to_le_bytes(),
                h.to_le_bytes(),
                0f32.to_le_bytes(),
                0f32.to_le_bytes(),
            ]
            .concat(),
            usage: wgpu::BufferUsages::UNIFORM,
        });
        let rect_group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: None,
            layout: &pipelines.rect_layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: screen_size.as_entire_binding(),
            }],
        });
        let rect_buffer = (!rects.is_empty()).then(|| {
            gpu.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some("rects"),
                contents: &Rect::bytes(&rects),
                usage: wgpu::BufferUsages::VERTEX,
            })
        });
        let picture_group = match (
            &self.picture,
            matches!(layout_kind, ScreenLayout::VideoLyrics | ScreenLayout::Video) && !waiting,
        ) {
            (Some(picture), true) => {
                // Fit the picture inside the screen, keeping its aspect.
                let (pw, ph) = (picture.size.0 as f32, picture.size.1 as f32);
                let scale = (w / pw).min(h / ph);
                let (dw, dh) = (pw * scale / w, ph * scale / h);
                let dest = [-dw, dh, dw, -dh];
                let uniform = gpu.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("picture rect"),
                    contents: &dest.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<u8>>(),
                    usage: wgpu::BufferUsages::UNIFORM,
                });
                let view = picture
                    .texture
                    .create_view(&wgpu::TextureViewDescriptor::default());
                Some(gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
                    label: None,
                    layout: &pipelines.picture_layout,
                    entries: &[
                        wgpu::BindGroupEntry {
                            binding: 0,
                            resource: uniform.as_entire_binding(),
                        },
                        wgpu::BindGroupEntry {
                            binding: 1,
                            resource: wgpu::BindingResource::TextureView(&view),
                        },
                        wgpu::BindGroupEntry {
                            binding: 2,
                            resource: wgpu::BindingResource::Sampler(&pipelines.sampler),
                        },
                    ],
                }))
            }
            _ => None,
        };
        let mut encoder = gpu
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("frame") });
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("screen"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &target,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            if let Some(group) = &picture_group {
                pass.set_pipeline(&pipelines.picture);
                pass.set_bind_group(0, group, &[]);
                pass.draw(0..6, 0..1);
            }
            if let Some(buffer) = &rect_buffer {
                pass.set_pipeline(&pipelines.rects);
                pass.set_bind_group(0, &rect_group, &[]);
                pass.set_vertex_buffer(0, buffer.slice(..));
                pass.draw(0..6, 0..rects.len() as u32);
            }
            if let Err(error) = screen.text.render(&screen.atlas, &screen.viewport, &mut pass) {
                log::warn!("text: {error}");
            }
        }
        gpu.queue.submit(Some(encoder.finish()));
        screen.window.pre_present_notify();
        frame.present();
        screen.atlas.trim();
    }
}

impl ApplicationHandler for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        self.report_displays(event_loop);
        self.open_screens(event_loop);
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, id: WindowId, event: WindowEvent) {
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::KeyboardInput { event, .. }
                if event.logical_key == winit::keyboard::Key::Named(winit::keyboard::NamedKey::Escape) =>
            {
                event_loop.exit()
            }
            WindowEvent::Resized(size) => {
                if let (Some(screen), Some(gpu)) = (self.screens.get_mut(&id), &self.gpu) {
                    screen.config.width = size.width.max(1);
                    screen.config.height = size.height.max(1);
                    screen.surface.configure(&gpu.device, &screen.config);
                    screen.prepared = None;
                }
            }
            WindowEvent::RedrawRequested => self.draw(id),
            _ => {}
        }
    }

    fn about_to_wait(&mut self, event_loop: &ActiveEventLoop) {
        if self.last_check.elapsed() > Duration::from_secs(2) {
            // Screens plugged in or out, or a new plan from the control.
            self.last_check = Instant::now();
            self.report_displays(event_loop);
            self.open_screens(event_loop);
        }
        for screen in self.screens.values() {
            screen.window.request_redraw();
        }
    }
}
