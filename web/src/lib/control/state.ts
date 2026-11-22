/**
 * The control's picture of the server, and how each live event changes it. Pure, so the same
 * code runs on every event and in the tests.
 */
import type { PlayerStatus, Queue } from '#lib/contracts';
import type { Content, Job, NodeView, PlayerView, Snapshot, TaskView } from './types';

/** Log lines kept per task for the live view (the server keeps the same). */
export const LOG_LINES = 500;

export interface LiveState {
	jobs: Job[];
	contents: Content[];
	queues: Queue[];
	players: PlayerView[];
	nodes: NodeView[];
	/** The last lines each running task wrote, by task id. */
	logs: Record<string, string[]>;
	/** When each player's status arrived (performance.now()), to move its position smoothly. */
	statusAt: Record<string, number>;
	/** The last event's sequence number: a gap means events were lost. */
	seq: number;
}

export const empty = (): LiveState => ({
	jobs: [],
	contents: [],
	queues: [],
	players: [],
	nodes: [],
	logs: {},
	statusAt: {},
	seq: 0
});

function upsert<T>(list: T[], item: T, key: (x: T) => string, first = false): T[] {
	const index = list.findIndex((x) => key(x) === key(item));
	if (index < 0) return first ? [item, ...list] : [...list, item];
	const copy = list.slice();
	copy[index] = item;
	return copy;
}

const byId = (x: { id: string }) => x.id;

export type LiveEvent =
	| Snapshot
	| { type: 'job'; seq: number; job: Job }
	| { type: 'task'; seq: number; job_id: string; task: TaskView }
	| { type: 'task-log'; seq: number; job_id: string; task_id: string; lines: string[] }
	| { type: 'content'; seq: number; content: Content }
	| { type: 'queue'; seq: number; queue: Queue }
	| {
			type: 'player';
			seq: number;
			player_id: string;
			online?: boolean;
			config?: PlayerView['config'];
	  }
	| { type: 'player-status'; seq: number; player_id: string; status: PlayerStatus }
	| {
			type: 'player-command';
			seq: number;
			player_id: string;
			command: { item_id: string | null; anchor: PlayerView['anchor'] };
	  }
	| { type: 'node'; seq: number; node: NodeView }
	| { type: 'node-removed'; seq: number; id: string }
	| { type: 'pong'; now: number; sent: number | null };

/** True when `event` does not follow the state's last one: events were lost on the way. */
export function missed(state: LiveState, event: LiveEvent): boolean {
	if (event.type === 'snapshot' || event.type === 'pong') return false;
	return state.seq > 0 && event.seq !== state.seq + 1;
}

export function apply(state: LiveState, event: LiveEvent, now = 0): LiveState {
	const next = applyEvent(state, event, now);
	if (event.type === 'pong' || next === state) return next;
	return { ...next, seq: event.seq };
}

function applyEvent(state: LiveState, event: LiveEvent, now: number): LiveState {
	switch (event.type) {
		case 'snapshot':
			return {
				...state,
				jobs: event.jobs,
				contents: event.contents,
				queues: event.queues,
				players: event.players,
				nodes: event.nodes,
				statusAt: Object.fromEntries(event.players.map((p) => [p.id, now]))
			};
		case 'job': {
			// A finished job's tasks no longer write: their live logs can go.
			const finished = ['done', 'failed', 'cancelled'].includes(event.job.state);
			const logs = finished ? withoutLogs(state.logs, event.job) : state.logs;
			return { ...state, jobs: upsert(state.jobs, event.job, byId, true), logs };
		}
		case 'task':
			return {
				...state,
				jobs: state.jobs.map((job) =>
					job.id === event.job_id ? { ...job, tasks: upsert(job.tasks, event.task, byId) } : job
				)
			};
		case 'task-log': {
			const lines = [...(state.logs[event.task_id] ?? []), ...event.lines].slice(-LOG_LINES);
			return { ...state, logs: { ...state.logs, [event.task_id]: lines } };
		}
		case 'content': {
			const contents = upsert(state.contents, event.content, byId).filter((c) => !c.deleted_at);
			return { ...state, contents: contents.sort((a, b) => a.title.localeCompare(b.title)) };
		}
		case 'queue':
			return { ...state, queues: upsert(state.queues, event.queue, (q) => q.player_id) };
		case 'player':
			return {
				...state,
				players: state.players.map((p) =>
					p.id === event.player_id
						? { ...p, online: event.online ?? p.online, config: event.config ?? p.config }
						: p
				)
			};
		case 'player-status':
			return {
				...state,
				players: state.players.map((p) =>
					p.id === event.player_id ? { ...p, status: event.status, online: true } : p
				),
				statusAt: { ...state.statusAt, [event.player_id]: now }
			};
		case 'player-command':
			return {
				...state,
				players: state.players.map((p) =>
					p.id === event.player_id
						? { ...p, item_id: event.command.item_id, anchor: event.command.anchor }
						: p
				)
			};
		case 'node': {
			const nodes = upsert(state.nodes, event.node, byId);
			const player =
				event.node.kind === 'player' && !state.players.some((p) => p.id === event.node.id);
			return {
				...state,
				nodes,
				// A newly enrolled player: shown at once, its status comes when it connects.
				players: player
					? [...state.players, newPlayer(event.node)]
					: state.players.map((p) => (p.id === event.node.id ? { ...p, name: event.node.name } : p))
			};
		}
		case 'node-removed':
			return {
				...state,
				nodes: state.nodes.filter((n) => n.id !== event.id),
				players: state.players.filter((p) => p.id !== event.id),
				queues: state.queues.filter((q) => q.player_id !== event.id)
			};
		default:
			return state;
	}
}

function withoutLogs(logs: Record<string, string[]>, job: Job): Record<string, string[]> {
	const copy = { ...logs };
	for (const task of job.tasks) delete copy[task.id];
	return copy;
}

function newPlayer(node: NodeView): PlayerView {
	return {
		id: node.id,
		name: node.name,
		online: false,
		last_seen: node.last_seen,
		status: {
			errors: [],
			outputs: { displays: [], audio: [] },
			cache: [],
			item_id: null,
			position: null,
			state: 'idle',
			semitones: 0,
			volume: 1,
			sync: {}
		},
		config: {
			routing: { master: null, routes: [], screens: [], policies: {} },
			calibration: { audio_ms: {}, display_ms: {} }
		},
		anchor: null,
		item_id: null
	};
}

/** Where a player is in its song now, moving on from its last status while it plays. */
export function positionNow(state: LiveState, player: PlayerView, now: number): number | null {
	const position = player.status.position;
	if (position === null || position === undefined) return null;
	if (player.status.state !== 'playing') return position;
	const at = state.statusAt[player.id] ?? now;
	return position + (now - at) / 1000;
}

/** A job's overall progress, 0–1. */
export function jobProgress(job: Job): number {
	if (job.state === 'done') return 1;
	if (!job.tasks.length) return 0;
	const total = job.tasks.reduce((sum, t) => sum + (t.state === 'done' ? 1 : (t.fraction ?? 0)), 0);
	return total / job.tasks.length;
}

/** The task a job is on now (running, or the first one not done). */
export function currentTask(job: Job): TaskView | undefined {
	return (
		job.tasks.find((t) => t.state === 'running' || t.state === 'leased') ??
		job.tasks.find((t) => t.state === 'held') ??
		job.tasks.find((t) => t.state === 'failed') ??
		job.tasks.find((t) => t.state !== 'done' && t.state !== 'cancelled')
	);
}
