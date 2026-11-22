import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { apply, currentTask, empty, jobProgress, missed, positionNow } from './state';
import type { Job, NodeView, PlayerView, Snapshot } from './types';
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

const node = (id: string, kind: 'worker' | 'player'): NodeView => ({
	id,
	kind,
	name: id,
	capabilities: {
		os: 'windows',
		cpus: 16,
		ram_mb: 65536,
		gpus: [],
		internet: true,
		tasks: [],
		models: {},
		decoders: [],
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
	type: 'snapshot',
	seq,
	now: 0,
	jobs: [job('a')],
	contents: [],
	queues: [],
	players: [],
	nodes: []
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

	it('keeps one queue per player, and shows a new player at once', () => {
		let state = apply(empty(), snapshot(1));
		state = apply(state, { type: 'node', seq: 2, node: node('p1', 'player') });
		expect(state.players.map((p) => p.id)).toEqual(['p1']);
		const queue = { player_id: 'p1', version: 1, items: [] };
		state = apply(state, { type: 'queue', seq: 3, queue });
		state = apply(state, { type: 'queue', seq: 4, queue: { ...queue, version: 2 } });
		expect(state.queues).toEqual([{ ...queue, version: 2 }]);
		state = apply(state, { type: 'node-removed', seq: 5, id: 'p1' });
		expect(state.players).toEqual([]);
		expect(state.queues).toEqual([]);
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

	it('moves a playing player on from its last status', () => {
		const player = {
			id: 'x',
			status: { state: 'playing', position: 10 },
			online: true
		} as unknown as PlayerView;
		const state = { ...empty(), players: [player], statusAt: { x: 1000 } };
		expect(positionNow(state, player, 3000)).toBe(12);
		expect(
			positionNow(state, { ...player, status: { ...player.status, state: 'paused' } }, 3000)
		).toBe(10);
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
