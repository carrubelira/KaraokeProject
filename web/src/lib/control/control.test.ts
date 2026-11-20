import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { apply, empty, jobProgress, positionNow } from './state';
import type { Job, PlayerView } from './types';
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
		fraction: null,
		error: null,
		error_code: null,
		outputs: {},
		elapsed: null,
		eta: null,
		...t
	}))
});

describe('live state', () => {
	it('takes a snapshot, then events', () => {
		let state = apply(empty(), {
			type: 'snapshot',
			seq: 1,
			now: 0,
			jobs: [job('a')],
			contents: [],
			playlists: [],
			players: []
		});
		state = apply(state, { type: 'job', job: job('b') });
		expect(state.jobs.map((j) => j.id)).toEqual(['b', 'a']);
		state = apply(state, {
			type: 'task',
			job_id: 'a',
			task: { ...job('a', [{}]).tasks[0], fraction: 0.5, state: 'running' }
		});
		expect(jobProgress(state.jobs[1])).toBe(0.5);
		state = apply(state, {
			type: 'playlist',
			playlist: { id: 'p', name: 'N', version: 1, items: [], player_id: null }
		});
		state = apply(state, { type: 'playlist-deleted', id: 'p' });
		expect(state.playlists).toEqual([]);
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
