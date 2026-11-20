/**
 * The control's picture of the server, and how each live event changes it. Pure, so the same
 * code runs on every event and in the tests.
 */
import type { PlayerStatus, Playlist } from '#lib/contracts';
import type { Content, Job, NodeView, PlayerView, Snapshot, TaskView, Telemetry } from './types';

export interface LiveState {
	jobs: Job[];
	contents: Content[];
	playlists: Playlist[];
	players: PlayerView[];
	nodes: NodeView[];
	/** When each player's status arrived (performance.now()), to move its position smoothly. */
	statusAt: Record<string, number>;
}

export const empty = (): LiveState => ({
	jobs: [],
	contents: [],
	playlists: [],
	players: [],
	nodes: [],
	statusAt: {}
});

function upsert<T extends { id: string }>(list: T[], item: T, first = false): T[] {
	const index = list.findIndex((x) => x.id === item.id);
	if (index < 0) return first ? [item, ...list] : [...list, item];
	const copy = list.slice();
	copy[index] = item;
	return copy;
}

export type LiveEvent =
	| Snapshot
	| { type: 'job'; job: Job }
	| { type: 'task'; job_id: string; task: TaskView }
	| { type: 'content'; content: Content }
	| { type: 'playlist'; playlist: Playlist }
	| { type: 'playlist-deleted'; id: string }
	| { type: 'player'; player_id: string; online?: boolean; config?: PlayerView['config'] }
	| { type: 'player-status'; player_id: string; status: PlayerStatus }
	| {
			type: 'player-command';
			player_id: string;
			command: { item_id: string | null; anchor: PlayerView['anchor'] };
	  }
	| { type: 'node'; node: { id: string; kind: string; name: string } }
	| { type: 'telemetry'; node_id: string; telemetry: Telemetry; busy_playing: boolean }
	| { type: 'pong'; now: number; sent: number | null };

export function apply(state: LiveState, event: LiveEvent, now = 0): LiveState {
	switch (event.type) {
		case 'snapshot':
			return {
				...state,
				jobs: event.jobs,
				contents: event.contents,
				playlists: event.playlists,
				players: event.players,
				statusAt: Object.fromEntries(event.players.map((p) => [p.id, now]))
			};
		case 'job':
			return { ...state, jobs: upsert(state.jobs, event.job, true) };
		case 'task':
			return {
				...state,
				jobs: state.jobs.map((job) =>
					job.id === event.job_id ? { ...job, tasks: upsert(job.tasks, event.task) } : job
				)
			};
		case 'content': {
			const contents = upsert(state.contents, event.content).filter((c) => !c.deleted_at);
			return { ...state, contents: contents.sort((a, b) => a.title.localeCompare(b.title)) };
		}
		case 'playlist':
			return { ...state, playlists: upsert(state.playlists, event.playlist) };
		case 'playlist-deleted':
			return { ...state, playlists: state.playlists.filter((p) => p.id !== event.id) };
		case 'player': {
			const known = state.players.some((p) => p.id === event.player_id);
			if (!known) return state;
			return {
				...state,
				players: state.players.map((p) =>
					p.id === event.player_id
						? { ...p, online: event.online ?? p.online, config: event.config ?? p.config }
						: p
				)
			};
		}
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
		case 'telemetry':
			return {
				...state,
				nodes: state.nodes.map((n) =>
					n.id === event.node_id
						? { ...n, telemetry: event.telemetry, busy_playing: event.busy_playing, online: true }
						: n
				)
			};
		default:
			return state;
	}
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
