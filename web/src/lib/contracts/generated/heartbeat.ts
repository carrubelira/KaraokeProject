/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Heartbeat {
	telemetry: Telemetry;
	/**
	 * Task ids it holds.
	 */
	running: string[];
	/**
	 * A player on this machine is playing: go easy on the GPU.
	 */
	busy_playing: boolean;
}
export interface Telemetry {
	gpu_util: number | null;
	vram_used_mb: number | null;
	vram_free_mb: number | null;
	gpu_temp_c: number | null;
	cpu_util: number | null;
	ram_used_mb: number | null;
}
