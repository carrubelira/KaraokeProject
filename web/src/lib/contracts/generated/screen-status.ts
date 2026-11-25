/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface ScreenStatus {
	state: 'connecting' | 'idle' | 'provisioning' | 'syncing' | 'waiting' | 'playing' | 'paused' | 'error';
	/**
	 * The session epoch this state is about.
	 */
	epoch: number | null;
	/**
	 * Its first frame is on screen, at the cue.
	 */
	ready: boolean;
	flags: ('offline' | 'hidden' | 'degraded' | 'fullscreen')[];
	cache: ContentCache[];
	sync: ScreenSync;
	error: string | null;
}
export interface ContentCache {
	content_id: string;
	manifest: string;
	state: 'absent' | 'downloading' | 'verifying' | 'ready' | 'failed';
	fraction: number;
	error: string | null;
}
export interface ScreenSync {
	/**
	 * p95 of picture vs timeline.
	 */
	error_ms: number | null;
	rtt_ms: number | null;
	drift_ppm: number | null;
	dropped_frames: number;
}
