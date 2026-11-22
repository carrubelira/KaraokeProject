/**
 * The console's picture of the server, and how each live event changes it. Pure, so the same
 * code runs on every event and in the tests.
 */
import type { AudioStatus, Queue, ScreenStatus, Session } from '#lib/contracts';
import { endOf, positionAt } from '#lib/screen/timeline.js';
import type { AudioView, Content, Job, NodeView, ScreenView, Snapshot, TaskView } from './types';

/** Log lines kept per task for the live view (the server keeps the same). */
export const LOG_LINES = 500;

export interface LiveState {
	jobs: Job[];
	contents: Content[];
	queue: Queue;
	session: Session;
	audio: AudioView;
	screens: ScreenView[];
	nodes: NodeView[];
	/** The last lines each running task wrote, by task id. */
	logs: Record<string, string[]>;
	/** The last event's sequence number: a gap means events were lost. */
	seq: number;
}

export const emptySession = (): Session => ({
	version: 0,
	epoch: 0,
	state: 'idle',
	current: null,
	anchor: null,
	upcoming: [],
	semitones: 0,
	volume: 1
});

const emptyAudio = (): AudioView => ({
	online: false,
	required: true,
	fault: null,
	status: {
		state: 'idle',
		epoch: null,
		ready: false,
		item_id: null,
		position: null,
		errors: [],
		devices: [],
		cache: [],
		sync: {}
	},
	config: { routing: { master: null, routes: [], policies: {} }, calibration_ms: {} }
});

export const empty = (): LiveState => ({
	jobs: [],
	contents: [],
	queue: { version: 0, items: [] },
	session: emptySession(),
	audio: emptyAudio(),
	screens: [],
	nodes: [],
	logs: {},
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
	| { type: 'session'; seq: number; session: Session }
	| { type: 'audio'; seq: number; audio: AudioView }
	| { type: 'audio-status'; seq: number; status: AudioStatus }
	| { type: 'screen'; seq: number; screen: ScreenView }
	| { type: 'screen-status'; seq: number; id: string; status: ScreenStatus }
	| { type: 'screen-removed'; seq: number; id: string }
	| { type: 'node'; seq: number; node: NodeView }
	| { type: 'node-removed'; seq: number; id: string }
	| { type: 'pong'; now: number; sent: number | null };

/** True when `event` does not follow the state's last one: events were lost on the way. */
export function missed(state: LiveState, event: LiveEvent): boolean {
	if (event.type === 'snapshot' || event.type === 'pong') return false;
	return state.seq > 0 && event.seq !== state.seq + 1;
}

export function apply(state: LiveState, event: LiveEvent): LiveState {
	const next = applyEvent(state, event);
	if (event.type === 'pong' || next === state) return next;
	return { ...next, seq: event.seq };
}

function applyEvent(state: LiveState, event: LiveEvent): LiveState {
	switch (event.type) {
		case 'snapshot':
			return {
				...state,
				jobs: event.jobs,
				contents: event.contents,
				queue: event.queue,
				session: event.session,
				audio: event.audio,
				screens: event.screens,
				nodes: event.nodes
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
			return event.queue.version >= state.queue.version ? { ...state, queue: event.queue } : state;
		case 'session':
			return event.session.version >= state.session.version
				? { ...state, session: event.session }
				: state;
		case 'audio':
			return { ...state, audio: event.audio };
		case 'audio-status':
			return { ...state, audio: { ...state.audio, online: true, status: event.status } };
		case 'screen':
			return { ...state, screens: upsert(state.screens, event.screen, byId) };
		case 'screen-status':
			return {
				...state,
				screens: state.screens.map((s) =>
					s.id === event.id ? { ...s, online: true, status: event.status } : s
				)
			};
		case 'screen-removed':
			return { ...state, screens: state.screens.filter((s) => s.id !== event.id) };
		case 'node':
			return { ...state, nodes: upsert(state.nodes, event.node, byId) };
		case 'node-removed':
			return { ...state, nodes: state.nodes.filter((n) => n.id !== event.id) };
		default:
			return state;
	}
}

function withoutLogs(logs: Record<string, string[]>, job: Job): Record<string, string[]> {
	const copy = { ...logs };
	for (const task of job.tasks) delete copy[task.id];
	return copy;
}

/** Where the song on is at server instant `server` (µs), from the session's anchor. */
export function positionNow(session: Session, server: number): number | null {
	if (!session.anchor || !session.current) return null;
	return positionAt(session.anchor, server, endOf(session.current));
}

/** The screens the operator is warned about that are not on the cued frame. */
export function notReady(state: LiveState): ScreenView[] {
	return state.screens.filter(
		(s) => s.counts && !(s.status?.ready && s.status.epoch === state.session.epoch)
	);
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
