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
		border: 1px solid var(--line-strong);
		border-bottom-width: 2px;
		border-radius: 2px;
		font: 500 0.74em/1.5 var(--font-mono);
		color: var(--dim);
		text-align: center;
		white-space: nowrap;
	}
</style>
