/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * Sent once with a one-time token; the answer carries the node's own credential.
 */
export interface Enrollment {
	token: string;
	kind: 'worker' | 'player';
	name: string;
	capabilities: Capabilities;
}
export interface Capabilities {
	os: 'windows' | 'linux' | 'macos';
	cpus: number;
	ram_mb: number;
	gpus: Gpu[];
	internet: boolean;
	/**
	 * Task kinds it can run.
	 */
	tasks: ('fetch' | 'make' | 'package' | 'render')[];
	/**
	 * Model name to version.
	 */
	models: {
		[k: string]: string;
	};
	/**
	 * Video codecs a player decodes in hardware.
	 */
	decoders: string[];
	/**
	 * It shares the server's disk: blobs go by path, not HTTP.
	 */
	same_host_as_server: boolean;
}
export interface Gpu {
	name: string;
	vram_total_mb: number;
}
