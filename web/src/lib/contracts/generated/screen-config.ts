/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * What the operator sets for one screen, kept by its id.
 */
export interface ScreenConfig {
	name: string | null;
	layout: 'video-lyrics' | 'lyrics' | 'video' | 'off';
	theme: string;
	/**
	 * How late the picture really is (the TV's processing).
	 */
	display_ms: number;
	/**
	 * Never download a taller video than this (a Raspberry Pi).
	 */
	video_max_height: number | null;
}
