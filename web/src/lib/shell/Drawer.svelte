<script lang="ts">
	/** A panel that slides in from the right with the detail of one row; Escape closes it. */
	import type { Snippet } from 'svelte';
	import { i18n } from '#lib/i18n';
	import Icon from './Icon.svelte';

	let { title, onclose, children }: { title: string; onclose: () => void; children: Snippet } =
		$props();
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<aside class="drawer" aria-label={title}>
	<header>
		<h2>{title}</h2>
		<button class="ctl-btn ctl-quiet" onclick={onclose} aria-label={i18n.t.common.close}
			><Icon name="close" size={16} /></button
		>
	</header>
	<div class="body">{@render children()}</div>
</aside>

<style>
	.drawer {
		position: fixed;
		z-index: 25;
		top: 0;
		right: 0;
		bottom: var(--statusbar);
		width: min(30rem, 100vw);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-left: 1px solid var(--border-strong);
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
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.body {
		flex: 1;
		overflow: auto;
		padding: var(--sp-4);
	}
</style>
