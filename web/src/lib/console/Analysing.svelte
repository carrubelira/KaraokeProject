<script lang="ts">
	/**
	 * A song being analysed: its steps lit as they pass (download, metadata, fingerprint,
	 * AcoustID, MusicBrainz, lyrics), what the worker says it is doing, and its last log lines.
	 * A failure shows its cause and what to do.
	 */
	import { live } from '#lib/control/live.svelte.js';
	import type { Job } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import ErrorNote from './ErrorNote.svelte';
	import Icon from './Icon.svelte';

	let { job }: { job: Job } = $props();
	const t = $derived(i18n.t);
	const STEPS = [
		'download',
		'metadata',
		'fingerprint',
		'acoustid',
		'musicbrainz',
		'lyrics'
	] as const;

	const fetch = $derived(job.tasks.find((x) => x.kind === 'fetch'));
	const analyse = $derived(job.tasks.find((x) => x.kind === 'analyze'));
	const failed = $derived(job.tasks.find((x) => x.state === 'failed'));
	const at = $derived.by(() => {
		if (fetch && fetch.state !== 'done') return 0;
		if (!analyse || analyse.state === 'done') return STEPS.length;
		const step = analyse.step ?? 'metadata';
		const index = STEPS.indexOf(step as (typeof STEPS)[number]);
		return index < 0 ? 1 : index;
	});
	const active = $derived(fetch && fetch.state !== 'done' ? fetch : analyse);
	const lines = $derived((active ? live.state.logs[active.id] : undefined)?.slice(-3) ?? []);
	const fraction = $derived(
		fetch && fetch.state !== 'done' ? (fetch.fraction ?? 0) : (analyse?.fraction ?? 0)
	);
	const worker = $derived(live.state.nodes.find((n) => n.id === active?.node_id)?.name);
</script>

<article class="analysing">
	<header>
		<strong class="title truncate">{job.title}</strong>
		<span class="badge {failed ? 'error' : 'info'}">
			{failed ? t.jobs.states.failed : t.jobs.states.active}
		</span>
		{#if worker}<span class="muted small">{t.jobs.on(worker)}</span>{/if}
		<button
			class="btn subtle icon cancel"
			aria-label={t.cmd.cancel}
			title={t.cmd.cancel}
			onclick={() => jobs.act([job.id], 'cancel')}><Icon name="close" size={16} /></button
		>
	</header>
	<ol class="steps">
		{#each STEPS as step, i (step)}
			<li class:done={i < at} class:now={i === at && !failed} class:bad={i === at && !!failed}>
				<span class="dot" aria-hidden="true">
					{#if i < at}<Icon name="check" size={12} />{/if}
				</span>
				<span class="name">{t.add.steps[step]}</span>
			</li>
		{/each}
	</ol>
	{#if failed}
		<ErrorNote task={failed} {job} />
	{:else}
		<div class="progress"><span style:width="{fraction * 100}%"></span></div>
		<p class="muted small message">{active?.message ?? active?.step ?? ''}</p>
		{#if lines.length}
			<pre class="tail">{lines.join('\n')}</pre>
		{/if}
	{/if}
</article>

<style>
	.analysing {
		display: grid;
		gap: 12px;
		padding: 16px;
		border-bottom: 1px solid var(--border);
	}
	.analysing:last-child {
		border-bottom: 0;
	}
	header {
		display: flex;
		align-items: center;
		gap: 10px;
		min-width: 0;
	}
	.cancel {
		margin-left: auto;
	}
	.steps {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 18px;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.steps li {
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--faint);
		font-size: 13px;
	}
	.dot {
		display: grid;
		place-items: center;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 1px solid var(--border-strong);
	}
	.done {
		color: var(--muted);
	}
	.done .dot {
		background: var(--ok);
		border-color: var(--ok);
		color: #fff;
	}
	.now {
		color: var(--text);
		font-weight: 500;
	}
	.now .dot {
		border: 2px solid var(--accent);
	}
	.bad {
		color: var(--error);
	}
	.bad .dot {
		border-color: var(--error);
		background: var(--error);
	}
	.message {
		min-height: 1.2em;
	}
	.tail {
		margin: 0;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg);
		color: var(--muted);
		font: 12px/1.5 var(--mono);
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		max-height: 5.5em;
		overflow: hidden;
	}
</style>
