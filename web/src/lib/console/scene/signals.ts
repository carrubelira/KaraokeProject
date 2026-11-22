/**
 * What the background scene shows, boiled down from the live state to a few numbers per node.
 * Pure (and cheap): it runs every frame.
 */
import type { LiveState } from '#lib/control/state.js';

export interface WorkerSignal {
	id: string;
	online: boolean;
	/** 0–1: how hard its GPU works. */
	load: number;
	/** 0–1: VRAM in use. */
	memory: number;
	/** Tasks it runs now. */
	tasks: number;
	/** One of its tasks failed in the last minutes. */
	failing: boolean;
}

export interface ScreenSignal {
	id: string;
	online: boolean;
	state: 'idle' | 'loading' | 'playing' | 'paused' | 'waiting';
	/** Something on it does not work (an output lost, a song that did not load). */
	alarm: boolean;
	selected: boolean;
}

export interface Signals {
	workers: WorkerSignal[];
	screens: ScreenSignal[];
	/** Jobs waiting for the operator. */
	review: number;
	connected: boolean;
}

const RECENT = 5 * 60 * 1000;

export function signals(
	state: LiveState,
	selected: string | undefined,
	connected: boolean
): Signals {
	const now = Date.now();
	const failingOn = new Set<string>();
	let review = 0;
	for (const job of state.jobs) {
		if (job.state === 'review') review += 1;
		if (job.state !== 'failed' || now - Date.parse(job.updated_at) > RECENT) continue;
		for (const task of job.tasks)
			if (task.state === 'failed' && task.node_id) failingOn.add(task.node_id);
	}
	const workers = state.nodes
		.filter((n) => n.kind === 'worker')
		.map((n) => {
			const total = n.capabilities.gpus[0]?.vram_total_mb ?? 0;
			const used = n.telemetry.vram_used_mb ?? 0;
			return {
				id: n.id,
				online: n.online,
				load: Math.min(1, (n.telemetry.gpu_util ?? 0) / 100),
				memory: total ? Math.min(1, used / total) : 0,
				tasks: n.running.length,
				failing: failingOn.has(n.id)
			};
		});
	const screens = state.players.map((p) => ({
		id: p.id,
		online: p.online,
		state: p.status.state,
		alarm: (p.status.errors ?? []).length > 0,
		selected: p.id === selected
	}));
	return { workers, screens, review, connected };
}
