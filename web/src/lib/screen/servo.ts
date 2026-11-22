/**
 * How a `<video>` is kept on the timeline (decision 011).
 *
 * The browser decodes and shows the video on its own clock; what can be steered is its speed.
 * `error` is the media time of the frame about to be shown minus where the timeline will be when
 * it is shown, in seconds (positive: the picture is ahead).
 *
 * - Inside `DEADBAND` (half a frame at 60 fps) it plays at speed 1: chasing noise would wobble.
 * - Up to `HARD` it changes speed by at most `MAX_TRIM` (3 %, invisible on a muted video) to
 *   close the gap in about `CLOSE_IN` seconds.
 * - Beyond, it jumps: to where the timeline will be once the jump is done, aiming ahead by as
 *   long as the last jump took.
 */

export const DEADBAND = 0.008;
export const HARD = 0.15;
export const MAX_TRIM = 0.03;
const CLOSE_IN = 1.5;

export type Steer = { kind: 'rate'; rate: number } | { kind: 'seek'; ahead: number };

export function steer(error: number, seekLag: number): Steer {
	if (!Number.isFinite(error) || Math.abs(error) > HARD) return { kind: 'seek', ahead: seekLag };
	if (Math.abs(error) < DEADBAND) return { kind: 'rate', rate: 1 };
	const trim = Math.max(-MAX_TRIM, Math.min(MAX_TRIM, error / CLOSE_IN));
	return { kind: 'rate', rate: 1 - trim };
}

/** Learns how long a jump takes, for the next one to aim ahead by that much. */
export function learnLag(previous: number, measured: number): number {
	const clamped = Math.max(0, Math.min(1, measured));
	return previous === 0 ? clamped : 0.7 * previous + 0.3 * clamped;
}

/**
 * What the frame loop asks once per presented frame. A frame's media time is its start, so the
 * raw error saws by a whole frame as frames go by; it is measured from the frame's middle and
 * smoothed over about half a second before it steers. A big error jumps at once.
 */
export class VideoFollower {
	#filtered = 0;
	#primed = false;
	/** How long the last jumps took, in seconds: the next one aims ahead by that much. */
	seekLag = 0.08;

	/** `mediaTime` of the frame about to show, its length, and the timeline when it shows. */
	frame(mediaTime: number, span: number, target: number): Steer {
		const raw = mediaTime + span / 2 - target;
		if (Math.abs(raw) > HARD) return { kind: 'seek', ahead: this.seekLag };
		this.#filtered = this.#primed ? this.#filtered + 0.15 * (raw - this.#filtered) : raw;
		this.#primed = true;
		return steer(this.#filtered, this.seekLag);
	}

	/** A jump finished after `took` seconds. */
	seeked(took: number): void {
		this.seekLag = learnLag(this.seekLag, took);
		this.#primed = false;
	}
}

/** The 95th percentile of the absolute errors, in ms (what the screen reports). */
export function p95Ms(errors: readonly number[]): number | null {
	if (!errors.length) return null;
	const sorted = errors.map((e) => Math.abs(e) * 1000).sort((a, b) => a - b);
	return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))];
}
