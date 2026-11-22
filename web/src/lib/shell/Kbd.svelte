<script lang="ts">
	/** A shortcut as keys, the platform's way. */
	import { label } from '#lib/commands/keys.js';

	let { keys }: { keys: string | string[] | undefined } = $props();
	const first = $derived(Array.isArray(keys) ? keys[0] : keys);
</script>

{#if first}<kbd class="kbd">{label(first)}</kbd>{/if}

<style>
	.kbd {
		display: inline-block;
		min-width: 1.6em;
		padding: 0.05em 0.45em;
		border: 1px solid var(--border-strong);
		border-radius: 4px;
		font: 400 0.75em/1.5 var(--font-mono);
		color: var(--text-2);
		text-align: center;
		white-space: nowrap;
	}
</style>
