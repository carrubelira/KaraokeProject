<script lang="ts">
	/**
	 * The live 3D signal field behind the whole console. Three.js loads after the first paint
	 * (it is a large module), the scene follows the live state, and it rests when the tab is
	 * hidden, when the operator turns effects off, or when the system asks for less motion.
	 */
	import { onMount } from 'svelte';
	import { live } from '#lib/control/live.svelte.js';
	import { player } from '#lib/shell/actions.svelte.js';
	import { prefs } from '#lib/shell/prefs.svelte.js';
	import type { Field, Motion } from './field';
	import { signals } from './signals';

	let canvas: HTMLCanvasElement | undefined = $state();
	let field = $state<Field | null>(null);
	let reduced = $state(false);

	const motion = $derived<Motion>(reduced ? 'off' : prefs.value.effects);
	const current = $derived(signals(live.state, player()?.id, live.connected));

	onMount(() => {
		const query = matchMedia('(prefers-reduced-motion: reduce)');
		reduced = query.matches;
		const onChange = () => (reduced = query.matches);
		query.addEventListener('change', onChange);
		let made: Field | null = null;
		let cancelled = false;
		const observer = new ResizeObserver(() => made?.resize());
		void import('./field').then(({ Field }) => {
			if (cancelled || !canvas) return;
			try {
				made = new Field(canvas, motion);
				field = made;
				observer.observe(canvas);
			} catch {
				// No WebGL here: the console works the same without its background.
			}
		});
		return () => {
			cancelled = true;
			query.removeEventListener('change', onChange);
			observer.disconnect();
			made?.dispose();
		};
	});

	$effect(() => field?.setMotion(motion));
	$effect(() => field?.update(current));
</script>

<canvas bind:this={canvas} class="scene" class:hidden={!field} aria-hidden="true"></canvas>

<style>
	.scene {
		position: fixed;
		inset: 0;
		width: 100%;
		height: 100%;
		z-index: 0;
		pointer-events: none;
		opacity: 1;
		transition: opacity 1.2s ease;
	}

	.hidden {
		opacity: 0;
	}
</style>
