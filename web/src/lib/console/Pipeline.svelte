<script lang="ts">
	/**
	 * One job as a pipeline: its tasks left to right (download → analysis → karaoke, or the video),
	 * each lit by its state, with what the worker is doing right now, how far it is and how long
	 * is left; a failure says why and what to do; every task's log opens below.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { live } from '#lib/control/live.svelte.js';
	import { currentTask, jobProgress } from '#lib/control/state.js';
	import type { Job, TaskView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import ErrorNote from './ErrorNote.svelte';
	import Icon from './Icon.svelte';
	import LogView from './LogView.svelte';

	let { job }: { job: Job } = $props();
	const t = $derived(i18n.t);
	const now = $derived(currentTask(job));
	const failed = $derived(job.tasks.find((x) => x.state === 'failed'));
	let logOf = $state<string | null>(null);
	const logTask = $derived(job.tasks.find((x) => x.id === logOf) ?? null);
	const tone = $derived(
		{
			active: 'info',
			review: 'warn',
			paused: 'warn',
			done: 'cue',
			failed: 'onair',
			cancelled: 'off'
		}[job.state]
	);
	const nodeName = (id: string | null) => live.state.nodes.find((n) => n.id === id)?.name ?? id;

	function stageText(task: TaskView): string {
		if (task.state !== 'running') return t.jobs.tasks[task.state];
		const stage = task.stage ? (t.jobs.stages[task.stage] ?? task.stage) : t.jobs.tasks.running;
		return task.step ? `${stage} · ${task.step}` : stage;
	}
</script>

<article
	class="c-panel job"
	class:is-onair={job.state === 'failed'}
	class:is-warn={job.state === 'review'}
>
	<header class="c-panel-head">
		<span class="c-tally {tone}">{t.jobs.states[job.state]}</span>
		<strong class="title">{job.title}</strong>
		<span class="spacer"></span>
		{#if job.state === 'active' && job.eta !== null}
			<span class="mono dim small">{t.jobs.eta(clock(job.eta))}</span>
		{/if}
		<span class="actions">
			{#if job.state === 'review'}
				<button class="c-btn go" onclick={() => goto(resolve('/engadir'))}>{t.jobs.review}</button>
			{/if}
			{#if job.state === 'done' && job.result?.content_id}
				<button class="c-btn ghost" onclick={() => goto(resolve('/biblioteca'))}
					>{t.jobs.openSong}</button
				>
			{/if}
			{#if job.state === 'active'}
				<button
					class="c-btn icon ghost"
					title={t.cmd.pauseJob}
					aria-label={t.cmd.pauseJob}
					onclick={() => jobs.act([job.id], 'pause')}
				>
					<Icon name="pause" size={16} />
				</button>
				<button
					class="c-btn icon ghost"
					title={t.cmd.prioritise}
					aria-label={t.cmd.prioritise}
					onclick={() => jobs.priority(job.id, 10)}
				>
					<Icon name="up" size={16} />
				</button>
			{/if}
			{#if job.state === 'paused'}
				<button
					class="c-btn icon ghost"
					title={t.cmd.resumeJob}
					aria-label={t.cmd.resumeJob}
					onclick={() => jobs.act([job.id], 'resume')}
				>
					<Icon name="play" size={16} />
				</button>
			{/if}
			{#if job.state === 'failed' || job.state === 'cancelled'}
				<button
					class="c-btn icon ghost"
					title={t.cmd.retry}
					aria-label={t.cmd.retry}
					onclick={() => jobs.act([job.id], 'retry')}
				>
					<Icon name="retry" size={16} />
				</button>
			{/if}
			{#if ['active', 'paused', 'review'].includes(job.state)}
				<button
					class="c-btn icon ghost"
					title={t.cmd.cancel}
					aria-label={t.cmd.cancel}
					onclick={() => jobs.act([job.id], 'cancel')}
				>
					<Icon name="close" size={16} />
				</button>
			{/if}
		</span>
	</header>

	<div class="c-progress" style:--value={jobProgress(job)}></div>

	<ol class="tasks">
		{#each job.tasks as task (task.id)}
			<li class="task {task.state}" class:current={task.id === now?.id}>
				<button
					class="open"
					onclick={() => (logOf = logOf === task.id ? null : task.id)}
					aria-expanded={logOf === task.id}
				>
					<span class="kind label">{t.jobs.kinds[task.kind]}</span>
					<span class="state">{stageText(task)}</span>
					{#if task.state === 'running' && task.fraction !== null}
						<span class="c-meter info" style:--value={task.fraction}></span>
					{/if}
					<span class="meta mono">
						{#if task.node_id}<span>{t.jobs.on(nodeName(task.node_id) ?? '')}</span>{/if}
						{#if task.attempts > 1}<span class="warn">{t.jobs.attempt(task.attempts)}</span>{/if}
						{#if task.state === 'running' && task.eta}<span>{t.jobs.eta(clock(task.eta))}</span
							>{/if}
						{#if task.state === 'running' && task.elapsed}<span class="faint"
								>{clock(task.elapsed)}</span
							>{/if}
					</span>
				</button>
				{#if task.state === 'running' && task.message}<p class="message">{task.message}</p>{/if}
			</li>
		{/each}
	</ol>

	{#if failed}
		<div class="failure">
			<ErrorNote task={failed} {job} onlog={() => (logOf = failed.id)} />
		</div>
	{/if}

	{#if logTask}
		<div class="logs">
			<span class="label">{t.jobs.log} · {t.jobs.kinds[logTask.kind]}</span>
			<LogView {job} task={logTask} />
		</div>
	{/if}
</article>

<style>
	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}
	.small {
		font-size: 12px;
	}
	.actions {
		display: flex;
		gap: 4px;
	}
	.tasks {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(0, 1fr);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.task {
		position: relative;
		border-right: 1px solid var(--line);
	}
	.task:last-child {
		border-right: 0;
	}
	.task::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: 0;
		height: 2px;
		background: var(--line);
	}
	.task.done::after {
		background: var(--cue);
	}
	.task.running::after,
	.task.leased::after {
		background: var(--info);
		box-shadow: 0 0 10px var(--info);
	}
	.task.failed::after {
		background: var(--onair);
	}
	.task.held::after {
		background: var(--warn);
	}
	.open {
		display: grid;
		gap: 6px;
		width: 100%;
		padding: 12px 14px;
		border: 0;
		background: transparent;
		text-align: left;
		cursor: pointer;
	}
	.open:hover {
		background: rgb(150 175 205 / 0.04);
	}
	.state {
		font-size: 14px;
		font-weight: 600;
	}
	.waiting .state,
	.ready .state,
	.cancelled .state {
		color: var(--faint);
		font-weight: 500;
	}
	.done .state {
		color: var(--cue);
	}
	.failed .state {
		color: var(--onair);
	}
	.held .state {
		color: var(--warn);
	}
	.running .state {
		color: var(--info);
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
		font-size: 11px;
		color: var(--dim);
	}
	.meta .warn {
		color: var(--warn);
	}
	.message {
		margin: 0;
		padding: 0 14px 12px;
		font-size: 12.5px;
		color: var(--dim);
	}
	.failure,
	.logs {
		display: grid;
		gap: 8px;
		padding: 12px 14px 14px;
		border-top: 1px solid var(--line);
	}
	@media (max-width: 760px) {
		.tasks {
			grid-auto-flow: row;
		}
		.task {
			border-right: 0;
			border-bottom: 1px solid var(--line);
		}
	}
</style>
