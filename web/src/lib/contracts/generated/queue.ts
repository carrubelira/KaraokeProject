/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * What the stage will play, in order: one per backend, with an optimistic version.
 */
export interface Queue {
	version: number;
	items: QueueItem[];
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
