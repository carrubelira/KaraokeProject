<script lang="ts">
	/** Galicia's coastline, drawn as a faint line: the one ornament of the control. */
	import { COAST } from './coast';

	let { class: className = '' }: { class?: string } = $props();
</script>

<svg class="coast {className}" viewBox="-400 -410 740 790" aria-hidden="true" focusable="false">
	<path d={COAST} />
</svg>

<style>
	.coast {
		display: block;
		pointer-events: none;
	}
	path {
		fill: none;
		stroke: currentColor;
		stroke-width: 1.2;
		stroke-linejoin: round;
		vector-effect: non-scaling-stroke;
	}
</style>
