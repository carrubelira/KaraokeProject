import { describe, expect, it } from 'vitest';
import { describeJob, matches, stepsOf } from './describe';
import type { Job, TaskView } from './types';

const task = (kind: TaskView['kind'], state: TaskView['state'], extra: Partial<TaskView> = {}) =>
	({
		id: `${kind}-${state}`,
		kind,
		state,
		node_id: null,
		pinned_node: null,
		priority: 0,
		attempts: 1,
		stage: null,
		fraction: null,
		error: null,
		error_code: null,
		outputs: {},
		elapsed: null,
		eta: null,
		...extra
	}) satisfies TaskView;

const job = (state: Job['state'], tasks: TaskView[], extra: Partial<Job> = {}): Job => ({
	id: 'j',
	kind: 'create',
	title: 'Song',
	state,
	params: {},
	result: null,
	error: null,
	created_at: '2026-11-22T10:00:00Z',
	updated_at: '2026-11-22T10:00:00Z',
	tasks,
	eta: 90,
	...extra
});

describe('describeJob', () => {
	it('is queued, waiting for a free machine, while no task is working', () => {
		const summary = describeJob(job('active', [task('fetch', 'ready'), task('make', 'waiting')]));
		expect(summary.status).toBe('queued');
		expect(summary.step).toBe('waiting');
		expect(summary.node).toBeNull();
	});

	it('names the stage the working task reports, and where it runs', () => {
		const summary = describeJob(
			job('active', [
				task('fetch', 'done'),
				task('make', 'running', { stage: 'separate', node_id: 'w1', fraction: 0.5 })
			])
		);
		expect(summary).toMatchObject({ status: 'running', step: 'separate', node: 'w1', eta: 90 });
		expect(summary.fraction).toBeCloseTo(0.75);
	});

	it('falls back on what the task does when it reports no stage', () => {
		expect(describeJob(job('active', [task('fetch', 'leased')])).step).toBe('download');
		expect(describeJob(job('active', [task('render', 'running')])).step).toBe('render');
	});

	it('keeps the error of the failed task and no time left', () => {
		const summary = describeJob(
			job('failed', [task('fetch', 'done'), task('make', 'failed', { error: 'out of memory' })])
		);
		expect(summary).toMatchObject({ status: 'failed', step: 'make', error: 'out of memory' });
		expect(summary.eta).toBeNull();
	});

	it('has no step once done', () => {
		const summary = describeJob(job('done', [task('fetch', 'done'), task('make', 'done')]));
		expect(summary).toMatchObject({ status: 'done', step: null, fraction: 1 });
	});

	it('says where a paused job stopped', () => {
		const summary = describeJob(job('paused', [task('fetch', 'done'), task('make', 'paused')]));
		expect(summary).toMatchObject({ status: 'paused', step: 'make' });
	});
});

describe('stepsOf', () => {
	it('turns the tasks into a timeline', () => {
		const steps = stepsOf(
			job('active', [task('fetch', 'done'), task('make', 'running'), task('package', 'waiting')])
		);
		expect(steps.map((s) => s.state)).toEqual(['done', 'current', 'pending']);
	});
});

describe('matches', () => {
	it('groups paused jobs with the ones in progress', () => {
		expect(matches(job('paused', []), 'active')).toBe(true);
		expect(matches(job('failed', []), 'active')).toBe(false);
		expect(matches(job('failed', []), 'failed')).toBe(true);
		expect(matches(job('done', []), 'all')).toBe(true);
	});
});
