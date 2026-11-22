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

<article class="analysing" class:failed={!!failed}>
	<header>
		<span class="c-tally {failed ? 'onair' : 'info'}"></span>
		<strong class="title">{job.title}</strong>
		{#if worker}<span class="c-tag">{t.jobs.on(worker)}</span>{/if}
		<span class="spacer"></span>
		<button
			class="c-btn icon ghost"
			aria-label={t.cmd.cancel}
			title={t.cmd.cancel}
			onclick={() => jobs.act([job.id], 'cancel')}><Icon name="close" size={16} /></button
		>
	</header>
	<ol class="steps">
		{#each STEPS as step, i (step)}
			<li class:done={i < at} class:now={i === at && !failed} class:bad={i === at && !!failed}>
				<span class="dot"></span>
				<span class="label">{t.add.steps[step]}</span>
			</li>
		{/each}
	</ol>
	{#if failed}
		<ErrorNote task={failed} {job} />
	{:else}
		<div class="c-progress" style:--value={fraction}></div>
		<p class="message dim">{active?.message ?? active?.step ?? ''}</p>
		{#if lines.length}
			<pre class="tail">{lines.join('\n')}</pre>
		{/if}
	{/if}
</article>

<style>
	.analysing {
		display: grid;
		gap: 12px;
		padding: 14px;
		border-bottom: 1px solid var(--line);
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
	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.spacer {
		flex: 1;
	}
	.steps {
		display: grid;
		grid-template-columns: repeat(6, 1fr);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.steps li {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		text-align: center;
	}
	.steps li::before {
		content: '';
		position: absolute;
		top: 5px;
		left: -50%;
		right: 50%;
		height: 1px;
		background: var(--line-strong);
	}
	.steps li:first-child::before {
		display: none;
	}
	.steps li.done::before,
	.steps li.now::before {
		background: var(--cue);
	}
	.dot {
		position: relative;
		width: 11px;
		height: 11px;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--void);
	}
	.done .dot {
		background: var(--cue);
		border-color: var(--cue);
	}
	.now .dot {
		border-color: var(--info);
		background: var(--info);
		box-shadow: 0 0 12px var(--info);
		animation: pulse 1s ease-in-out infinite;
	}
	.bad .dot {
		background: var(--onair);
		border-color: var(--onair);
	}
	.now .label {
		color: var(--info);
	}
	.done .label {
		color: var(--text);
	}
	@keyframes pulse {
		50% {
			transform: scale(1.35);
		}
	}
	.message {
		margin: 0;
		font-size: 13px;
		min-height: 1.2em;
	}
	.tail {
		margin: 0;
		padding: 8px 10px;
		background: rgb(0 0 0 / 0.5);
		border: 1px solid var(--line);
		font: 11px/1.5 var(--font-mono);
		color: var(--dim);
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		max-height: 5.5em;
		overflow: hidden;
	}
	@media (max-width: 640px) {
		.steps .label {
			display: none;
		}
	}
</style>
