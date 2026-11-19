//! What is on screen at a song time (port of `web/src/lib/lyrics/scene.ts` and `fill.ts`).
//!
//! Pure functions of the time: seeking or pausing shows the right state at once, and every
//! screen evaluates them with the master clock on each frame.

use crate::{BreakBar, Dot, Layout, Row, scroll_focus, scroll_offset, scroll_opacity};

/// Between `t0` and `t1` the fill edge moves from `x0` to `x1` (px from the row's left edge).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct FillSegment {
    pub t0: f64,
    pub t1: f64,
    pub x0: f64,
    pub x1: f64,
}

/// Where a part of the row is drawn (px from the row's left edge), as the renderer measured it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PartBox {
    pub x0: f64,
    pub x1: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Fill {
    /// Each syllable fills across its width while it is sung (ASS `\kf`).
    Wipe,
    /// Each word fills at once when it starts (ASS `\k`).
    Word,
}

pub fn fill_segments(row: &Row, boxes: &[PartBox], mode: Fill) -> Vec<FillSegment> {
    let parts: usize = row.words.iter().map(|w| w.parts.len()).sum();
    assert_eq!(boxes.len(), parts, "row {}: one box per part", row.line_id);
    let mut segments = Vec::with_capacity(parts);
    let mut next = 0;
    for word in &row.words {
        let first = boxes[next];
        let last = boxes[next + word.parts.len() - 1];
        match mode {
            Fill::Word => {
                let t = word.parts[0].start;
                segments.push(FillSegment {
                    t0: t,
                    t1: t,
                    x0: first.x0,
                    x1: last.x1,
                });
            }
            Fill::Wipe => {
                for (i, part) in word.parts.iter().enumerate() {
                    let b = boxes[next + i];
                    segments.push(FillSegment {
                        t0: part.start,
                        t1: part.end,
                        x0: b.x0,
                        x1: b.x1,
                    });
                }
            }
        }
        next += word.parts.len();
    }
    segments
}

/// The fill edge at `t`: 0 before anything is sung, then always moving right.
pub fn fill_x(segments: &[FillSegment], t: f64) -> f64 {
    let mut x = 0.0;
    for s in segments {
        if t >= s.t1 {
            x = s.x1;
        } else if t > s.t0 {
            return s.x0 + (s.x1 - s.x0) * (t - s.t0) / (s.t1 - s.t0);
        } else {
            return x;
        }
    }
    x
}

#[derive(Clone, Debug, PartialEq)]
pub struct SceneState {
    /// Groups on screen and their opacity.
    pub groups: Vec<(usize, f64)>,
    pub dots: Vec<Dot>,
    pub bar: Option<(BreakBar, f64)>,
    /// Scroll mode: how far down the list is drawn (px); 0 in pages mode.
    pub offset: f64,
}

/// What is on screen at song time `t` (already including the theme's anticipation).
pub fn scene_at(layout: &Layout, t: f64, transition: f64) -> SceneState {
    let mut groups = Vec::new();
    let plan = layout.scroll.as_ref();
    let focus = plan.map_or(0.0, |p| scroll_focus(p, t));
    for g in &layout.groups {
        if t < g.show || t >= g.hide {
            continue;
        }
        let opacity = match plan {
            Some(plan) => scroll_opacity(g.index as f64 - focus, plan.visible),
            None => {
                let fade = transition.min((g.hide - g.show) / 2.0);
                if fade > 0.0 {
                    1f64.min((t - g.show) / fade).min((g.hide - t) / fade)
                } else {
                    1.0
                }
            }
        };
        groups.push((g.index, opacity));
    }
    let mut dots = Vec::new();
    for c in &layout.countdowns {
        if t < c.start || t >= c.end {
            continue;
        }
        dots.extend(c.dots.iter().filter(|d| t < d.off).cloned());
    }
    let mut bar = None;
    for b in &layout.bars {
        if t >= b.start && t < b.end {
            bar = Some((b.clone(), (t - b.start) / (b.end - b.start)));
        }
    }
    SceneState {
        groups,
        dots,
        bar,
        offset: plan.map_or(0.0, |p| scroll_offset(p, t)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{PartSpan, RowWord};
    use kp_proto::Role;

    fn row() -> Row {
        let part = |text: &str, start: f64, end: f64| PartSpan {
            text: text.into(),
            start,
            end,
        };
        Row {
            line_id: "l".into(),
            role: Role::Lead,
            singer: None,
            color: "#fff".into(),
            words: vec![
                RowWord {
                    parts: vec![part("O", 1.0, 1.5), part("la", 1.5, 2.0)],
                },
                RowWord {
                    parts: vec![part("mar", 3.0, 4.0)],
                },
            ],
            text: "Ola mar".into(),
            scale: 1.0,
            x: 0.0,
            y: 0.0,
            width: 100.0,
            height: 10.0,
        }
    }

    #[test]
    fn wipe_moves_across_each_syllable_and_word_jumps() {
        let boxes = [
            PartBox { x0: 0.0, x1: 10.0 },
            PartBox { x0: 10.0, x1: 30.0 },
            PartBox { x0: 40.0, x1: 70.0 },
        ];
        let wipe = fill_segments(&row(), &boxes, Fill::Wipe);
        assert_eq!(fill_x(&wipe, 0.5), 0.0);
        assert_eq!(fill_x(&wipe, 1.25), 5.0);
        assert_eq!(fill_x(&wipe, 2.5), 30.0);
        assert_eq!(fill_x(&wipe, 3.5), 55.0);
        assert_eq!(fill_x(&wipe, 9.0), 70.0);
        let word = fill_segments(&row(), &boxes, Fill::Word);
        assert_eq!(fill_x(&word, 1.2), 30.0);
        assert_eq!(fill_x(&word, 3.0), 70.0);
    }
}
