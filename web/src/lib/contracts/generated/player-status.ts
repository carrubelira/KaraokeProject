/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * What a player reports every second and on every change.
 */
export interface PlayerStatus {
	outputs: PlayerOutputs;
	cache: ContentCache[];
	item_id: string | null;
	position: number | null;
	state: 'idle' | 'loading' | 'playing' | 'paused' | 'waiting';
	semitones: number;
	volume: number;
	/**
	 * Diagnostics: measured drift (ppm) and offsets (ms).
	 */
	sync: {
		[k: string]: number;
	};
}
export interface PlayerOutputs {
	displays: Display[];
	audio: AudioDevice[];
}
export interface Display {
	/**
	 * Stable across reboots (EDID serial or OS id).
	 */
	id: string;
	name: string;
	width: number;
	height: number;
	refresh_hz: number;
	primary: boolean;
	connected: boolean;
}
export interface AudioDevice {
	/**
	 * Stable across reboots.
	 */
	id: string;
	name: string;
	channels: number;
	sample_rate: number;
	latency_ms: number | null;
	default: boolean;
	connected: boolean;
	bluetooth: boolean;
}
export interface ContentCache {
	content_id: string;
	manifest: string;
	state: 'absent' | 'downloading' | 'verifying' | 'ready' | 'failed';
	fraction: number;
	error: string | null;
}
