//! Decoding with ffmpeg (decision 001).
//!
//! - [`decode_audio`]: a whole stem (Opus in Ogg) to interleaved stereo f32 at 48 kHz, with its
//!   pre-skip already dropped (the Ogg demuxer marks it and libavcodec skips it), so sample 0 is
//!   song time 0 plus the track's offset.
//! - [`VideoDecoder`]: frames in order with their time in seconds, as RGBA at the size asked,
//!   seeking to the keyframe before a position. It tries the platform's hardware decoder first
//!   (D3D11VA on Windows, VideoToolbox on macOS, CUDA on NVIDIA) and falls back to software.
//!
//! This is the one crate allowed `unsafe`: setting up a hardware device is not in ffmpeg-next's
//! safe API.

use std::path::Path;
use std::sync::Once;

use ffmpeg::format::{Pixel, Sample, sample::Type as SampleType};
use ffmpeg::media::Type;
use ffmpeg::software::{resampling, scaling};
use ffmpeg::util::{channel_layout::ChannelLayout, frame};
use ffmpeg_next as ffmpeg;

pub const RATE: u32 = 48_000;

#[derive(Debug, thiserror::Error)]
pub enum MediaError {
    #[error("ffmpeg: {0}")]
    Ffmpeg(#[from] ffmpeg::Error),
    #[error("{0} has no {1} stream")]
    NoStream(String, &'static str),
}

fn init() {
    static ONCE: Once = Once::new();
    ONCE.call_once(|| {
        ffmpeg::init().expect("ffmpeg initialises");
        ffmpeg::util::log::set_level(ffmpeg::util::log::Level::Error);
    });
}

/// A whole audio file as interleaved stereo f32 at 48 kHz.
pub fn decode_audio(path: &Path) -> Result<Vec<f32>, MediaError> {
    init();
    let mut input = ffmpeg::format::input(path)?;
    let stream = input
        .streams()
        .best(Type::Audio)
        .ok_or_else(|| MediaError::NoStream(path.display().to_string(), "audio"))?;
    let index = stream.index();
    let context = ffmpeg::codec::context::Context::from_parameters(stream.parameters())?;
    let mut decoder = context.decoder().audio()?;
    let layout = if decoder.channel_layout().is_empty() {
        ChannelLayout::default(i32::from(decoder.channels()))
    } else {
        decoder.channel_layout()
    };
    decoder.set_channel_layout(layout);
    let mut resampler = resampling::Context::get(
        decoder.format(),
        layout,
        decoder.rate(),
        Sample::F32(SampleType::Packed),
        ChannelLayout::STEREO,
        RATE,
    )?;
    let mut samples = Vec::new();
    let mut decoded = frame::Audio::empty();
    let push = |decoded: &frame::Audio,
                resampler: &mut resampling::Context,
                samples: &mut Vec<f32>|
     -> Result<(), MediaError> {
        let mut out = frame::Audio::empty();
        resampler.run(decoded, &mut out)?;
        append(&out, samples);
        Ok(())
    };
    for (stream, packet) in input.packets() {
        if stream.index() != index {
            continue;
        }
        decoder.send_packet(&packet)?;
        while decoder.receive_frame(&mut decoded).is_ok() {
            push(&decoded, &mut resampler, &mut samples)?;
        }
    }
    decoder.send_eof()?;
    while decoder.receive_frame(&mut decoded).is_ok() {
        push(&decoded, &mut resampler, &mut samples)?;
    }
    // What the resampler still holds.
    loop {
        let mut out = frame::Audio::empty();
        if resampler.flush(&mut out).is_err() || out.samples() == 0 {
            break;
        }
        append(&out, &mut samples);
    }
    Ok(samples)
}

fn append(frame: &frame::Audio, samples: &mut Vec<f32>) {
    let count = frame.samples() * 2;
    if count == 0 {
        return;
    }
    let data = frame.data(0);
    let floats = data[..count * 4]
        .chunks_exact(4)
        .map(|b| f32::from_ne_bytes([b[0], b[1], b[2], b[3]]));
    samples.extend(floats);
}

/// One decoded picture.
#[derive(Clone, Debug)]
pub struct VideoFrame {
    pub time: f64,
    pub width: u32,
    pub height: u32,
    /// RGBA rows, `width * 4` bytes each.
    pub rgba: Vec<u8>,
}

pub struct VideoDecoder {
    input: ffmpeg::format::context::Input,
    index: usize,
    decoder: ffmpeg::decoder::Video,
    scaler: Option<(scaling::Context, Pixel, u32, u32)>,
    time_base: f64,
    width: u32,
    height: u32,
    pub hardware: Option<&'static str>,
    eof: bool,
}

impl VideoDecoder {
    /// Opens `path`, scaling frames to fit `max_height` (keeping the aspect).
    pub fn open(path: &Path, max_height: u32, try_hardware: bool) -> Result<Self, MediaError> {
        init();
        let input = ffmpeg::format::input(path)?;
        let stream = input
            .streams()
            .best(Type::Video)
            .ok_or_else(|| MediaError::NoStream(path.display().to_string(), "video"))?;
        let index = stream.index();
        let time_base = f64::from(stream.time_base());
        let mut context = ffmpeg::codec::context::Context::from_parameters(stream.parameters())?;
        let hardware = if try_hardware {
            hw::attach(&mut context)
        } else {
            None
        };
        let decoder = context.decoder().video()?;
        let (w, h) = (decoder.width().max(1), decoder.height().max(1));
        let height = h.min(max_height.max(2)) & !1;
        let width = ((u64::from(w) * u64::from(height) / u64::from(h)) as u32).max(2) & !1;
        Ok(Self {
            input,
            index,
            decoder,
            scaler: None,
            time_base,
            width,
            height,
            hardware,
            eof: false,
        })
    }

    pub fn size(&self) -> (u32, u32) {
        (self.width, self.height)
    }

    /// Jumps to the keyframe at or before `seconds`; the next frames lead up to it.
    pub fn seek(&mut self, seconds: f64) -> Result<(), MediaError> {
        let ts = (seconds.max(0.0) * f64::from(ffmpeg::ffi::AV_TIME_BASE)) as i64;
        self.input.seek(ts, ..ts)?;
        self.decoder.flush();
        self.eof = false;
        Ok(())
    }

    /// The next frame, or `None` at the end.
    pub fn next_frame(&mut self) -> Result<Option<VideoFrame>, MediaError> {
        self.next_frame_from(f64::NEG_INFINITY)
    }

    /// The next frame that starts at `from` seconds or later. The ones before are decoded (they
    /// are needed for the ones after) but neither copied out of the GPU nor converted, which is
    /// most of the cost: catching up from a keyframe after a seek is several times faster.
    pub fn next_frame_from(&mut self, from: f64) -> Result<Option<VideoFrame>, MediaError> {
        let mut decoded = frame::Video::empty();
        loop {
            if self.decoder.receive_frame(&mut decoded).is_ok() {
                let pts = decoded.timestamp().or(decoded.pts()).unwrap_or(0);
                if (pts as f64) * self.time_base + 0.05 < from {
                    continue;
                }
                let decoded = hw::download(std::mem::replace(&mut decoded, frame::Video::empty()));
                return Ok(Some(self.convert(&decoded)?));
            }
            if self.eof {
                return Ok(None);
            }
            let mut sent = false;
            for (stream, packet) in self.input.packets() {
                if stream.index() == self.index {
                    self.decoder.send_packet(&packet)?;
                    sent = true;
                    break;
                }
            }
            if !sent {
                self.decoder.send_eof()?;
                self.eof = true;
            }
        }
    }

    fn convert(&mut self, decoded: &frame::Video) -> Result<VideoFrame, MediaError> {
        let format = decoded.format();
        let (sw, sh) = (decoded.width(), decoded.height());
        let rebuild = self
            .scaler
            .as_ref()
            .is_none_or(|(_, f, w, h)| *f != format || *w != sw || *h != sh);
        if rebuild {
            let context = scaling::Context::get(
                format,
                sw,
                sh,
                Pixel::RGBA,
                self.width,
                self.height,
                scaling::Flags::BILINEAR,
            )?;
            self.scaler = Some((context, format, sw, sh));
        }
        let (scaler, ..) = self.scaler.as_mut().expect("built above");
        let mut rgba = frame::Video::empty();
        scaler.run(decoded, &mut rgba)?;
        let stride = rgba.stride(0);
        let row = self.width as usize * 4;
        let mut pixels = Vec::with_capacity(row * self.height as usize);
        for y in 0..self.height as usize {
            pixels.extend_from_slice(&rgba.data(0)[y * stride..y * stride + row]);
        }
        let pts = decoded.timestamp().or(decoded.pts()).unwrap_or(0);
        Ok(VideoFrame {
            time: pts as f64 * self.time_base,
            width: self.width,
            height: self.height,
            rgba: pixels,
        })
    }
}

#[allow(unsafe_code)]
mod hw {
    use super::*;
    use ffmpeg::ffi;

    fn kinds() -> &'static [(ffi::AVHWDeviceType, &'static str)] {
        if cfg!(target_os = "windows") {
            &[
                (ffi::AVHWDeviceType::AV_HWDEVICE_TYPE_D3D11VA, "d3d11va"),
                (ffi::AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA, "cuda"),
            ]
        } else if cfg!(target_os = "macos") {
            &[(ffi::AVHWDeviceType::AV_HWDEVICE_TYPE_VIDEOTOOLBOX, "videotoolbox")]
        } else {
            &[
                (ffi::AVHWDeviceType::AV_HWDEVICE_TYPE_CUDA, "cuda"),
                (ffi::AVHWDeviceType::AV_HWDEVICE_TYPE_VAAPI, "vaapi"),
            ]
        }
    }

    /// Gives the decoder a hardware device when one opens; returns its name.
    pub fn attach(context: &mut ffmpeg::codec::context::Context) -> Option<&'static str> {
        for (kind, name) in kinds() {
            let mut device: *mut ffi::AVBufferRef = std::ptr::null_mut();
            // SAFETY: ffmpeg allocates `device`; on success the codec context takes a new
            // reference and we drop ours.
            unsafe {
                if ffi::av_hwdevice_ctx_create(&mut device, *kind, std::ptr::null(), std::ptr::null_mut(), 0)
                    >= 0
                {
                    (*context.as_mut_ptr()).hw_device_ctx = ffi::av_buffer_ref(device);
                    ffi::av_buffer_unref(&mut device);
                    log::info!("video decoding on {name}");
                    return Some(name);
                }
            }
        }
        None
    }

    /// A frame in GPU memory copied to system memory (others pass through).
    pub fn download(decoded: frame::Video) -> frame::Video {
        // SAFETY: reads the frame's own fields; the transfer writes a fresh frame.
        unsafe {
            if (*decoded.as_ptr()).hw_frames_ctx.is_null() {
                return decoded;
            }
            let mut software = frame::Video::empty();
            if ffi::av_hwframe_transfer_data(software.as_mut_ptr(), decoded.as_ptr(), 0) < 0 {
                return decoded;
            }
            (*software.as_mut_ptr()).pts = (*decoded.as_ptr()).pts;
            (*software.as_mut_ptr()).best_effort_timestamp = (*decoded.as_ptr()).best_effort_timestamp;
            software
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    fn make(name: &str, args: &[&str]) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("kp-media-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(name);
        let status = Command::new("ffmpeg")
            .args(["-nostdin", "-v", "error", "-y"])
            .args(args)
            .arg(&path)
            .status();
        assert!(
            status.map(|s| s.success()).unwrap_or(false),
            "ffmpeg is needed for these tests"
        );
        path
    }

    #[test]
    fn opus_decodes_to_the_exact_length_at_48k() {
        let path = make(
            "tone.opus",
            &[
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2:sample_rate=44100",
                "-ac",
                "2",
                "-c:a",
                "libopus",
                "-b:a",
                "128k",
                "-f",
                "ogg",
            ],
        );
        let samples = decode_audio(&path).unwrap();
        let frames = samples.len() / 2;
        // The pre-skip is gone: 2 s at 48 kHz, give or take a resampler's tail.
        assert!((frames as i64 - 96_000).abs() < 200, "{frames} frames");
        let peak = samples.iter().fold(0f32, |m, s| m.max(s.abs()));
        assert!(peak > 0.05 && peak < 1.0, "peak {peak}");
    }

    #[test]
    fn video_frames_come_in_order_and_seek_works() {
        let path = make(
            "count.mp4",
            &[
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=25:duration=3",
                "-c:v",
                "libx264",
                "-g",
                "25",
                "-pix_fmt",
                "yuv420p",
            ],
        );
        let mut video = VideoDecoder::open(&path, 120, false).unwrap();
        assert_eq!(video.size(), (160, 120));
        let first = video.next_frame().unwrap().unwrap();
        assert_eq!(first.rgba.len(), 160 * 120 * 4);
        assert!(first.time.abs() < 0.05);
        let second = video.next_frame().unwrap().unwrap();
        assert!((second.time - 0.04).abs() < 0.01);
        video.seek(2.0).unwrap();
        let after = video.next_frame().unwrap().unwrap();
        assert!(after.time <= 2.0 + 1e-6 && after.time >= 1.0, "{}", after.time);
        let mut last = after.time;
        while let Some(frame) = video.next_frame().unwrap() {
            assert!(frame.time > last);
            last = frame.time;
        }
        assert!(last > 2.8);
    }
}
