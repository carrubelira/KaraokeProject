/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Session {
	/**
	 * Goes up on every change.
	 */
	version: number;
	/**
	 * Goes up on every cue; `ready` reports name the epoch they are for.
	 */
	epoch: number;
	state: 'idle' | 'cueing' | 'cued' | 'playing' | 'paused' | 'ended' | 'fault';
	current: Program | null;
	/**
	 * Where the song is, and when.
	 */
	anchor: Anchor | null;
	/**
	 * The next items, to download and get ready ahead.
	 */
	upcoming: Program[];
	semitones: number;
	volume: number;
}
/**
 * A queue item with the manifest it plays: what screens and audio prepare.
 */
export interface Program {
	item: QueueItem;
	manifest: string;
	duration: number;
}
export interface QueueItem {
	id: string;
	content_id: string;
	/**
	 * Pinned version; None = latest.
	 */
	manifest: string | null;
	/**
	 * Entry point.
	 */
	start: number | null;
	/**
	 * Exit point.
	 */
	end: number | null;
	semitones: number;
	singer: string | null;
}
/**
 * A song position that holds at an instant (µs on the server's monotonic clock) and moves
 * at a rate (0 paused, 1 playing).
 */
export interface Anchor {
	position: number;
	instant: number;
	rate: number;
}
