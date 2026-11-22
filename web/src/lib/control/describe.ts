/**
 * A job told in plain words: what state it is in, which step it is on and where, without the
 * queue's vocabulary (tasks, leases, kinds). The views only translate the keys this returns.
 */
import { jobProgress } from './state';
import type { Job, TaskView } from './types';

export type JobStatus = 'queued' | 'running' | 'paused' | 'done' | 'failed' | 'cancelled';

/** What is being done right now (or where it stopped). */
export type Step =
	| 'waiting'
	| 'download'
	| 'decode'
	| 'separate'
	| 'transcribe'
	| 'align'
	| 'encode'
	| 'upload'
	| 'make'
	| 'package'
	| 'render';

export type StepState = 'done' | 'current' | 'pending' | 'failed' | 'cancelled';

export interface JobSummary {
	status: JobStatus;
	step: Step | null;
	/** The task the step belongs to. */
	task: TaskView | null;
	/** The machine doing it, by id. */
	node: string | null;
	fraction: number;
	eta: number | null;
	error: string | null;
}

export type JobFilter = 'all' | 'active' | 'failed' | 'done';

const STAGES: Record<string, Step> = {
	download: 'download',
	decode: 'decode',
	separate: 'separate',
	transcribe: 'transcribe',
	align: 'align',
	encode: 'encode',
	upload: 'upload',
	render: 'render'
};

const KIND_STEP: Record<TaskView['kind'], Step> = {
	fetch: 'download',
	make: 'make',
	package: 'package',
	render: 'render'
};

const working = (task: TaskView) => task.state === 'running' || task.state === 'leased';

/** The step a task is on: its reported stage, or what its kind does. */
export function stepOf(task: TaskView): Step {
	if (task.state === 'ready') return 'waiting';
	return (task.stage && STAGES[task.stage]) || KIND_STEP[task.kind];
}

/** The task that tells where the job is: the one working, else the one it stopped or waits on. */
function currentTask(job: Job): TaskView | null {
	const tasks = job.tasks;
	return (
		tasks.find(working) ??
		tasks.find((t) => t.state === 'failed') ??
		tasks.find((t) => t.state === 'ready') ??
		tasks.find((t) => t.state !== 'done' && t.state !== 'cancelled') ??
		null
	);
}

export function describeJob(job: Job): JobSummary {
	const task = job.state === 'done' ? null : currentTask(job);
	const status: JobStatus =
		job.state === 'active' ? (job.tasks.some(working) ? 'running' : 'queued') : job.state;
	let step: Step | null = null;
	if (task && status !== 'cancelled') step = status === 'queued' ? 'waiting' : stepOf(task);
	if (status === 'paused' && task) step = KIND_STEP[task.kind];
	return {
		status,
		step,
		task,
		node: task && working(task) ? task.node_id : null,
		fraction: jobProgress(job),
		eta: status === 'running' || status === 'queued' ? job.eta : null,
		error: status === 'failed' ? (task?.error ?? job.error) : null
	};
}

/** The job's tasks as a timeline. */
export function stepsOf(job: Job): { task: TaskView; state: StepState }[] {
	return job.tasks.map((task) => ({
		task,
		state:
			task.state === 'done'
				? 'done'
				: task.state === 'failed'
					? 'failed'
					: task.state === 'cancelled'
						? 'cancelled'
						: working(task)
							? 'current'
							: 'pending'
	}));
}

export function matches(job: Job, filter: JobFilter): boolean {
	switch (filter) {
		case 'all':
			return true;
		case 'active':
			return job.state === 'active' || job.state === 'paused';
		case 'failed':
			return job.state === 'failed';
		case 'done':
			return job.state === 'done';
	}
}

/** The colour class of a job's status mark, the same in every view. */
export const BADGE: Record<JobStatus, string> = {
	queued: '',
	running: 'ctl-active',
	paused: 'ctl-warn',
	done: 'ctl-ok',
	failed: 'ctl-bad',
	cancelled: ''
};
