<script lang="ts">
	/**
	 * Jobs: one row per song being made or exported, told in plain words (state, current step,
	 * progress, machine, time left), with a detail drawer (Enter) for the steps and the error.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import {
		BADGE,
		describeJob,
		matches,
		stepOf,
		stepsOf,
		type JobFilter
	} from '#lib/control/describe.js';
	import { live } from '#lib/control/live.svelte.js';
	import type { Job } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import Drawer from '#lib/shell/Drawer.svelte';
	import { clock, when } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { Selection } from '#lib/shell/selection.svelte.js';

	const t = $derived(i18n.t);
	const FILTERS: JobFilter[] = ['all', 'active', 'failed', 'done'];
	let filter = $state<JobFilter>('all');
	let open = $state<string | null>(null);
	const list = $derived(live.state.jobs.filter((j) => matches(j, filter)));
	const count = (f: JobFilter) => live.state.jobs.filter((j) => matches(j, f)).length;
	const selection = new Selection(() => list.map((j) => j.id));
	const detail = $derived(open ? live.state.jobs.find((j) => j.id === open) : undefined);
	const nodeName = (id: string | null) =>
		id ? (live.state.nodes.find((n) => n.id === id)?.name ?? id) : '';

	$effect(() => {
		void list.length;
		selection.clamp();
	});
	$effect(() => {
		const id = selection.current;
		if (id) document.getElementById(`job-${id}`)?.scrollIntoView({ block: 'nearest' });
		if (open && id) open = id;
	});

	const states = (wanted: string[]) =>
		selection.targets.filter((id) => wanted.includes(list.find((j) => j.id === id)?.state ?? ''));

	function cycle(step: number) {
		const i = FILTERS.indexOf(filter);
		filter = FILTERS[(i + step + FILTERS.length) % FILTERS.length];
	}

	onMount(() => {
		commands.scope = 'queue';
		const group = () => t.groups.jobs;
		const scope = 'queue' as const;
		return commands.register(
			...[
				{
					id: 'queue.down',
					title: () => t.cmd.down,
					keys: ['j', 'ArrowDown'],
					run: () => selection.move(1),
					hidden: true
				},
				{
					id: 'queue.up',
					title: () => t.cmd.up,
					keys: ['k', 'ArrowUp'],
					run: () => selection.move(-1),
					hidden: true
				},
				{
					id: 'queue.extendDown',
					title: () => t.cmd.selectDown,
					keys: ['Shift+j'],
					run: () => selection.extend(1)
				},
				{
					id: 'queue.extendUp',
					title: () => t.cmd.selectUp,
					keys: ['Shift+k'],
					run: () => selection.extend(-1)
				},
				{
					id: 'queue.mark',
					title: () => t.cmd.toggleSelect,
					keys: ['x'],
					run: () => selection.toggle()
				},
				{
					id: 'queue.open',
					title: () => t.cmd.details,
					keys: ['Enter'],
					run: () => void (open = open ? null : (selection.current ?? null))
				},
				{ id: 'queue.filterNext', title: () => t.cmd.filterNext, keys: ['f'], run: () => cycle(1) },
				{
					id: 'queue.filterPrevious',
					title: () => t.cmd.filterPrevious,
					keys: ['Shift+f'],
					run: () => cycle(-1)
				},
				{
					id: 'queue.retry',
					title: () => t.cmd.retry,
					keys: ['r'],
					run: () => jobs.act(states(['failed', 'cancelled']), 'retry')
				},
				{
					id: 'queue.retryFailed',
					title: () => t.cmd.retryFailed,
					keys: ['Shift+r'],
					run: jobs.retryFailed
				},
				{
					id: 'queue.cancel',
					title: () => t.cmd.cancel,
					keys: ['Delete', 'Backspace'],
					run: () => jobs.act(states(['active', 'paused']), 'cancel')
				},
				{
					id: 'queue.pause',
					title: () => t.cmd.pauseJob,
					keys: ['Shift+p'],
					run: () => jobs.act(states(['active']), 'pause')
				},
				{
					id: 'queue.resume',
					title: () => t.cmd.resumeJob,
					keys: ['Shift+c'],
					run: () => jobs.act(states(['paused']), 'resume')
				},
				{
					id: 'queue.up_',
					title: () => t.cmd.prioritise,
					keys: ['Alt+ArrowUp', '+'],
					run: () => jobs.priority(states(['active', 'paused']), 10)
				},
				{
					id: 'queue.down_',
					title: () => t.cmd.deprioritise,
					keys: ['Alt+ArrowDown', '-'],
					run: () => jobs.priority(states(['active', 'paused']), -10)
				}
			].map((c) => ({ ...c, group, scope }))
		);
	});
</script>

{#snippet actions(job: Job)}
	{#if job.state === 'failed' || job.state === 'cancelled'}
		<button class="ctl-btn" onclick={() => jobs.act([job.id], 'retry')}
			>{t.cmd.retry} <Kbd keys="r" /></button
		>
	{/if}
	{#if job.state === 'active'}
		<button class="ctl-btn" onclick={() => jobs.act([job.id], 'pause')}
			>{t.jobs.pause} <Kbd keys="Shift+p" /></button
		>
	{/if}
	{#if job.state === 'paused'}
		<button class="ctl-btn" onclick={() => jobs.act([job.id], 'resume')}
			>{t.jobs.resume} <Kbd keys="Shift+c" /></button
		>
	{/if}
	{#if job.state === 'active' || job.state === 'paused'}
		<button class="ctl-btn" onclick={() => jobs.priority([job.id], 10)}
			>{t.cmd.prioritise} <Kbd keys="+" /></button
		>
		<button class="ctl-btn ctl-danger" onclick={() => jobs.act([job.id], 'cancel')}
			>{t.cmd.cancel} <Kbd keys="Delete" /></button
		>
	{/if}
{/snippet}

<div class="ctl-page" class:with-drawer={detail}>
	<header class="ctl-page-head">
		<h1>{t.jobs.title}</h1>
		<span class="ctl-sub">{t.jobs.summary(count('active'), count('failed'))}</span>
		<div class="ctl-actions">
			<button class="ctl-btn" onclick={jobs.retryFailed} disabled={!count('failed')}
				>{t.cmd.retryFailed} <Kbd keys="Shift+r" /></button
			>
		</div>
	</header>

	<section class="ctl-panel">
		<div class="ctl-toolbar">
			<div class="ctl-seg" role="group" aria-label={t.jobs.filter}>
				{#each FILTERS as f (f)}
					<button aria-pressed={filter === f} onclick={() => (filter = f)}
						>{t.jobs.filters[f]} <span class="ctl-mono ctl-muted">{count(f)}</span></button
					>
				{/each}
			</div>
			<span class="ctl-end"><Kbd keys="f" /> {t.jobs.filterHint}</span>
		</div>
		{#if list.length === 0}
			<p class="ctl-empty">{filter === 'all' ? t.jobs.empty : t.jobs.emptyFilter}</p>
		{:else}
			<table class="ctl-table" aria-label={t.jobs.title}>
				<thead>
					<tr>
						<th>{t.jobs.columns.title}</th>
						<th>{t.jobs.columns.state}</th>
						<th>{t.jobs.columns.step}</th>
						<th>{t.jobs.columns.progress}</th>
						<th>{t.jobs.columns.machine}</th>
						<th class="ctl-num">{t.jobs.columns.left}</th>
						<th class="ctl-num">{t.jobs.columns.created}</th>
					</tr>
				</thead>
				<tbody>
					{#each list as job, i (job.id)}
						{@const s = describeJob(job)}
						<tr
							id={`job-${job.id}`}
							class:ctl-cursor={i === selection.cursor}
							class:ctl-marked={selection.marked.has(job.id)}
							aria-selected={i === selection.cursor}
							onclick={() => (selection.cursor = i)}
							ondblclick={() => (open = job.id)}
						>
							<td class="ctl-title">{job.title}</td>
							<td><span class="ctl-badge {BADGE[s.status]}">{t.jobs.status[s.status]}</span></td>
							<td class="ctl-ellipsis" class:failed={s.status === 'failed'}>
								{s.step ? t.jobs.steps[s.step] : ''}
								{#if s.task && s.task.attempts > 1}<span class="ctl-muted ctl-after">
										· {t.jobs.attempt(s.task.attempts)}</span
									>{/if}
							</td>
							<td>
								{#if s.status !== 'cancelled'}
									<div class="ctl-progress">
										<div class="ctl-track">
											<span style:width={`${Math.round(s.fraction * 100)}%`}></span>
										</div>
										<span class="ctl-pct">{Math.round(s.fraction * 100)} %</span>
									</div>
								{/if}
							</td>
							<td>{nodeName(s.node)}</td>
							<td class="ctl-num">{s.eta !== null ? clock(s.eta) : ''}</td>
							<td class="ctl-num ctl-muted">{when(job.created_at, i18n.locale)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
	<p class="ctl-hint">
		<Kbd keys="Enter" />
		{t.cmd.details} · <Kbd keys="x" />
		{t.cmd.toggleSelect} · <Kbd keys="r" />
		{t.cmd.retry} · <Kbd keys="Delete" />
		{t.cmd.cancel} · <Kbd keys="?" />
		{t.cmd.cheatsheet}
	</p>
</div>

{#if detail}
	{@const s = describeJob(detail)}
	<Drawer title={detail.title} onclose={() => (open = null)}>
		<dl class="ctl-kv">
			<dt>{t.jobs.columns.state}</dt>
			<dd><span class="ctl-badge {BADGE[s.status]}">{t.jobs.status[s.status]}</span></dd>
			<dt>{t.jobs.kind}</dt>
			<dd>{t.jobs.kinds[detail.kind]}</dd>
			<dt>{t.jobs.columns.created}</dt>
			<dd>{new Date(detail.created_at).toLocaleString(i18n.locale)}</dd>
			{#if s.eta !== null}<dt>{t.jobs.columns.left}</dt>
				<dd class="ctl-mono">{clock(s.eta)}</dd>{/if}
		</dl>
		<h3>{t.jobs.timeline}</h3>
		<ol class="timeline">
			{#each stepsOf(detail) as { task, state } (task.id)}
				<li class={state}>
					<span class="mark" aria-hidden="true"></span>
					<div>
						<p class="what">{t.jobs.taskKinds[task.kind]}</p>
						<p class="ctl-muted">
							{t.jobs.stepStates[state]}{#if state === 'current' && task.stage}
								· {t.jobs.steps[stepOf(task)]}{/if}{#if task.node_id}
								· {nodeName(task.node_id)}{/if}{#if task.attempts > 1}
								· {t.jobs.attempt(task.attempts)}{/if}{#if task.elapsed}
								· <span class="ctl-mono">{clock(task.elapsed)}</span>{/if}
						</p>
						{#if task.error}<pre class="error">{task.error}</pre>{/if}
					</div>
				</li>
			{/each}
		</ol>
		{#if detail.error && !detail.tasks.some((task) => task.error)}
			<pre class="error">{detail.error}</pre>
		{/if}
		<div class="buttons">{@render actions(detail)}</div>
	</Drawer>
{/if}

<style>
	.with-drawer {
		margin-right: 30rem;
	}
	td.failed {
		color: #f1a5a3;
	}
	h3 {
		margin: var(--sp-5) 0 var(--sp-3);
		font-size: var(--fs-m);
	}
	.timeline {
		list-style: none;
		padding: 0;
		display: grid;
	}
	.timeline li {
		position: relative;
		display: grid;
		grid-template-columns: 1.5rem 1fr;
		padding-bottom: var(--sp-4);
	}
	.timeline li:not(:last-child)::before {
		content: '';
		position: absolute;
		left: 0.34rem;
		top: 1.1rem;
		bottom: 0;
		width: 1px;
		background: var(--border-strong);
	}
	.mark {
		width: 0.75rem;
		height: 0.75rem;
		margin-top: 0.3rem;
		border-radius: 50%;
		border: 2px solid var(--border-strong);
		background: var(--surface);
	}
	.done .mark {
		background: var(--ok);
		border-color: var(--ok);
	}
	.current .mark {
		border-color: var(--accent);
		background: var(--accent);
	}
	.failed .mark {
		background: var(--bad);
		border-color: var(--bad);
	}
	.what {
		font-weight: 500;
	}
	.error {
		margin-top: var(--sp-2);
		padding: var(--sp-2) var(--sp-3);
		border: 1px solid rgb(224 98 94 / 0.4);
		border-radius: var(--radius);
		background: rgb(224 98 94 / 0.08);
		color: #f1a5a3;
		font: var(--fs-s) / 1.5 var(--font-mono);
		white-space: pre-wrap;
		word-break: break-word;
	}
	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		margin-top: var(--sp-4);
	}
</style>
