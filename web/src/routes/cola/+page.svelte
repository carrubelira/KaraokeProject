<script lang="ts">
	/** The queue: every job with its tasks, stage, progress, ETA and worker (scope `queue`). */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { jobProgress } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { Selection } from '#lib/shell/selection.svelte.js';

	const t = $derived(i18n.t);
	const list = $derived(live.state.jobs);
	const selection = new Selection(() => list.map((j) => j.id));
	const nodeName = (id: string | null) =>
		live.state.nodes.find((n) => n.id === id)?.name ?? id ?? '';

	$effect(() => {
		void list.length;
		selection.clamp();
	});

	const targeted = () => selection.targets;
	const states = (wanted: string[]) =>
		targeted().filter((id) => wanted.includes(list.find((j) => j.id === id)?.state ?? ''));

	onMount(() => {
		commands.scope = 'queue';
		const group = () => t.groups.queue;
		return commands.register(
			{
				id: 'queue.down',
				title: () => t.cmd.down,
				group,
				scope: 'queue',
				keys: ['j', 'ArrowDown'],
				run: () => selection.move(1),
				hidden: true
			},
			{
				id: 'queue.up',
				title: () => t.cmd.up,
				group,
				scope: 'queue',
				keys: ['k', 'ArrowUp'],
				run: () => selection.move(-1),
				hidden: true
			},
			{
				id: 'queue.extendDown',
				title: () => t.cmd.selectDown,
				group,
				scope: 'queue',
				keys: ['Shift+j'],
				run: () => selection.extend(1)
			},
			{
				id: 'queue.extendUp',
				title: () => t.cmd.selectUp,
				group,
				scope: 'queue',
				keys: ['Shift+k'],
				run: () => selection.extend(-1)
			},
			{
				id: 'queue.mark',
				title: () => t.cmd.toggleSelect,
				group,
				scope: 'queue',
				keys: ['x'],
				run: () => selection.toggle()
			},
			{
				id: 'queue.retry',
				title: () => t.cmd.retry,
				group,
				scope: 'queue',
				keys: ['r'],
				run: () => jobs.act(states(['failed', 'cancelled']), 'retry')
			},
			{
				id: 'queue.retryFailed',
				title: () => t.cmd.retryFailed,
				group,
				scope: 'queue',
				keys: ['Shift+r'],
				run: jobs.retryFailed
			},
			{
				id: 'queue.cancel',
				title: () => t.cmd.cancel,
				group,
				scope: 'queue',
				keys: ['Delete', 'Backspace'],
				run: () => jobs.act(states(['active', 'paused']), 'cancel')
			},
			{
				id: 'queue.pause',
				title: () => t.cmd.pauseJob,
				group,
				scope: 'queue',
				keys: ['Shift+p'],
				run: () => jobs.act(states(['active']), 'pause')
			},
			{
				id: 'queue.resume',
				title: () => t.cmd.resumeJob,
				group,
				scope: 'queue',
				keys: ['Shift+c'],
				run: () => jobs.act(states(['paused']), 'resume')
			},
			{
				id: 'queue.up_',
				title: () => t.cmd.prioritise,
				group,
				scope: 'queue',
				keys: ['Alt+ArrowUp', '+'],
				run: () => jobs.priority(states(['active', 'paused']), 10)
			},
			{
				id: 'queue.down_',
				title: () => t.cmd.deprioritise,
				group,
				scope: 'queue',
				keys: ['Alt+ArrowDown', '-'],
				run: () => jobs.priority(states(['active', 'paused']), -10)
			}
		);
	});

	const pill = (state: string) =>
		state === 'done'
			? 'ctl-ok'
			: state === 'failed'
				? 'ctl-bad'
				: state === 'active'
					? 'ctl-warn'
					: '';
</script>

<div class="ctl-page">
	<div class="ctl-page-head">
		<h1>{t.queue.title}</h1>
		<span class="ctl-muted"
			>{list.filter((j) => j.state === 'active').length} · {t.queue.states.active}</span
		>
	</div>
	{#if list.length === 0}
		<p class="ctl-muted">{t.queue.empty}</p>
	{:else}
		<ul class="ctl-rows" role="listbox" aria-label={t.queue.title}>
			{#each list as job, i (job.id)}
				{@const progress = jobProgress(job)}
				<li
					class="ctl-row job"
					class:ctl-cursor={i === selection.cursor}
					class:ctl-marked={selection.marked.has(job.id)}
					role="option"
					aria-selected={i === selection.cursor}
					onclick={() => (selection.cursor = i)}
					onkeydown={() => {}}
				>
					<span class="title">{job.title}</span>
					<span class="ctl-pill {pill(job.state)}">{t.queue.states[job.state]}</span>
					<span class="tasks">
						{#each job.tasks as task (task.id)}
							<span class="task">
								{t.queue.kinds[task.kind]}: {t.queue.tasks[
									task.state
								]}{#if task.stage && task.state === 'running'}
									· {task.stage}{/if}
								{#if task.node_id}<span class="ctl-muted">
										{t.queue.on(nodeName(task.node_id))}</span
									>{/if}
								{#if task.attempts > 1}<span class="ctl-muted">
										· {t.queue.attempt(task.attempts)}</span
									>{/if}
								{#if task.error}<span class="error"> · {task.error}</span>{/if}
							</span>
						{/each}
					</span>
					<span class="ctl-bar" aria-hidden="true"
						><span style:width={`${Math.round(progress * 100)}%`}></span></span
					>
					<span class="ctl-muted mono"
						>{job.state === 'active' && job.eta !== null ? t.queue.eta(clock(job.eta)) : ''}</span
					>
					<span class="ctl-muted">{t.queue.priority(job.tasks[0]?.priority ?? 0)}</span>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="ctl-muted keys">
		<Kbd keys="r" />
		{t.cmd.retry} · <Kbd keys="Shift+r" />
		{t.cmd.retryFailed} · <Kbd keys="Delete" />
		{t.cmd.cancel} ·
		<Kbd keys="Shift+p" />
		{t.cmd.pauseJob} · <Kbd keys="Shift+c" />
		{t.cmd.resumeJob} · <Kbd keys="Alt+ArrowUp" />
		{t.cmd.prioritise}
	</p>
</div>

<style>
	.job {
		grid-template-columns:
			minmax(10rem, 1.4fr) auto minmax(14rem, 2fr) minmax(5rem, 0.6fr)
			7rem 6rem;
	}
	.title {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.tasks {
		display: grid;
		font-size: var(--t--1);
	}
	.error {
		color: var(--erro);
	}
	.mono {
		font-family: var(--font-data);
	}
	.keys {
		margin-top: var(--s-4);
		font-size: var(--t--1);
	}
</style>
