<script lang="ts">
	import { toasts } from '#lib/control/toasts.svelte.js';
</script>

<div class="toasts" role="status" aria-live="polite">
	{#each toasts.list as toast (toast.id)}
		<div class="toast" class:error={toast.kind === 'error'}>
			<span class="text">{toast.text}</span>
			{#if toast.action}<button class="btn subtle" onclick={() => toast.action?.run()}
					>{toast.action.label}</button
				>{/if}
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		z-index: 60;
		right: 16px;
		bottom: calc(var(--player-height) + 12px);
		display: grid;
		gap: 8px;
		max-width: min(28rem, calc(100vw - 2rem));
	}
	.toast {
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 10px 14px;
		background: var(--surface-2);
		border: 1px solid var(--border-strong);
		border-left: 3px solid var(--accent);
		border-radius: var(--radius);
		box-shadow: 0 12px 32px -12px rgb(0 0 0 / 0.6);
	}
	.toast.error {
		border-left-color: var(--error);
	}
	.text {
		flex: 1;
	}
</style>
