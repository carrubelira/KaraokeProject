<script lang="ts">
	import { toasts } from '#lib/control/toasts.svelte.js';
</script>

<div class="toasts" role="status" aria-live="polite">
	{#each toasts.list as toast (toast.id)}
		<div class="toast" class:error={toast.kind === 'error'}>
			<span class="lamp" aria-hidden="true"></span>
			<span class="text">{toast.text}</span>
			{#if toast.action}<button onclick={() => toast.action?.run()}>{toast.action.label}</button
				>{/if}
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		z-index: 60;
		right: 16px;
		bottom: calc(var(--deck) + 14px);
		display: grid;
		gap: 8px;
		max-width: min(30rem, calc(100vw - 2rem));
	}
	.toast {
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 10px 14px;
		background: var(--panel-solid);
		border: 1px solid var(--line-strong);
		border-left: 2px solid var(--cue);
		border-radius: var(--radius);
		box-shadow: 0 12px 40px -12px rgb(0 0 0 / 0.8);
		font-size: 13.5px;
		animation: in 0.25s var(--ease);
	}
	.toast.error {
		border-left-color: var(--onair);
	}
	.lamp {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--cue);
		box-shadow: 0 0 8px var(--cue-glow);
		flex: none;
	}
	.error .lamp {
		background: var(--onair);
		box-shadow: 0 0 8px var(--onair-glow);
	}
	button {
		background: none;
		border: 0;
		color: var(--info);
		font: 500 11px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		cursor: pointer;
	}
	@keyframes in {
		from {
			transform: translateY(8px);
			opacity: 0;
		}
	}
</style>
