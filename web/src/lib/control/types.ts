/** What the v4 server answers (plan v4 §3); contracts v2 types come from #lib/contracts. */
import type { PlayerConfig, PlayerStatus, Playlist } from '#lib/contracts';

export interface Content {
	id: string;
	manifest: string;
	version: number;
	title: string;
	artist: string | null;
	language: string;
	duration: number;
	created_at: string;
	updated_at: string;
	deleted_at: string | null;
}

export type TaskState =
	'waiting' | 'ready' | 'leased' | 'running' | 'done' | 'failed' | 'cancelled' | 'paused';

export interface TaskView {
	id: string;
	kind: 'fetch' | 'make' | 'package' | 'render';
	state: TaskState;
	node_id: string | null;
	pinned_node: string | null;
	priority: number;
	attempts: number;
	stage: string | null;
	fraction: number | null;
	error: string | null;
	error_code: string | null;
	outputs: Record<string, string>;
	elapsed: number | null;
	eta: number | null;
}

export type JobState = 'active' | 'paused' | 'done' | 'failed' | 'cancelled';

export interface Job {
	id: string;
	kind: 'create' | 'render';
	title: string;
	state: JobState;
	params: Record<string, unknown>;
	result: { outputs: Record<string, string>; content_id?: string; manifest?: string } | null;
	error: string | null;
	created_at: string;
	updated_at: string;
	tasks: TaskView[];
	eta: number | null;
}

export interface Telemetry {
	gpu_util: number | null;
	vram_used_mb: number | null;
	vram_free_mb: number | null;
	gpu_temp_c: number | null;
	cpu_util: number | null;
	ram_used_mb: number | null;
}

export interface NodeView {
	id: string;
	kind: 'worker' | 'player';
	name: string;
	capabilities: {
		os: string;
		cpus: number;
		ram_mb: number;
		gpus: { name: string; vram_total_mb: number }[];
		internet: boolean;
		tasks: string[];
		models: Record<string, string>;
		decoders: string[];
		same_host_as_server: boolean;
	};
	last_seen: number;
	online: boolean;
	telemetry: Telemetry;
	busy_playing: boolean;
	running: string[];
}

export interface PlayerView {
	id: string;
	name: string;
	online: boolean;
	last_seen: number;
	status: PlayerStatus;
	config: PlayerConfig;
	anchor: { position: number; instant: number; rate: number } | null;
	item_id: string | null;
}

export interface Snapshot {
	type: 'snapshot';
	seq: number;
	now: number;
	jobs: Job[];
	contents: Content[];
	playlists: Playlist[];
	players: PlayerView[];
}

export interface Session {
	id: string;
	name: string;
	preferences: Record<string, unknown>;
}

export interface Candidate {
	id: number;
	title: string;
	artist: string;
	album: string | null;
	duration: number;
	synced: boolean;
	text: string;
	duration_gap: number | null;
}
