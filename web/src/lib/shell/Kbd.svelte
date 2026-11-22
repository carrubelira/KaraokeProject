<script lang="ts">
	/** A shortcut as keys, the platform's way. */
	import { label } from '#lib/commands/keys.js';

	let { keys }: { keys: string | string[] | undefined } = $props();
	const first = $derived(Array.isArray(keys) ? keys[0] : keys);
</script>

{#if first}<kbd class="kbd">{label(first)}</kbd>{/if}
