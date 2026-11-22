/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface PlayerCommand {
	id: string;
	command: 'load' | 'play' | 'pause' | 'seek' | 'next' | 'previous' | 'stop' | 'volume' | 'pitch' | 'reload';
	item_id: string | null;
	/**
	 * Where and when, for play/seek.
	 */
	anchor: Anchor | null;
	/**
	 * Volume (0 to 2) or semitones.
	 */
	value: number | null;
	/**
	 * µs on the server's clock.
	 */
	issued_at: number;
}
/**
 * A song position that holds at an instant (µs on the server's clock) and moves at a rate.
 */
export interface Anchor {
	position: number;
	instant: number;
	rate: number;
}
