//! This process's monotonic clock, in microseconds since it started.

use std::sync::OnceLock;
use std::time::Instant;

fn origin() -> Instant {
    static ORIGIN: OnceLock<Instant> = OnceLock::new();
    *ORIGIN.get_or_init(Instant::now)
}

pub fn now_us() -> i64 {
    origin().elapsed().as_micros() as i64
}
