//! A whole stem (Opus in Ogg) to interleaved stereo f32 at 48 kHz, with libopus.
//!
//! The Ogg pages are read in Rust (`ogg`); each Opus packet goes to libopus (`opus`, built from
//! source with cmake when the system has none). As the Opus spec says, the first `pre-skip`
//! samples of the stream are dropped and the last page's granule position says where the song
//! ends (the encoder pads the last packet), so sample 0 is the song's t = 0 plus the track's
//! offset and nothing is padded at the end.

use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use ogg::PacketReader;
use opus::{Channels, Decoder};

/// The longest Opus packet: 120 ms at 48 kHz.
const MAX_FRAME: usize = 5760;

struct Head {
    channels: usize,
    preskip: usize,
}

fn head(packet: &[u8]) -> Result<Head, String> {
    if packet.len() < 19 || &packet[..8] != b"OpusHead" {
        return Err("not an Opus stream (no OpusHead)".into());
    }
    let channels = usize::from(packet[9]);
    if !(1..=2).contains(&channels) {
        return Err(format!("{channels} channels: only mono and stereo are played"));
    }
    let preskip = usize::from(u16::from_le_bytes([packet[10], packet[11]]));
    Ok(Head { channels, preskip })
}

pub fn decode_audio(path: &Path) -> Result<Vec<f32>, String> {
    let file = File::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut reader = PacketReader::new(BufReader::new(file));
    let mut next = || {
        reader
            .read_packet()
            .map_err(|e| format!("{}: {e}", path.display()))
    };
    let first = next()?.ok_or("an empty file")?;
    let head = head(&first.data)?;
    next()?.ok_or("no OpusTags")?; // the comments: nothing to play
    let channels = if head.channels == 1 {
        Channels::Mono
    } else {
        Channels::Stereo
    };
    let mut decoder = Decoder::new(48_000, channels).map_err(|e| e.to_string())?;
    let mut buffer = vec![0f32; MAX_FRAME * head.channels];
    let mut stereo: Vec<f32> = Vec::new();
    let mut granule: Option<u64> = None;
    while let Some(packet) = next()? {
        let frames = decoder
            .decode_float(&packet.data, &mut buffer, false)
            .map_err(|e| format!("{}: {e}", path.display()))?;
        let decoded = &buffer[..frames * head.channels];
        if head.channels == 2 {
            stereo.extend_from_slice(decoded);
        } else {
            stereo.extend(decoded.iter().flat_map(|&s| [s, s]));
        }
        if packet.last_in_page() {
            granule = Some(packet.absgp_page());
        }
    }
    let total = stereo.len() / 2;
    let start = head.preskip.min(total);
    let end = granule
        .and_then(|g| usize::try_from(g).ok())
        .unwrap_or(total)
        .min(total)
        .max(start);
    Ok(stereo[start * 2..end * 2].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ogg::{PacketWriteEndInfo, PacketWriter};
    use opus::{Application, Encoder};

    /// Writes `seconds` of a stereo sine in Opus, as the engine does; returns how many frames.
    fn tone(path: &Path, seconds: f64) -> usize {
        let frames = (seconds * 48_000.0) as usize;
        let mut encoder = Encoder::new(48_000, Channels::Stereo, Application::Audio).unwrap();
        let preskip = encoder.get_lookahead().unwrap() as usize;
        let mut head = b"OpusHead".to_vec();
        head.extend_from_slice(&[1, 2]);
        head.extend_from_slice(&(preskip as u16).to_le_bytes());
        head.extend_from_slice(&48_000u32.to_le_bytes());
        head.extend_from_slice(&[0, 0, 0]);
        let mut writer = PacketWriter::new(File::create(path).unwrap());
        writer
            .write_packet(head, 1, PacketWriteEndInfo::EndPage, 0)
            .unwrap();
        let mut tags = b"OpusTags".to_vec();
        tags.extend_from_slice(&[0; 8]);
        writer
            .write_packet(tags, 1, PacketWriteEndInfo::EndPage, 0)
            .unwrap();
        // The song, then silence for the encoder's lookahead, in 20 ms packets.
        let padded = (frames + preskip).div_ceil(960) * 960;
        let samples: Vec<f32> = (0..padded)
            .flat_map(|i| {
                let s = if i < frames {
                    (2.0 * std::f32::consts::PI * 440.0 * i as f32 / 48_000.0).sin() * 0.5
                } else {
                    0.0
                };
                [s, s]
            })
            .collect();
        let mut packet = vec![0u8; 4000];
        let count = samples.len() / (960 * 2);
        for (n, chunk) in samples.chunks(960 * 2).enumerate() {
            let size = encoder.encode_float(chunk, &mut packet).unwrap();
            let last = n + 1 == count;
            // The last page's granule position: where the song ends, counted with the pre-skip.
            let granule = if last { preskip + frames } else { (n + 1) * 960 } as u64;
            let end = if last {
                PacketWriteEndInfo::EndStream
            } else {
                PacketWriteEndInfo::NormalPacket
            };
            writer
                .write_packet(packet[..size].to_vec(), 1, end, granule)
                .unwrap();
        }
        frames
    }

    #[test]
    fn opus_decodes_to_the_exact_length_at_48k() {
        let path = std::env::temp_dir().join(format!("kp-tone-{}.opus", std::process::id()));
        let frames = tone(&path, 1.5);
        let samples = decode_audio(&path).unwrap();
        let _ = std::fs::remove_file(&path);
        // 1.5 s of stereo: the pre-skip is gone and the padding of the last packet too.
        assert_eq!(samples.len(), 2 * frames);
        let peak = samples.iter().fold(0f32, |m, s| m.max(s.abs()));
        assert!(peak > 0.3, "the tone, not silence: {peak}");
        // It starts on time: lined up against the sine, the best lag is none (the pre-skip went).
        let sine = |i: i64| (2.0 * std::f32::consts::PI * 440.0 * i as f32 / 48_000.0).sin() * 0.5;
        let mismatch = |lag: i64| -> f32 {
            (10_000..20_000)
                .map(|i: i64| (samples[2 * i as usize] - sine(i + lag)).powi(2))
                .sum()
        };
        let best = (-50..=50)
            .min_by(|a, b| mismatch(*a).total_cmp(&mismatch(*b)))
            .unwrap();
        assert_eq!(best, 0, "the decoded tone lags by {best} samples");
    }

    #[test]
    fn a_file_that_is_not_opus_is_an_error() {
        let path = std::env::temp_dir().join(format!("kp-not-audio-{}.ogg", std::process::id()));
        std::fs::write(&path, b"not audio").unwrap();
        let result = decode_audio(&path);
        let _ = std::fs::remove_file(&path);
        assert!(result.is_err());
    }
}
