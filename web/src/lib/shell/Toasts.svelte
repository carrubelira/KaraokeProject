<script lang="ts">
	import { toasts } from '#lib/control/toasts.svelte.js';
</script>

<div class="toasts" role="status" aria-live="polite">
	{#each toasts.list as toast (toast.id)}
		<div class="toast" class:error={toast.kind === 'error'}>
			<span>{toast.text}</span>
			{#if toast.action}<button onclick={() => toast.action?.run()}>{toast.action.label}</button
				>{/if}
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		z-index: 50;
		right: var(--s-4);
		bottom: calc(var(--statusbar) + var(--sp-3));
		display: grid;
		gap: var(--s-2);
		max-width: min(28rem, calc(100vw - 2rem));
	}
	.toast {
		display: flex;
		gap: var(--s-3);
		align-items: center;
		padding: var(--s-2) var(--s-4);
		background: var(--surface-2);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-control);
	}
	.toast.error {
		border-color: var(--erro);
	}
	button {
		background: none;
		border: 0;
		color: var(--accent-text);
		font: inherit;
		cursor: pointer;
	}
</style>
