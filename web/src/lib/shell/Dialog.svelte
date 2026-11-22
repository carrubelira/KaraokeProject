<script lang="ts">
	/** A modal dialog over a dimmed page; Escape or the backdrop closes it. */
	import type { Snippet } from 'svelte';
	import { i18n } from '#lib/i18n';
	import Icon from './Icon.svelte';

	let {
		title,
		onclose,
		children,
		width = '34rem'
	}: { title: string; onclose: () => void; children: Snippet; width?: string } = $props();
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<div class="backdrop" role="presentation" onclick={onclose}></div>
<div class="dialog" role="dialog" aria-modal="true" aria-label={title} style:width>
	<header>
		<h2>{title}</h2>
		<button class="ctl-btn ctl-quiet" onclick={onclose} aria-label={i18n.t.common.close}
			><Icon name="close" size={16} /></button
		>
	</header>
	<div class="body">{@render children()}</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: rgb(0 0 0 / 0.5);
	}
	.dialog {
		position: fixed;
		z-index: 41;
		top: 14vh;
		left: 50%;
		transform: translateX(-50%);
		max-width: calc(100vw - 2rem);
		max-height: 76vh;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius);
	}
	header {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: var(--sp-3) var(--sp-4);
		border-bottom: 1px solid var(--border);
	}
	h2 {
		flex: 1;
		font-size: var(--fs-l);
	}
	.body {
		overflow: auto;
		padding: var(--sp-4);
	}
</style>
