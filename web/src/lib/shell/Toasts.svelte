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
		bottom: 3.2rem;
		display: grid;
		gap: var(--s-2);
		max-width: min(28rem, calc(100vw - 2rem));
	}
	.toast {
		display: flex;
		gap: var(--s-3);
		align-items: center;
		padding: var(--s-2) var(--s-4);
		background: var(--fondo-2);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		box-shadow: var(--sombra);
	}
	.toast.error {
		border-color: var(--erro);
	}
	button {
		background: none;
		border: 0;
		color: var(--ceo);
		font: inherit;
		cursor: pointer;
	}
</style>
