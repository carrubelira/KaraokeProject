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

<div class="note" role="alert">
	<Icon name="warn" size={20} />
	<div class="body">
		<strong>{known.title}</strong>
		<p>{known.hint}</p>
		{#if task.error}<p class="raw mono">{task.error}</p>{/if}
		<div class="actions">
			{#if job.state === 'failed'}
				<button class="c-btn go" onclick={() => jobs.act([job.id], 'retry')}>
					<Icon name="retry" size={16} />
					{t.cmd.retry}
				</button>
				{#if elsewhere}
					<button class="c-btn" onclick={() => jobs.retryElsewhere(job.id, task.node_id)}>
						{t.cmd.retryElsewhere}
					</button>
				{/if}
			{/if}
			{#if onlog}
				<button class="c-btn ghost" onclick={onlog}
					><Icon name="log" size={16} /> {t.jobs.log}</button
				>
			{/if}
		</div>
	</div>
</div>

<style>
	.note {
		display: flex;
		gap: 12px;
		padding: 12px 14px;
		border: 1px solid rgb(255 58 70 / 0.35);
		border-left: 2px solid var(--onair);
		background: rgb(255 58 70 / 0.06);
		color: var(--onair);
	}
	.body {
		display: grid;
		gap: 6px;
		color: var(--text);
		min-width: 0;
	}
	p {
		margin: 0;
		color: var(--dim);
		font-size: 13.5px;
	}
	.raw {
		font-size: 11.5px;
		color: var(--faint);
		overflow-wrap: anywhere;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 4px;
	}
</style>
