import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import {
	apply,
	currentTask,
	empty,
	emptySession,
	jobProgress,
	missed,
	notReady,
	positionNow
} from './state';
import type { Job, NodeView, ScreenView, Snapshot } from './types';
import { Upload } from './upload.svelte';

const job = (id: string, tasks: Partial<Job['tasks'][number]>[] = []): Job => ({
	id,
	kind: 'create',
	title: id,
	state: 'active',
	params: {},
	result: null,
	error: null,
	created_at: '',
	updated_at: '',
	eta: null,
	tasks: tasks.map((t, i) => ({
		id: `${id}:${i}`,
		kind: 'make',
		state: 'ready',
		node_id: null,
		pinned_node: null,
		priority: 0,
		attempts: 0,
		stage: null,
		step: null,
		message: null,
		fraction: null,
		error: null,
		error_code: null,
		outputs: {},
		data: {},
		log: null,
		elapsed: null,
		eta: null,
		...t
	}))
});

const node = (id: string): NodeView => ({
	id,
	kind: 'worker',
	name: id,
	capabilities: {
		os: 'windows',
		cpus: 16,
		ram_mb: 65536,
		gpus: [],
		internet: true,
		tasks: [],
		models: {},
		same_host_as_server: false
	},
	last_seen: 0,
	online: true,
	telemetry: {
		gpu_util: null,
		vram_used_mb: null,
		vram_free_mb: null,
		gpu_temp_c: null,
		cpu_util: null,
		ram_used_mb: null,
		ram_total_mb: null
	},
	busy_playing: false,
	running: []
});

const snapshot = (seq: number): Snapshot => ({
	...empty(),
	type: 'snapshot',
	seq,
	now: 0,
	jobs: [job('a')]
});

const screen = (id: string, over: Partial<ScreenView> = {}): ScreenView => ({
	id,
	online: true,
	last_seen: 0,
	hello: null,
	config: {
		name: null,
		layout: 'video-lyrics',
		theme: 'clasico',
		display_ms: 0,
		video_max_height: null
	},
	status: {
		state: 'provisioning',
		epoch: null,
		ready: false,
		flags: [],
		cache: [],
		sync: { error_ms: null, rtt_ms: null, drift_ppm: null, dropped_frames: 0 },
		error: null
	},
	counts: true,
	...over
});

describe('live state', () => {
	it('takes a snapshot, then events in order', () => {
		let state = apply(empty(), snapshot(7));
		expect(state.seq).toBe(7);
		state = apply(state, { type: 'job', seq: 8, job: job('b') });
		expect(state.jobs.map((j) => j.id)).toEqual(['b', 'a']);
		state = apply(state, {
			type: 'task',
			seq: 9,
			job_id: 'a',
			task: { ...job('a', [{}]).tasks[0], fraction: 0.5, state: 'running' }
		});
		expect(jobProgress(state.jobs[1])).toBe(0.5);
		expect(state.seq).toBe(9);
	});

	it('notices a lost event (a gap in the sequence)', () => {
		const state = apply(empty(), snapshot(7));
		expect(missed(state, { type: 'job', seq: 8, job: job('b') })).toBe(false);
		expect(missed(state, { type: 'job', seq: 10, job: job('b') })).toBe(true);
		expect(missed(state, snapshot(40))).toBe(false);
	});

	it('keeps the newest queue and session, and every screen', () => {
		let state = apply(empty(), snapshot(1));
		const queue = { version: 2, items: [] };
		state = apply(state, { type: 'queue', seq: 2, queue });
		state = apply(state, { type: 'queue', seq: 3, queue: { ...queue, version: 1 } });
		expect(state.queue.version).toBe(2);
		const cued = { ...emptySession(), version: 4, epoch: 2, state: 'cued' as const };
		state = apply(state, { type: 'session', seq: 4, session: cued });
		state = apply(state, { type: 'session', seq: 5, session: { ...cued, version: 3 } });
		expect(state.session.state).toBe('cued');
		state = apply(state, { type: 'screen', seq: 6, screen: screen('tv') });
		state = apply(state, { type: 'screen', seq: 7, screen: screen('portatil') });
		expect(notReady(state).map((s) => s.id)).toEqual(['tv', 'portatil']);
		const ready = { ...screen('tv').status!, state: 'waiting' as const, epoch: 2, ready: true };
		state = apply(state, { type: 'screen-status', seq: 8, id: 'tv', status: ready });
		expect(notReady(state).map((s) => s.id)).toEqual(['portatil']);
		state = apply(state, { type: 'screen-removed', seq: 9, id: 'portatil' });
		expect(notReady(state)).toEqual([]);
		state = apply(state, { type: 'node', seq: 10, node: node('w1') });
		state = apply(state, { type: 'node-removed', seq: 11, id: 'w1' });
		expect(state.nodes).toEqual([]);
	});

	it('streams task logs and drops them when the job ends', () => {
		let state = apply(empty(), snapshot(1));
		const running = job('a', [{ state: 'running' }]);
		state = apply(state, { type: 'task-log', seq: 2, job_id: 'a', task_id: 'a:0', lines: ['one'] });
		state = apply(state, { type: 'task-log', seq: 3, job_id: 'a', task_id: 'a:0', lines: ['two'] });
		expect(state.logs['a:0']).toEqual(['one', 'two']);
		expect(currentTask(running)?.id).toBe('a:0');
		state = apply(state, { type: 'job', seq: 4, job: { ...running, state: 'done' } });
		expect(state.logs['a:0']).toBeUndefined();
	});

	it('moves the song on from the session anchor', () => {
		const program = {
			item: {
				id: 'a',
				content_id: 'a',
				manifest: null,
				start: null,
				end: 60,
				semitones: 0,
				singer: null
			},
			manifest: 'm',
			duration: 200
		};
		const playing = {
			...emptySession(),
			state: 'playing' as const,
			current: program,
			anchor: { position: 10, instant: 1_000_000, rate: 1 }
		};
		expect(positionNow(playing, 3_000_000)).toBe(12);
		expect(positionNow(playing, 900e6)).toBe(60);
		expect(positionNow(emptySession(), 3_000_000)).toBeNull();
	});
});

describe('resumable upload', () => {
	it('goes on from the server offset after a failure', async () => {
		const file = new File([new Uint8Array(20 * 1024 * 1024)], 'song.mp3');
		let stored = 0;
		let failed = false;
		const client = {
			createUpload: async () => ({ id: 'u', offset: 0, size: file.size, blob: null }),
			uploadState: async () => ({
				id: 'u',
				offset: stored,
				size: file.size,
				blob: stored === file.size ? 'h' : null
			}),
			appendUpload: async (_: string, offset: number, chunk: Blob) => {
				if (offset !== stored) throw new ApiError(409, 'bad_offset', 'resume', { offset: stored });
				if (!failed && offset > 0) {
					failed = true;
					stored += chunk.size / 2; // half arrived, then the connection dropped
					throw new ApiError(503, 'down', 'down');
				}
				stored += chunk.size;
				return {
					id: 'u',
					offset: stored,
					size: file.size,
					blob: stored === file.size ? 'h' : null
				};
			}
		};
		const upload = new Upload(
			file,
			client as unknown as ConstructorParameters<typeof Upload>[1],
			async () => {}
		);
		expect(await upload.run()).toBe('h');
		expect(upload.fraction).toBe(1);
	});
});
