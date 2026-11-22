//! Where and when every lyrics row shows, for any screen size.
//!
//! A port of `packages/engine/src/karaoke_engine/subtitles/layout.py` (the reference, also run
//! by the web in `web/src/lib/lyrics/layout.ts`). The shared cases in `fixtures/lyrics-layout/`
//! keep the three identical to 1e-6 px, so a song breaks its lines and takes turns on the TV
//! exactly as in the browser and in the video. Any change goes to all three, in the same order
//! of floating-point operations.

use std::collections::HashMap;

use kp_proto::{Line, Role, Singer};
use serde::{Deserialize, Serialize};

pub mod scene;
pub mod theme;
pub use theme::{FontMetrics, Theme};

const BREAK_AFTER: &str = ",.;:!?…»)";
const PUNCTUATION_BONUS: f64 = 0.9;
const MIN_SCALE: f64 = 0.6;
const MAX_FALLBACK_ROWS: usize = 4;
const BACKING_ATTACH: f64 = 1.5;
const MIN_LEAD: f64 = 0.5;
const SCROLL_GAP: f64 = 0.35;
const SCROLL_SETTLE: f64 = 0.25;

fn scroll_anchor(position: &str) -> f64 {
    match position {
        "top" => 0.30,
        "center" => 0.42,
        _ => 0.62,
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PartSpan {
    pub text: String,
    pub start: f64,
    pub end: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RowWord {
    pub parts: Vec<PartSpan>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Row {
    pub line_id: String,
    pub role: Role,
    pub singer: Option<String>,
    pub color: String,
    pub words: Vec<RowWord>,
    pub text: String,
    pub scale: f64,
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Group {
    pub index: usize,
    pub block: usize,
    pub slot: usize,
    pub start: f64,
    pub end: f64,
    pub show: f64,
    pub hide: f64,
    pub rows: Vec<Row>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Dot {
    pub x: f64,
    pub y: f64,
    pub r: f64,
    pub off: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Countdown {
    pub block: usize,
    pub start: f64,
    pub end: f64,
    pub dots: Vec<Dot>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BreakBar {
    pub start: f64,
    pub end: f64,
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ScrollPlan {
    pub offsets: Vec<f64>,
    pub switches: Vec<f64>,
    pub transition: f64,
    pub visible: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    Pages,
    Scroll,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Layout {
    pub width: f64,
    pub height: f64,
    pub font_px: f64,
    pub mode: Mode,
    pub groups: Vec<Group>,
    pub countdowns: Vec<Countdown>,
    pub bars: Vec<BreakBar>,
    pub scroll: Option<ScrollPlan>,
}

fn join(words: &[String]) -> String {
    words.join(" ")
}

/// Rows (word indices) for a line, and how much to shrink it so the widest row fits.
pub fn wrap(
    words: &[String],
    px: f64,
    max_width: f64,
    max_rows: usize,
    metrics: &FontMetrics,
) -> (Vec<Vec<usize>>, f64) {
    let full = metrics.width(&join(words), px);
    let all: Vec<usize> = (0..words.len()).collect();
    if full <= max_width {
        return (vec![all], 1.0);
    }
    if max_rows < 2 || words.len() < 2 {
        if full * MIN_SCALE > max_width && words.len() >= 2 {
            return wrap_more(words, px, max_width, metrics, 2);
        }
        return (vec![all], fit(max_width, full));
    }
    let mut best = 1;
    let mut best_cost = 0.0;
    let mut best_widest = 0.0;
    for i in 1..words.len() {
        let widest = metrics
            .width(&join(&words[..i]), px)
            .max(metrics.width(&join(&words[i..]), px));
        let ends_with_break = words[i - 1]
            .chars()
            .last()
            .is_some_and(|c| BREAK_AFTER.contains(c));
        let cost = if ends_with_break {
            widest * PUNCTUATION_BONUS
        } else {
            widest
        };
        if i == 1 || cost < best_cost {
            best = i;
            best_cost = cost;
            best_widest = widest;
        }
    }
    let rows = vec![(0..best).collect(), (best..words.len()).collect()];
    if best_widest <= max_width {
        return (rows, 1.0);
    }
    if best_widest * MIN_SCALE > max_width && words.len() >= 3 {
        return wrap_more(words, px, max_width, metrics, 3);
    }
    (rows, fit(max_width, best_widest))
}

fn fit(max_width: f64, widest: f64) -> f64 {
    if widest * MIN_SCALE <= max_width {
        MIN_SCALE.max(max_width / widest)
    } else {
        max_width / widest
    }
}

fn wrap_more(
    words: &[String],
    px: f64,
    max_width: f64,
    metrics: &FontMetrics,
    first: usize,
) -> (Vec<Vec<usize>>, f64) {
    let n = words.len();
    let mut width = vec![vec![0.0; n + 1]; n + 1];
    for i in 0..n {
        for j in i + 1..=n {
            width[i][j] = metrics.width(&join(&words[i..j]), px);
        }
    }
    let mut rows = Vec::new();
    let mut widest = 0.0;
    for count in first..=MAX_FALLBACK_ROWS.min(n) {
        let (r, w) = balanced(&width, n, count);
        rows = r;
        widest = w;
        if widest * MIN_SCALE <= max_width {
            break;
        }
    }
    (
        rows,
        if widest <= max_width {
            1.0
        } else {
            fit(max_width, widest)
        },
    )
}

fn balanced(width: &[Vec<f64>], n: usize, count: usize) -> (Vec<Vec<usize>>, f64) {
    let mut best = vec![vec![f64::INFINITY; n + 1]; count + 1];
    let mut cut = vec![vec![0usize; n + 1]; count + 1];
    best[0][0] = 0.0;
    for r in 1..=count {
        for j in r..=n {
            for i in r - 1..j {
                let candidate = best[r - 1][i].max(width[i][j]);
                if candidate < best[r][j] {
                    best[r][j] = candidate;
                    cut[r][j] = i;
                }
            }
        }
    }
    let mut rows = Vec::new();
    let mut end = n;
    for r in (1..=count).rev() {
        let start = cut[r][end];
        rows.insert(0, (start..end).collect());
        end = start;
    }
    (rows, best[count][n])
}

fn display_words(line: &Line, brackets: bool) -> Vec<RowWord> {
    let mut words: Vec<RowWord> = line
        .words
        .iter()
        .map(|word| {
            let parts: Vec<PartSpan> = word
                .parts
                .iter()
                .map(|p| PartSpan {
                    text: p.text.clone(),
                    start: p.start,
                    end: p.end,
                })
                .collect();
            RowWord {
                parts: if parts.is_empty() {
                    vec![PartSpan {
                        text: word.text.clone(),
                        start: word.start,
                        end: word.end,
                    }]
                } else {
                    parts
                },
            }
        })
        .collect();
    if brackets && !words.is_empty() {
        let first = &mut words[0].parts[0];
        first.text = format!("[{}", first.text);
        let last = words
            .last_mut()
            .expect("not empty")
            .parts
            .last_mut()
            .expect("a word has a part");
        last.text.push(']');
    }
    words
}

fn sort_by_start(lines: &mut [&Line]) {
    lines.sort_by(|a, b| a.start.total_cmp(&b.start));
}

fn groups(lines: &[Line]) -> Vec<Vec<Line>> {
    let mut leads: Vec<&Line> = lines.iter().filter(|l| l.role == Role::Lead).collect();
    sort_by_start(&mut leads);
    let mut attached: Vec<Vec<&Line>> = vec![Vec::new(); leads.len()];
    let mut alone: Vec<&Line> = Vec::new();
    for line in lines.iter().filter(|l| l.role == Role::Backing) {
        let mut target: i64 = -1;
        let mut best = 0.0;
        for (i, lead) in leads.iter().enumerate() {
            let overlap = line.end.min(lead.end) - line.start.max(lead.start);
            if overlap > best {
                target = i as i64;
                best = overlap;
            }
        }
        if target < 0 {
            let mut previous: i64 = -1;
            for (i, lead) in leads.iter().enumerate() {
                if lead.end <= line.start && (previous < 0 || lead.end >= leads[previous as usize].end) {
                    previous = i as i64;
                }
            }
            if previous >= 0 && line.start - leads[previous as usize].end < BACKING_ATTACH {
                target = previous;
            }
        }
        if target >= 0 {
            attached[target as usize].push(line);
        } else {
            alone.push(line);
        }
    }
    let mut out: Vec<Vec<Line>> = leads
        .iter()
        .zip(attached)
        .map(|(lead, mut extra)| {
            sort_by_start(&mut extra);
            std::iter::once(*lead).chain(extra).cloned().collect()
        })
        .collect();
    out.extend(alone.into_iter().map(|line| vec![line.clone()]));
    out.sort_by(|a, b| group_start(a).total_cmp(&group_start(b)));
    out
}

fn group_start(lines: &[Line]) -> f64 {
    lines.iter().map(|l| l.start).fold(f64::INFINITY, f64::min)
}

fn group_end(lines: &[Line]) -> f64 {
    lines.iter().map(|l| l.end).fold(f64::NEG_INFINITY, f64::max)
}

fn colors(singers: &[Singer], theme: &Theme) -> HashMap<Option<String>, String> {
    let mut colors = HashMap::new();
    colors.insert(None, theme.colors.sung.clone());
    let palette = &theme.colors.singers;
    for (i, singer) in singers.iter().enumerate() {
        let color = match &singer.color {
            Some(color) => color.clone(),
            None if singers.len() >= 2 && !palette.is_empty() => palette[i % palette.len()].clone(),
            None => theme.colors.sung.clone(),
        };
        colors.insert(Some(singer.id.clone()), color);
    }
    colors
}

fn rows(
    lines: &[Line],
    theme: &Theme,
    font_px: f64,
    usable: f64,
    metrics: &FontMetrics,
    colors: &HashMap<Option<String>, String>,
) -> Vec<Row> {
    let mut rows = Vec::new();
    let mut top = 0.0;
    for line in lines {
        let backing = line.role == Role::Backing;
        let role_scale = if backing { theme.backing.scale } else { 1.0 };
        let words = display_words(line, backing && theme.backing.brackets);
        let texts: Vec<String> = words
            .iter()
            .map(|w| w.parts.iter().map(|p| p.text.as_str()).collect())
            .collect();
        let (indices, wrap_scale) = wrap(
            &texts,
            font_px * role_scale,
            usable,
            theme.layout.max_rows,
            metrics,
        );
        let scale = role_scale * wrap_scale;
        let row_px = font_px * scale;
        let height = row_px * theme.layout.line_spacing;
        for row_words in indices {
            let text = row_words
                .iter()
                .map(|&i| texts[i].as_str())
                .collect::<Vec<_>>()
                .join(" ");
            rows.push(Row {
                line_id: line.id.clone(),
                role: line.role,
                singer: line.singer.clone(),
                color: colors
                    .get(&line.singer)
                    .cloned()
                    .unwrap_or_else(|| theme.colors.sung.clone()),
                words: row_words.iter().map(|&i| words[i].clone()).collect(),
                width: metrics.width(&text, row_px),
                text,
                scale,
                x: 0.0,
                y: top + height / 2.0,
                height,
            });
            top += height;
        }
    }
    rows
}

fn total_height(rows: &[Row]) -> f64 {
    let mut total = 0.0;
    for row in rows {
        total += row.height;
    }
    total
}

fn countdown(
    block: usize,
    row: &Row,
    y_offset: f64,
    start: f64,
    end: f64,
    font_px: f64,
    theme: &Theme,
) -> Countdown {
    let anim = &theme.animation;
    let left = row.x - row.width / 2.0;
    let y = row.y + y_offset - row.height / 2.0 - 0.45 * font_px;
    let dots = (0..anim.countdown_dots)
        .map(|j| Dot {
            x: left + 0.2 * font_px + j as f64 * 0.55 * font_px,
            y,
            r: 0.14 * font_px,
            off: end - j as f64 * anim.countdown_step,
        })
        .collect();
    Countdown {
        block,
        start,
        end,
        dots,
    }
}

fn ease(u: f64) -> f64 {
    let v = 1.0 - u;
    1.0 - v * v * v
}

fn scroll_step(plan: &ScrollPlan, t: f64) -> (usize, f64) {
    let k = plan.switches.partition_point(|&s| s <= t);
    if k == 0 {
        return (0, 1.0);
    }
    if plan.transition <= 0.0 {
        return (k, 1.0);
    }
    let u = (t - plan.switches[k - 1]) / plan.transition;
    (k, if u < 1.0 { ease(u) } else { 1.0 })
}

/// Which group is on the anchor at `t`, with the fraction of a move in progress.
pub fn scroll_focus(plan: &ScrollPlan, t: f64) -> f64 {
    let (k, done) = scroll_step(plan, t);
    if k > 0 { k as f64 - 1.0 + done } else { 0.0 }
}

/// How far down the list is drawn at `t`, in px.
pub fn scroll_offset(plan: &ScrollPlan, t: f64) -> f64 {
    let (k, done) = scroll_step(plan, t);
    if k == 0 {
        return plan.offsets[0];
    }
    plan.offsets[k - 1] + (plan.offsets[k] - plan.offsets[k - 1]) * done
}

/// Opacity of a group `rank` places after the one on the anchor (negative: already sung).
pub fn scroll_opacity(rank: f64, visible: usize) -> f64 {
    let visible = visible as f64;
    if rank < 0.0 {
        return (1.0 + 0.6 * rank).max(0.0);
    }
    if rank <= visible - 1.0 {
        return 1.0 - 0.12 * rank;
    }
    ((1.0 - 0.12 * (visible - 1.0)) * (visible - rank)).max(0.0)
}

#[allow(clippy::too_many_arguments)]
fn scroll_layout(
    theme: &Theme,
    width: f64,
    height: f64,
    font_px: f64,
    rows_by_group: &[Vec<Row>],
    starts: &[f64],
    ends: &[f64],
    blocks: &[Vec<usize>],
) -> Layout {
    let anim = &theme.animation;
    let visible = theme.layout.visible_lines;
    let anchor = scroll_anchor(&theme.layout.position) * height;
    let n = rows_by_group.len();
    let mut tops = Vec::with_capacity(n);
    let mut top = 0.0;
    for rows in rows_by_group {
        tops.push(top);
        top += total_height(rows) + SCROLL_GAP * font_px;
    }
    let offsets: Vec<f64> = (0..n)
        .map(|k| anchor - (tops[k] + total_height(&rows_by_group[k]) / 2.0))
        .collect();
    let mut switches: Vec<f64> = Vec::new();
    for k in 1..n {
        let mut switch = (ends[k - 1] + anim.hold).min(starts[k] - anim.transition - SCROLL_SETTLE);
        if let Some(&last) = switches.last() {
            switch = switch.max(last + anim.transition);
        }
        switches.push(switch);
    }
    let plan = ScrollPlan {
        offsets: offsets.clone(),
        switches: switches.clone(),
        transition: anim.transition,
        visible,
    };
    let last_hide = if ends.is_empty() {
        0.0
    } else {
        ends.iter().copied().fold(f64::NEG_INFINITY, f64::max) + 2.0 * anim.hold
    };
    let mut block_of = vec![0; n];
    for (b, members) in blocks.iter().enumerate() {
        for &k in members {
            block_of[k] = b;
        }
    }
    let first_show = if starts.is_empty() {
        0.0
    } else {
        (starts[0] - anim.lead_in).max(0.0)
    };
    let mut groups = Vec::with_capacity(n);
    for (k, rows) in rows_by_group.iter().enumerate() {
        let show = if k >= visible {
            switches[k - visible]
        } else {
            first_show
        };
        let hide = if k + 1 < switches.len() {
            switches[k + 1] + anim.transition
        } else {
            last_hide
        };
        let placed = rows
            .iter()
            .map(|row| Row {
                x: width / 2.0,
                y: tops[k] + row.y,
                ..row.clone()
            })
            .collect();
        groups.push(Group {
            index: k,
            block: block_of[k],
            slot: 0,
            start: starts[k],
            end: ends[k],
            show,
            hide,
            rows: placed,
        });
    }
    let mut countdowns = Vec::new();
    let mut previous_end = 0.0;
    for (b, members) in blocks.iter().enumerate() {
        let first = members[0];
        let gap_before = if b > 0 {
            starts[first] - previous_end
        } else {
            starts[first]
        };
        if anim.countdown_min_gap > 0.0 && anim.countdown_dots > 0 && gap_before >= anim.countdown_min_gap {
            let start =
                (starts[first] - anim.countdown_dots as f64 * anim.countdown_step).max(groups[first].show);
            countdowns.push(countdown(
                b,
                &groups[first].rows[0],
                offsets[first],
                start,
                starts[first],
                font_px,
                theme,
            ));
        }
        previous_end = members.iter().map(|&k| ends[k]).fold(f64::NEG_INFINITY, f64::max);
    }
    Layout {
        width,
        height,
        font_px,
        mode: Mode::Scroll,
        groups,
        countdowns,
        bars: Vec::new(),
        scroll: Some(plan),
    }
}

/// The layout of a song's lyrics on a `width` × `height` screen.
pub fn build_layout(
    lines: &[Line],
    singers: &[Singer],
    theme: &Theme,
    width: f64,
    height: f64,
    metrics: &FontMetrics,
) -> Layout {
    let margin_x = theme.layout.margin * width;
    let margin_y = theme.layout.margin * height;
    let usable = width - 2.0 * margin_x;
    let font_px = (theme.layout.font_size * height)
        .min(usable / (theme.layout.min_row_chars as f64 * metrics.average_lowercase / metrics.upem));
    let colors = colors(singers, theme);
    let anim = &theme.animation;
    let slots = theme.layout.visible_lines;

    let lines_by_group = groups(lines);
    let starts: Vec<f64> = lines_by_group.iter().map(|g| group_start(g)).collect();
    let ends: Vec<f64> = lines_by_group.iter().map(|g| group_end(g)).collect();
    let mut rows_by_group: Vec<Vec<Row>> = lines_by_group
        .iter()
        .map(|g| rows(g, theme, font_px, usable, metrics, &colors))
        .collect();

    let mut blocks: Vec<Vec<usize>> = Vec::new();
    let mut latest_end = 0.0;
    for k in 0..lines_by_group.len() {
        let gap = starts[k] - latest_end;
        if k == 0 || (anim.countdown_min_gap > 0.0 && gap >= anim.countdown_min_gap) {
            blocks.push(Vec::new());
        }
        blocks.last_mut().expect("pushed above").push(k);
        latest_end = if k == 0 {
            ends[k]
        } else {
            f64::max(latest_end, ends[k])
        };
    }

    if theme.layout.mode == "scroll" {
        return scroll_layout(
            theme,
            width,
            height,
            font_px,
            &rows_by_group,
            &starts,
            &ends,
            &blocks,
        );
    }

    let n = lines_by_group.len();
    let mut show = vec![0.0; n];
    let mut hide = vec![0.0; n];
    let mut slot_of = vec![0; n];
    let mut block_of = vec![0; n];
    let mut countdowns = Vec::new();
    let mut bars = Vec::new();
    let mut previous_hide = 0.0;
    let mut previous_end = 0.0;
    for (b, members) in blocks.iter().enumerate() {
        let first = members[0];
        let block_start = starts[first];
        let block_end = members.iter().map(|&k| ends[k]).fold(f64::NEG_INFINITY, f64::max);
        let block_show = (block_start - anim.lead_in).max(previous_hide).max(0.0);
        let block_hide = if b + 1 < blocks.len() {
            (block_end + 2.0 * anim.hold).min(starts[blocks[b + 1][0]])
        } else {
            block_end + 2.0 * anim.hold
        };
        for (j, &k) in members.iter().enumerate() {
            slot_of[k] = j % slots;
            block_of[k] = b;
            show[k] = if j < slots {
                block_show
            } else {
                hide[members[j - slots]]
            };
            if j + slots < members.len() {
                let later = starts[members[j + slots]];
                let ready = (later - MIN_LEAD).max(ends[k]);
                hide[k] = show[k].max((ends[k] + anim.hold).min(ready));
            } else {
                hide[k] = block_hide;
            }
        }
        let mut bands = vec![0.0; slots];
        for &k in members {
            bands[slot_of[k]] = f64::max(bands[slot_of[k]], total_height(&rows_by_group[k]));
        }
        let mut total = 0.0;
        for band in &bands {
            total += band;
        }
        let mut top = match theme.layout.position.as_str() {
            "bottom" => height - margin_y - total,
            "top" => margin_y,
            _ => height / 2.0 - total / 2.0,
        };
        let mut band_tops = Vec::with_capacity(slots);
        for band in &bands {
            band_tops.push(top);
            top += band;
        }
        for &k in members {
            let slot = slot_of[k];
            let group_height = total_height(&rows_by_group[k]);
            let offset = if slots == 1 || (slots % 2 == 1 && slot == slots / 2) {
                band_tops[slot] + (bands[slot] - group_height) / 2.0
            } else if (slot as f64) < slots as f64 / 2.0 {
                band_tops[slot] + bands[slot] - group_height
            } else {
                band_tops[slot]
            };
            for row in &mut rows_by_group[k] {
                row.x = width / 2.0;
                row.y += offset;
            }
        }
        let gap_before = if b > 0 {
            block_start - previous_end
        } else {
            block_start
        };
        if anim.countdown_min_gap > 0.0 && anim.countdown_dots > 0 && gap_before >= anim.countdown_min_gap {
            let start = (block_start - anim.countdown_dots as f64 * anim.countdown_step).max(block_show);
            countdowns.push(countdown(
                b,
                &rows_by_group[first][0],
                0.0,
                start,
                block_start,
                font_px,
                theme,
            ));
        }
        if anim.break_bar_min > 0.0 && block_show - previous_hide >= anim.break_bar_min {
            bars.push(BreakBar {
                start: previous_hide,
                end: block_show,
                x: width / 2.0,
                y: band_tops[0] + total / 2.0,
                width: 0.3 * usable,
                height: 0.08 * font_px,
            });
        }
        previous_hide = block_hide;
        previous_end = block_end;
    }
    let groups = rows_by_group
        .into_iter()
        .enumerate()
        .map(|(k, rows)| Group {
            index: k,
            block: block_of[k],
            slot: slot_of[k],
            start: starts[k],
            end: ends[k],
            show: show[k],
            hide: hide[k],
            rows,
        })
        .collect();
    Layout {
        width,
        height,
        font_px,
        mode: Mode::Pages,
        groups,
        countdowns,
        bars,
        scroll: None,
    }
}
