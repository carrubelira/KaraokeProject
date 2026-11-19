//! The video of the song on, decoded ahead on its own thread (one decoder for every screen).
//!
//! The screens ask for the frame to show at a song time; the feed keeps a few frames around it
//! and seeks when the song jumps (a seek, a new entry point) or when it falls behind.

use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

use kp_media::{VideoDecoder, VideoFrame};

const AHEAD: usize = 6;

struct Queue {
    frames: VecDeque<Arc<VideoFrame>>,
    /// Song time the screens want, as f64 bits (read by the decoder).
    seek_to: Option<f64>,
    ended: bool,
}

pub struct VideoFeed {
    queue: Arc<(Mutex<Queue>, Condvar)>,
    stop: Arc<AtomicBool>,
    wanted: Arc<AtomicU64>,
    /// Seconds between the video's own time and the song's (the track's offset).
    offset: f64,
    pub hardware: Option<&'static str>,
}

impl VideoFeed {
    pub fn open(path: PathBuf, offset: f64, max_height: u32) -> Result<Self, String> {
        let queue = Arc::new((
            Mutex::new(Queue {
                frames: VecDeque::new(),
                seek_to: None,
                ended: false,
            }),
            Condvar::new(),
        ));
        let stop = Arc::new(AtomicBool::new(false));
        let wanted = Arc::new(AtomicU64::new(0f64.to_bits()));
        let (q, s, w) = (queue.clone(), stop.clone(), wanted.clone());
        // ffmpeg's contexts stay on the thread that opened them.
        let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
        thread::Builder::new()
            .name("video".into())
            .spawn(move || match VideoDecoder::open(&path, max_height, true) {
                Ok(decoder) => {
                    let _ = ready_tx.send(Ok(decoder.hardware));
                    decode(decoder, q, s, w);
                }
                Err(error) => {
                    let _ = ready_tx.send(Err(error.to_string()));
                }
            })
            .map_err(|e| e.to_string())?;
        let hardware = ready_rx.recv().map_err(|e| e.to_string())??;
        Ok(Self {
            queue,
            stop,
            wanted,
            offset,
            hardware,
        })
    }

    /// The frame to show at song time `t`: the last one that starts at or before it.
    pub fn frame_at(&self, t: f64) -> Option<Arc<VideoFrame>> {
        let t = t - self.offset;
        self.wanted.store(t.to_bits(), Ordering::Relaxed);
        let (lock, wake) = &*self.queue;
        let mut queue = lock.lock().ok()?;
        while queue.frames.len() > 1 && queue.frames[1].time <= t {
            queue.frames.pop_front();
            wake.notify_one();
        }
        let first = queue.frames.front().cloned();
        let behind =
            first.as_ref().is_some_and(|f| t - f.time > 0.5) && queue.frames.len() <= 1 && !queue.ended;
        let jumped_back = first.as_ref().is_some_and(|f| f.time - t > 0.25);
        if (behind || jumped_back || (first.is_none() && !queue.ended))
            && queue.seek_to.is_none()
            && (behind || jumped_back)
        {
            queue.seek_to = Some(t);
            queue.frames.clear();
            wake.notify_one();
        }
        first.filter(|f| f.time <= t + 0.1)
    }
}

impl Drop for VideoFeed {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        self.queue.1.notify_all();
    }
}

fn decode(
    mut decoder: VideoDecoder,
    queue: Arc<(Mutex<Queue>, Condvar)>,
    stop: Arc<AtomicBool>,
    wanted: Arc<AtomicU64>,
) {
    let (lock, wake) = &*queue;
    while !stop.load(Ordering::Relaxed) {
        let seek = {
            let Ok(mut q) = lock.lock() else { return };
            while q.frames.len() >= AHEAD && q.seek_to.is_none() && !stop.load(Ordering::Relaxed) {
                q = match wake.wait(q) {
                    Ok(q) => q,
                    Err(_) => return,
                };
            }
            q.seek_to.take()
        };
        if let Some(t) = seek {
            if decoder.seek(t).is_err() {
                log::warn!("video seek to {t:.2} failed");
            }
            // Decode up to the wanted time without queueing what is already past.
            let target = f64::from_bits(wanted.load(Ordering::Relaxed)).max(t);
            loop {
                match decoder.next_frame() {
                    Ok(Some(frame)) if frame.time + 0.05 < target => continue,
                    Ok(Some(frame)) => {
                        if let Ok(mut q) = lock.lock() {
                            q.frames.push_back(Arc::new(frame));
                            q.ended = false;
                        }
                        break;
                    }
                    _ => break,
                }
            }
            continue;
        }
        match decoder.next_frame() {
            Ok(Some(frame)) => {
                if let Ok(mut q) = lock.lock() {
                    q.frames.push_back(Arc::new(frame));
                }
            }
            Ok(None) => {
                if let Ok(mut q) = lock.lock() {
                    q.ended = true;
                    // Wait for a seek (a replay) or the end.
                    while q.seek_to.is_none() && !stop.load(Ordering::Relaxed) {
                        q = match wake.wait(q) {
                            Ok(q) => q,
                            Err(_) => return,
                        };
                    }
                }
            }
            Err(error) => {
                log::warn!("video decoding stopped: {error}");
                return;
            }
        }
    }
}
