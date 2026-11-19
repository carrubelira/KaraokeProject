/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Playlist {
	id: string;
	name: string;
	version: number;
	items: PlaylistItem[];
	player_id: string | null;
}
export interface PlaylistItem {
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
