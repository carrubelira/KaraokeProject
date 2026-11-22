<script lang="ts">
	/** The Galician coast as a faint line: the only nod to the place, kept in the background. */
	import { OUTLINE } from './galicia';

	let { opacity = 0.07 }: { opacity?: number } = $props();
</script>

<svg
	class="coast"
	viewBox="-1000 -1000 2000 2000"
	fill="none"
	stroke="currentColor"
	stroke-width="1"
	style:opacity
	aria-hidden="true"
	focusable="false"><path d={OUTLINE} vector-effect="non-scaling-stroke" /></svg
>

<style>
	.coast {
		display: block;
		width: 100%;
		height: 100%;
		color: var(--text);
		pointer-events: none;
	}
</style>
