/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Lease {
	task: Task;
	lease_id: string;
	expires_at: string;
	heartbeat_seconds: number;
}
export interface Task {
	id: string;
	kind: 'fetch' | 'analyze' | 'make' | 'package' | 'render';
	job_id: string;
	params: {};
	/**
	 * Blobs it reads.
	 */
	inputs: string[];
	vram_mb: number;
	needs_internet: boolean;
	priority: number;
}
