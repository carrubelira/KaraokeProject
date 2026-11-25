<script lang="ts">
	/**
	 * Processing: one row per song being made, with its state, the step it is on and how far, the
	 * computer doing it and the time. A row opens to show every step (download, analysis, making
	 * the karaoke, or the video), why one failed and what to do, and each step's log.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { commands } from '#lib/commands/registry.svelte.js';
	import ErrorNote from '#lib/console/ErrorNote.svelte';
	import Icon from '#lib/console/Icon.svelte';
	import LogView from '#lib/console/LogView.svelte';
	import { live } from '#lib/control/live.svelte.js';
	import { currentTask, jobProgress } from '#lib/control/state.js';
	import type { Job, JobState, TaskState, TaskView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';

	type Filter = 'all' | 'active' | 'review' | 'failed' | 'done';
	const t = $derived(i18n.t);
	let filter = $state<Filter>('all');
	const FILTERS: Filter[] = ['all', 'active', 'review', 'failed', 'done'];
	const matches: Record<Filter, (j: Job) => boolean> = {
		all: () => true,
		active: (j) => j.state === 'active' || j.state === 'paused',
		review: (j) => j.state === 'review',
		failed: (j) => j.state === 'failed',
		done: (j) => j.state === 'done' || j.state === 'cancelled'
	};
	const shown = $derived(live.state.jobs.filter(matches[filter]));
	const counts = $derived(
		Object.fromEntries(FILTERS.map((f) => [f, live.state.jobs.filter(matches[f]).length]))
	);
	const open = new SvelteSet<string>();
	let logOf = $state<string | null>(null);

	const JOB_TONE: Record<JobState, string> = {
		active: 'info',
		review: 'warn',
		paused: 'warn',
		done: 'ok',
		failed: 'error',
		cancelled: 'plain'
	};
	const TASK_TONE: Record<TaskState, string> = {
		waiting: 'plain',
		held: 'warn',
		ready: 'plain',
		leased: 'info',
		running: 'info',
		done: 'ok',
		failed: 'error',
		cancelled: 'plain',
		paused: 'warn'
	};

	const nodeName = (id: string | null) =>
		id ? (live.state.nodes.find((n) => n.id === id)?.name ?? id) : null;

	function stepText(task: TaskView | undefined): string {
		if (!task) return '';
		const kind = t.jobs.kinds[task.kind];
		if (task.state !== 'running') return kind;
		const stage = task.stage ? (t.jobs.stages[task.stage] ?? task.stage) : null;
		return [kind, stage, task.step].filter(Boolean).join(' · ');
	}

	function jobTime(job: Job): string {
		if (job.state === 'active' && job.eta !== null) return t.jobs.eta(clock(job.eta));
		const elapsed = job.tasks.reduce((sum, x) => sum + (x.elapsed ?? 0), 0);
		return elapsed ? clock(elapsed) : '';
	}

	function toggle(id: string) {
		if (open.has(id)) open.delete(id);
		else open.add(id);
	}

	onMount(() => {
		commands.scope = 'jobs';
		return commands.register({
			id: 'jobs.retryFailed',
			title: () => t.cmd.retryFailed,
			group: () => t.groups.jobs,
			scope: 'jobs',
			keys: ['Shift+r'],
			run: jobs.retryFailed
		});
	});
</script>

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.jobs.title}</h1>
			<p class="description">{t.jobs.description}</p>
		</div>
		<div class="actions">
			{#if counts.failed}
				<button class="btn" onclick={jobs.retryFailed}>
					<Icon name="retry" size={16} />
					{t.cmd.retryFailed}
				</button>
			{/if}
			<a class="btn primary" href={resolve('/engadir')}>
				<Icon name="add" size={16} />
				{t.nav.add}
			</a>
		</div>
	</header>

	<section class="panel">
		<div class="tabs" role="tablist">
			{#each FILTERS as f (f)}
				<button role="tab" aria-selected={filter === f} onclick={() => (filter = f)}>
					{t.jobs.filters[f]}<span class="count">{counts[f]}</span>
				</button>
			{/each}
		</div>

		{#if shown.length}
			<table class="table jobs">
				<thead>
					<tr>
						<th class="expand"><span class="sr-only">{t.jobs.steps}</span></th>
						<th>{t.jobs.song}</th>
						<th>{t.jobs.status}</th>
						<th>{t.jobs.step}</th>
						<th>{t.jobs.device}</th>
						<th class="num">{t.jobs.time}</th>
						<th><span class="sr-only">{t.common.more}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each shown as job (job.id)}
						{@const task = currentTask(job)}
						{@const isOpen = open.has(job.id)}
						{@const failed = job.tasks.find((x) => x.state === 'failed')}
						<tr class="job" class:selected={isOpen} onclick={() => toggle(job.id)}>
							<td class="expand">
								<button
									class="btn subtle icon chevron"
									class:open={isOpen}
									aria-expanded={isOpen}
									aria-label={t.jobs.steps}
									onclick={(e) => {
										e.stopPropagation();
										toggle(job.id);
									}}
								>
									<Icon name="chevron" size={16} />
								</button>
							</td>
							<td><strong class="title truncate">{job.title}</strong></td>
							<td><span class="badge {JOB_TONE[job.state]}">{t.jobs.states[job.state]}</span></td>
							<td class="step">
								{#if job.state === 'active' || job.state === 'paused'}
									<span class="truncate">{stepText(task)}</span>
									<div class="progress">
										<span style:width="{jobProgress(job) * 100}%"></span>
									</div>
								{:else if job.state === 'failed' && failed}
									<span class="error-text truncate">
										{t.jobs.kinds[failed.kind]} · {(
											t.errors[failed.error_code ?? 'unknown'] ?? t.errors.unknown
										).title}
									</span>
								{:else if job.state === 'review'}
									<span class="muted">{t.jobs.tasks.held}</span>
								{/if}
							</td>
							<td class="muted">{nodeName((task ?? job.tasks.at(-1))?.node_id ?? null) ?? ''}</td>
							<td class="num muted">{jobTime(job)}</td>
							<td class="row-actions" onclick={(e) => e.stopPropagation()}>
								{#if job.state === 'review'}
									<button class="btn primary" onclick={() => goto(resolve('/engadir'))}>
										{t.jobs.review}
									</button>
								{:else if job.state === 'done' && job.result?.content_id}
									<button class="btn subtle" onclick={() => goto(resolve('/biblioteca'))}>
										{t.jobs.openSong}
									</button>
								{/if}
								{#if job.state === 'active'}
									<button
										class="btn subtle icon"
										title={t.cmd.pauseJob}
										aria-label={t.cmd.pauseJob}
										onclick={() => jobs.act([job.id], 'pause')}
									>
										<Icon name="pause" size={16} />
									</button>
								{:else if job.state === 'paused'}
									<button
										class="btn subtle icon"
										title={t.cmd.resumeJob}
										aria-label={t.cmd.resumeJob}
										onclick={() => jobs.act([job.id], 'resume')}
									>
										<Icon name="play" size={16} />
									</button>
								{:else if job.state === 'failed' || job.state === 'cancelled'}
									<button
										class="btn subtle icon"
										title={t.cmd.retry}
										aria-label={t.cmd.retry}
										onclick={() => jobs.act([job.id], 'retry')}
									>
										<Icon name="retry" size={16} />
									</button>
								{/if}
								{#if ['active', 'paused', 'review'].includes(job.state)}
									<button
										class="btn subtle icon"
										title={t.cmd.cancel}
										aria-label={t.cmd.cancel}
										onclick={() => jobs.act([job.id], 'cancel')}
									>
										<Icon name="close" size={16} />
									</button>
								{/if}
							</td>
						</tr>
						{#if isOpen}
							<tr class="detail">
								<td></td>
								<td colspan="6">
									<div class="detail-body">
										{#if failed}
											<ErrorNote task={failed} {job} onlog={() => (logOf = failed.id)} />
										{/if}
										<table class="table steps">
											<thead>
												<tr>
													<th>{t.jobs.steps}</th>
													<th>{t.jobs.status}</th>
													<th>{t.jobs.device}</th>
													<th class="num">{t.jobs.time}</th>
													<th><span class="sr-only">{t.jobs.log}</span></th>
												</tr>
											</thead>
											<tbody>
												{#each job.tasks as step (step.id)}
													<tr>
														<td>
															<div class="step-name">
																<span>{t.jobs.kinds[step.kind]}</span>
																{#if step.state === 'running' && (step.stage || step.message)}
																	<span class="muted small truncate">
																		{[
																			step.stage ? (t.jobs.stages[step.stage] ?? step.stage) : null,
																			step.step,
																			step.message
																		]
																			.filter(Boolean)
																			.join(' · ')}
																	</span>
																{/if}
															</div>
														</td>
														<td>
															<span class="badge {TASK_TONE[step.state]}">
																{t.jobs.tasks[step.state]}{step.state === 'running' &&
																step.fraction !== null
																	? ` ${Math.round(step.fraction * 100)} %`
																	: ''}
															</span>
															{#if step.attempts > 1}
																<span class="faint small">{t.jobs.attempt(step.attempts)}</span>
															{/if}
														</td>
														<td class="muted">{nodeName(step.node_id) ?? ''}</td>
														<td class="num muted">
															{#if step.state === 'running' && step.eta}
																{t.jobs.eta(clock(step.eta))}
															{:else if step.elapsed}
																{clock(step.elapsed)}
															{/if}
														</td>
														<td class="row-actions">
															{#if step.state !== 'waiting' && step.state !== 'ready' && step.state !== 'held'}
																<button
																	class="btn subtle"
																	aria-expanded={logOf === step.id}
																	onclick={() => (logOf = logOf === step.id ? null : step.id)}
																>
																	<Icon name="log" size={16} />
																	{logOf === step.id ? t.jobs.hideLog : t.jobs.showLog}
																</button>
															{/if}
														</td>
													</tr>
													{#if logOf === step.id}
														<tr class="log-row">
															<td colspan="5"><LogView {job} task={step} /></td>
														</tr>
													{/if}
												{/each}
											</tbody>
										</table>
									</div>
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="empty"><p>{t.jobs.empty}</p></div>
		{/if}
	</section>
</div>

<style>
	.tabs {
		padding: 0 8px;
	}
	.jobs .expand {
		width: 44px;
		padding-right: 0;
	}
	.jobs tr.job {
		cursor: pointer;
	}
	.chevron :global(svg) {
		transition: transform 0.15s ease;
	}
	.chevron.open :global(svg) {
		transform: rotate(90deg);
	}
	.title {
		display: block;
		max-width: 340px;
	}
	.step {
		min-width: 180px;
		max-width: 320px;
	}
	.step > span {
		display: block;
		margin-bottom: 4px;
	}
	.error-text {
		color: var(--error);
	}
	.row-actions {
		width: 1%;
	}
	.row-actions > :global(*) {
		margin-left: 2px;
	}
	tr.detail,
	tr.detail:hover {
		background: var(--bg);
	}
	.detail-body {
		display: grid;
		gap: 12px;
		padding: 4px 0 8px;
	}
	.steps {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		border-collapse: separate;
		border-spacing: 0;
		background: var(--surface);
	}
	.steps th,
	.steps td {
		padding: 8px 12px;
	}
	.step-name {
		display: flex;
		flex-direction: column;
		min-width: 0;
		max-width: 420px;
	}
	.log-row:hover {
		background: none;
	}

	@media (max-width: 900px) {
		.jobs th:nth-child(5),
		.jobs td:nth-child(5),
		.jobs th:nth-child(6),
		.jobs td:nth-child(6) {
			display: none;
		}
	}
</style>
