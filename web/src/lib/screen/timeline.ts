/**
 * Where the song is, from the session's anchor (decision 011): `position + rate × elapsed`,
 * held between 0 and the song's exit point. Pure, so the frame loop, the tests and the console
 * all read the same thing.
 */
import type { Anchor, Program } from '#lib/contracts';

/** Seconds into the song at server instant `server` (µs). */
export function positionAt(anchor: Anchor, server: number, end = Infinity): number {
	const elapsed = Math.max(0, server - anchor.instant) / 1e6;
	return Math.min(end, Math.max(0, anchor.position + anchor.rate * elapsed));
}

/** Whether the song moves at server instant `server` (the anchor is in effect and playing). */
export function movingAt(anchor: Anchor, server: number): boolean {
	return anchor.rate > 0 && server >= anchor.instant;
}

/** The song's exit point, or its end. */
export function endOf(program: Program): number {
	const end = program.item.end;
	return end === null ? program.duration : Math.min(end, program.duration);
}

/**
 * Whether `next` carries on from `previous` without a jump: a start, a pause or the end, where
 * the picture only has to start or stop, not look for another frame.
 */
export function continuous(previous: Anchor, next: Anchor, tolerance = 0.05): boolean {
	return Math.abs(positionAt(previous, next.instant) - next.position) <= tolerance;
}
