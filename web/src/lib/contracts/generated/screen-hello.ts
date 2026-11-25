/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * The first thing a screen says: who it is and what it can show.
 */
export interface ScreenHello {
	screen_id: string;
	/**
	 * The browser's user agent.
	 */
	agent: string;
	width: number;
	height: number;
	refresh_hz: number | null;
	codecs: ('h264' | 'hevc' | 'av1')[];
	/**
	 * The console's monitor: shown, never waited for.
	 */
	preview: boolean;
}
