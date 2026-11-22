<script lang="ts">
	/**
	 * Why a task failed, in words, and what to do about it: retry, retry on another worker, or
	 * change the lyrics, as the error calls for. The worker's own message is there for whoever
	 * wants the detail, and so is its whole log.
	 */
	import type { Job, TaskView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { jobs } from '#lib/shell/actions.svelte.js';
	import Icon from './Icon.svelte';

	let { task, job, onlog }: { task: TaskView; job: Job; onlog?: () => void } = $props();
	const t = $derived(i18n.t);
	const code = $derived(task.error_code ?? 'unknown');
	const known = $derived(t.errors[code] ?? t.errors.unknown);
	const elsewhere = $derived(
		['gpu_memory', 'engine_failed', 'worker_lost', 'out_of_memory', 'disk_full'].includes(code)
	);
</script>

<div class="notice error note" role="alert">
	<Icon name="warn" size={20} />
	<div class="body">
		<strong>{known.title}</strong>
		<p>{known.hint}</p>
		{#if task.error}<p class="raw mono faint">{task.error}</p>{/if}
		<div class="actions">
			{#if job.state === 'failed'}
				<button class="btn primary" onclick={() => jobs.act([job.id], 'retry')}>
					<Icon name="retry" size={16} />
					{t.cmd.retry}
				</button>
				{#if elsewhere}
					<button class="btn" onclick={() => jobs.retryElsewhere(job.id, task.node_id)}>
						{t.cmd.retryElsewhere}
					</button>
				{/if}
			{/if}
			{#if onlog}
				<button class="btn subtle" onclick={onlog}
					><Icon name="log" size={16} /> {t.jobs.log}</button
				>
			{/if}
		</div>
	</div>
</div>

<style>
	.note > :global(svg) {
		flex: none;
		color: var(--error);
	}
	.body {
		display: grid;
		gap: 4px;
		min-width: 0;
	}
	p {
		color: var(--muted);
	}
	.raw {
		font-size: 12px;
		overflow-wrap: anywhere;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 6px;
	}
</style>
