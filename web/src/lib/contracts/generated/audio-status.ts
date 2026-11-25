/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * What `kp-audio` reports every second and on every change.
 */
export interface AudioStatus {
	state: 'idle' | 'loading' | 'ready' | 'playing' | 'paused';
	epoch: number | null;
	/**
	 * The cued song is decoded and primed.
	 */
	ready: boolean;
	item_id: string | null;
	position: number | null;
	errors: AudioError[];
	devices: AudioDevice[];
	cache: ContentCache[];
	/**
	 * Diagnostics: measured drift (ppm) and offsets (ms).
	 */
	sync: {
		[k: string]: number;
	};
}
/**
 * Something the audio engine could not do, until it can again.
 */
export interface AudioError {
	code: 'output_failed' | 'output_lost' | 'load_failed' | 'master_lost';
	/**
	 * The audio device id.
	 */
	device: string | null;
	item_id: string | null;
	message: string;
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
