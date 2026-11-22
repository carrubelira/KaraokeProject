<script lang="ts">
	/** Jobs: every job as a pipeline of its tasks, filtered by what needs attention. */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Pipeline from '#lib/console/Pipeline.svelte';
	import { live } from '#lib/control/live.svelte.js';
	import type { Job } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';

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

<div class="c-page">
	<div class="c-page-head">
		<h1>{t.jobs.title}</h1>
		<div class="filters" role="tablist">
			{#each FILTERS as f (f)}
				<button
					role="tab"
					aria-selected={filter === f}
					class:on={filter === f}
					onclick={() => (filter = f)}
				>
					{t.jobs.filters[f]} <span class="mono">{counts[f]}</span>
				</button>
			{/each}
		</div>
		<span class="spacer"></span>
		{#if counts.failed}
			<button class="c-btn" onclick={jobs.retryFailed}>{t.cmd.retryFailed}</button>
		{/if}
	</div>
	{#each shown as job (job.id)}
		<Pipeline {job} />
	{:else}
		<section class="c-panel"><p class="c-empty">{t.jobs.empty}</p></section>
	{/each}
</div>

<style>
	.filters {
		display: flex;
		gap: 2px;
		padding: 3px;
		border: 1px solid var(--line);
		border-radius: var(--radius);
		background: var(--panel);
	}
	.filters button {
		padding: 6px 12px;
		border: 0;
		border-radius: 2px;
		background: transparent;
		color: var(--dim);
		font: 500 11px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		cursor: pointer;
	}
	.filters button.on {
		background: var(--raise);
		color: var(--text);
	}
	.filters .mono {
		color: var(--faint);
		margin-left: 4px;
	}
</style>
